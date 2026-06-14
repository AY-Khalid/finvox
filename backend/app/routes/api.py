"""Public JSON API consumed by the Next.js PWA. v3: counterparty support."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Feedback, Transaction, User
from ..services.ledger import debt_totals, range_summary
from ..services.statements import build_statements

router = APIRouter(prefix="/api")


class FeedbackIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    page: str | None = None


def _require_admin(authorization: str | None) -> None:
    """Bearer-token check for admin-only routes."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/health")
def health():
    return {"status": "ok", "app": "finvox"}


@router.post("/feedback", status_code=201)
def submit_feedback(
    payload: FeedbackIn,
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    db: Session = Depends(get_db),
):
    """Public endpoint. Anyone can leave feedback once from the landing page."""
    fb = Feedback(
        message=payload.message.strip()[:4000],
        page=(payload.page or "")[:120] or None,
        user_agent=(user_agent or "")[:300] or None,
    )
    db.add(fb)
    db.commit()
    return {"status": "received", "id": fb.id}


@router.get("/admin/feedback")
def list_feedback(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Admin-only. Returns all collected feedback, newest first."""
    _require_admin(authorization)
    rows = (db.query(Feedback)
            .order_by(Feedback.created_at.desc())
            .limit(1000).all())
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "message": r.message,
                "page": r.page,
                "user_agent": r.user_agent,
                "created_at": r.created_at.isoformat() + "Z",
            }
            for r in rows
        ],
    }


@router.get("/ledger/{token}/statements")
def get_statements(token: str, start: str | None = None, end: str | None = None,
                   db: Session = Depends(get_db)):
    user = db.query(User).filter(User.token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Ledger not found")

    def parse(s, fallback):
        if not s:
            return fallback
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Bad date: {s}")

    first = (db.query(Transaction)
             .filter(Transaction.user_id == user.id)
             .order_by(Transaction.txn_date.asc()).first())
    start_d = parse(start, first.txn_date if first else date.today())
    end_d = parse(end, date.today())
    if start_d > end_d:
        raise HTTPException(status_code=400, detail="start must be before end")
    return build_statements(db, user, start_d, end_d)


@router.get("/ledger/{token}")
def get_ledger(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Ledger not found")

    txns = (db.query(Transaction)
            .filter(Transaction.user_id == user.id)
            .order_by(Transaction.txn_date.desc(), Transaction.id.desc())
            .limit(500).all())

    today = range_summary(db, user, date.today(), date.today())
    first = txns[-1].txn_date if txns else date.today()
    all_time = range_summary(db, user, first, date.today())

    return {
        "user": {
            "phone_masked": f"...{user.phone[-4:]}" if len(user.phone) >= 4 else user.phone,
            "name": user.name,
            "member_since": user.created_at.date().isoformat(),
        },
        "today": today,
        "all_time": all_time,
        "debts": debt_totals(db, user),
        "transactions": [
            {
                "id": t.id,
                "date": t.txn_date.isoformat(),
                "timestamp": t.created_at.isoformat() + "Z",  # UTC; client renders local time
                "type": t.type,
                "payment_method": t.payment_method or "cash",
                "counterparty": t.counterparty,
                "item": t.item,
                "quantity": t.quantity,
                "unit_price": t.unit_price,
                "amount": t.amount,
                "source": t.source,
            }
            for t in txns
        ],
    }
