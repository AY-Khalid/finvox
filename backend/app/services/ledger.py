"""Ledger logic: saving transactions and building summaries/statements. v3."""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import InventorySnapshot, Transaction, User


def naira(n: float) -> str:
    return f"₦{n:,.0f}" if float(n).is_integer() else f"₦{n:,.2f}"


def save_transactions(db: Session, user: User, parsed: dict, source: str) -> list[Transaction]:
    saved = []
    transcript = parsed.get("transcript") or ""
    for t in parsed.get("transactions", []):
        try:
            txn_date = datetime.strptime(t.get("date") or "", "%Y-%m-%d").date()
        except ValueError:
            txn_date = date.today()
        method = t.get("payment_method") or "cash"
        if method not in ("cash", "transfer", "pos", "owed"):
            method = "cash"
        cp = (t.get("counterparty") or "").strip() or None
        ttype = t.get("type") or "sale"
        cat = None
        if ttype == "expense":
            cat = t.get("category") if t.get("category") in ("stock", "operating") else "operating"
        txn = Transaction(
            user_id=user.id,
            type=ttype,
            payment_method=method,
            category=cat,
            counterparty=cp[:120] if cp else None,
            item=(t.get("item") or "item")[:200],
            quantity=t.get("quantity"),
            unit_price=t.get("unit_price"),
            amount=float(t.get("amount") or 0),
            raw_text=transcript[:2000],
            source=source,
            txn_date=txn_date,
        )
        db.add(txn)
        saved.append(txn)
    db.commit()
    return saved


def save_snapshot(db: Session, user: User, value: float) -> InventorySnapshot:
    snap = InventorySnapshot(user_id=user.id, value=float(value))
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def latest_snapshot(db: Session, user: User, on_or_before: date | None = None,
                    strictly_before: date | None = None) -> InventorySnapshot | None:
    q = db.query(InventorySnapshot).filter(InventorySnapshot.user_id == user.id)
    if strictly_before:
        q = q.filter(InventorySnapshot.snap_date < strictly_before)
    elif on_or_before:
        q = q.filter(InventorySnapshot.snap_date <= on_or_before)
    return q.order_by(InventorySnapshot.snap_date.desc(),
                      InventorySnapshot.id.desc()).first()


def debt_names(db: Session, user: User, ttype: str, as_of: date | None = None,
               limit: int = 6) -> list[tuple[str, float]]:
    """Who owes (ttype='sale') or is owed (ttype='expense'), grouped by name."""
    q = (
        select(func.coalesce(Transaction.counterparty, "Name not recorded"),
               func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id,
               Transaction.payment_method == "owed",
               Transaction.type == ttype)
    )
    if as_of:
        q = q.where(Transaction.txn_date <= as_of)
    q = q.group_by(func.coalesce(Transaction.counterparty, "Name not recorded")) \
         .order_by(func.sum(Transaction.amount).desc()).limit(limit)
    return [(name, float(total or 0)) for name, total in db.execute(q)]


def debt_totals(db: Session, user: User, as_of: date | None = None) -> dict:
    """Outstanding credit ('owed') totals up to a date.
    owed_to_me = unpaid credit sales. i_owe = things taken on credit."""
    q = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id,
               Transaction.payment_method == "owed")
    )
    if as_of:
        q = q.where(Transaction.txn_date <= as_of)
    owed_to_me = i_owe = 0.0
    for ttype, total in db.execute(q.group_by(Transaction.type)):
        if ttype == "sale":
            owed_to_me = float(total or 0)
        else:
            i_owe = float(total or 0)
    return {"owed_to_me": owed_to_me, "i_owe": i_owe}


def range_summary(db: Session, user: User, start: date, end: date) -> dict:
    q = (
        select(Transaction.type, func.sum(Transaction.amount), func.count())
        .where(Transaction.user_id == user.id,
               Transaction.txn_date >= start,
               Transaction.txn_date <= end)
        .group_by(Transaction.type)
    )
    sales = expenses = 0.0
    count = 0
    for ttype, total, n in db.execute(q):
        count += n
        if ttype == "sale":
            sales = float(total or 0)
        else:
            expenses = float(total or 0)

    top = db.execute(
        select(Transaction.item, func.sum(Transaction.amount).label("s"))
        .where(Transaction.user_id == user.id,
               Transaction.type == "sale",
               Transaction.txn_date >= start,
               Transaction.txn_date <= end)
        .group_by(Transaction.item).order_by(func.sum(Transaction.amount).desc())
    ).first()

    big = db.execute(
        select(Transaction.item, Transaction.amount)
        .where(Transaction.user_id == user.id,
               Transaction.type == "expense",
               Transaction.txn_date >= start,
               Transaction.txn_date <= end)
        .order_by(Transaction.amount.desc())
    ).first()

    by_method: dict[str, float] = {}
    for method, total in db.execute(
        select(Transaction.payment_method, func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id,
               Transaction.type == "sale",
               Transaction.txn_date >= start,
               Transaction.txn_date <= end)
        .group_by(Transaction.payment_method)
    ):
        by_method[method or "cash"] = float(total or 0)

    debts = debt_totals(db, user, as_of=end)
    debtors = debt_names(db, user, "sale", as_of=end)
    creditors = debt_names(db, user, "expense", as_of=end)

    return {"sales": sales, "expenses": expenses, "profit": sales - expenses,
            "debtors": debtors, "creditors": creditors,
            "count": count, "top_item": top[0] if top else None,
            "biggest_expense": {"item": big[0], "amount": float(big[1])} if big else None,
            "by_method": by_method, **debts,
            "start": start.isoformat(), "end": end.isoformat()}


METHOD_LABEL = {"cash": "cash", "transfer": "transfer", "pos": "POS", "owed": "owed, not paid yet"}


def confirmation_message(saved: list[Transaction], db: Session, user: User) -> str:
    lines = ["✅ Recorded:"]
    for t in saved:
        qty = f"{t.quantity:g} x {naira(t.unit_price)} = " if t.quantity and t.unit_price else ""
        tag = "\U0001f4b0 Sale" if t.type == "sale" else "\U0001f4b8 Expense"
        who = f", {t.counterparty}" if t.counterparty else ""
        lines.append(f"{tag}: {t.item}, {qty}{naira(t.amount)} "
                     f"({METHOD_LABEL.get(t.payment_method, 'cash')}{who})")
    s = range_summary(db, user, date.today(), date.today())
    lines.append(f"\nToday so far: sales {naira(s['sales'])} | "
                 f"expenses {naira(s['expenses'])} | profit {naira(s['profit'])}")
    return "\n".join(lines)


def summary_message(s: dict, focus: str = "all") -> str:
    period = "Today" if s["start"] == s["end"] else f"{s['start']} to {s['end']}"

    if focus == "owed_to_me":
        if s["owed_to_me"] <= 0:
            return f"\U0001f389 Good news: nobody dey owe you as of {s['end']}."
        lines = [f"\U0001f9fe People dey owe you {naira(s['owed_to_me'])} as of {s['end']}:"]
        for name, amt in s.get("debtors", []):
            lines.append(f"• {name}: {naira(amt)}")
        return "\n".join(lines)

    if focus == "i_owe":
        if s["i_owe"] <= 0:
            return f"\U0001f389 You no owe anybody as of {s['end']}. Clean book!"
        lines = [f"\U0001f4cb You dey owe {naira(s['i_owe'])} as of {s['end']}:"]
        for name, amt in s.get("creditors", []):
            lines.append(f"• {name}: {naira(amt)}")
        return "\n".join(lines)

    if focus == "profit":
        return (f"\U0001f4b5 Profit for {period}: {naira(s['profit'])}\n"
                f"(Sales {naira(s['sales'])}, expenses {naira(s['expenses'])}, "
                f"{s['count']} transactions)")

    if focus == "sales":
        lines = [f"\U0001f4b0 Sales for {period}: {naira(s['sales'])}"]
        if s["top_item"]:
            lines.append(f"Best seller: {s['top_item']}")
        if s["by_method"]:
            parts = ", ".join(f"{METHOD_LABEL.get(m, m)} {naira(v)}"
                              for m, v in s["by_method"].items())
            lines.append(f"By payment: {parts}")
        return "\n".join(lines)

    if focus == "expenses":
        lines = [f"\U0001f4b8 Expenses for {period}: {naira(s['expenses'])}"]
        if s["biggest_expense"]:
            b = s["biggest_expense"]
            lines.append(f"Biggest: {b['item']} ({naira(b['amount'])})")
        return "\n".join(lines)

    # focus == "all"
    if s["count"] == 0 and s["owed_to_me"] <= 0 and s["i_owe"] <= 0:
        return f"\U0001f4ca {period}: no transactions recorded yet. " \
               "Send me your sales as you make them!"
    lines = [
        f"\U0001f4ca Your summary for {period}",
        f"Sales: {naira(s['sales'])}",
        f"Expenses: {naira(s['expenses'])}",
        f"Profit: {naira(s['profit'])}",
        f"Transactions: {s['count']}",
    ]
    if s["top_item"]:
        lines.append(f"Best seller: {s['top_item']}")
    if s["owed_to_me"] > 0:
        lines.append(f"People owe you: {naira(s['owed_to_me'])}")
    if s["i_owe"] > 0:
        lines.append(f"You owe: {naira(s['i_owe'])}")
    return "\n".join(lines)
