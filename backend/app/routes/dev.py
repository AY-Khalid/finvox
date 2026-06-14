"""Dev-only simulator: test the full message flow without WhatsApp.

POST /dev/simulate  {"phone": "2348012345678", "text": "I sell rice 5000"}
Returns the exact reply WhatsApp would send.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..services.handler import handle_incoming

router = APIRouter(prefix="/dev")


class SimulateIn(BaseModel):
    phone: str
    text: str
    name: str | None = None


@router.post("/simulate")
async def simulate(payload: SimulateIn, db: Session = Depends(get_db)):
    if not settings.DEV_MODE:
        raise HTTPException(status_code=404)
    reply = await handle_incoming(db, payload.phone, text=payload.text,
                                  name=payload.name)
    return {"reply": reply}


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    """Delete ALL records (users, transactions, inventory). Dev only."""
    if not settings.DEV_MODE:
        raise HTTPException(status_code=404)
    from ..models import InventorySnapshot, Transaction, User
    n_t = db.query(Transaction).delete()
    n_s = db.query(InventorySnapshot).delete()
    n_u = db.query(User).delete()
    db.commit()
    return {"status": "reset",
            "deleted": {"users": n_u, "transactions": n_t, "inventory_snapshots": n_s}}
