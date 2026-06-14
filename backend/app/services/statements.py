"""Builds a simplified but complete set of financial statements from
recorded transactions:

- Income Statement (accrual basis: credit sales count as revenue)
- Cash Flow Statement (cash basis: only money actually received/paid)
- Balance Sheet (cash + receivables vs payables + owner's equity)

Assumptions, disclosed to the user: no opening balances before the first
recorded transaction, no inventory valuation, no depreciation. Statements
are prepared from the trader's own records and are unaudited.
"""
from datetime import date

from sqlalchemy.orm import Session

from ..models import Transaction, User
from .ledger import latest_snapshot

PAID = {"cash", "transfer", "pos"}
TOP_N = 8
METHOD_LABEL = {"cash": "Cash", "transfer": "Bank transfer", "pos": "POS"}


def _group_items(txns) -> list[dict]:
    g: dict[str, float] = {}
    for t in txns:
        key = t.item.strip().capitalize() if t.item else "Other"
        g[key] = g.get(key, 0.0) + t.amount
    items = sorted(g.items(), key=lambda kv: kv[1], reverse=True)
    out = [{"label": k, "amount": round(v, 2)} for k, v in items[:TOP_N]]
    other = sum(v for _, v in items[TOP_N:])
    if other > 0:
        out.append({"label": "Other items", "amount": round(other, 2)})
    return out


def _net_cash(txns) -> float:
    n = 0.0
    for t in txns:
        if (t.payment_method or "cash") in PAID:
            n += t.amount if t.type == "sale" else -t.amount
    return n


def build_statements(db: Session, user: User, start: date, end: date) -> dict:
    base = db.query(Transaction).filter(Transaction.user_id == user.id)
    in_range = base.filter(Transaction.txn_date >= start,
                           Transaction.txn_date <= end).all()
    before = base.filter(Transaction.txn_date < start).all()
    upto_end = base.filter(Transaction.txn_date <= end).all()

    sales = [t for t in in_range if t.type == "sale"]
    expenses = [t for t in in_range if t.type != "sale"]

    # ---------- Income Statement (accrual, with trading account) ----------
    revenue_total = sum(t.amount for t in sales)
    credit_sales = sum(t.amount for t in sales
                       if (t.payment_method or "cash") == "owed")

    stock_purchases = [t for t in expenses if (t.category or "") == "stock"]
    operating = [t for t in expenses if (t.category or "") != "stock"]
    stock_purchases_total = round(sum(t.amount for t in stock_purchases), 2)
    operating_total = round(sum(t.amount for t in operating), 2)

    # Inventory: trader-reported snapshots ("my stock worth 80k")
    open_snap = latest_snapshot(db, user, strictly_before=start)
    close_snap = latest_snapshot(db, user, on_or_before=end)
    opening_inventory = round(open_snap.value, 2) if open_snap else 0.0
    has_closing = close_snap is not None and (
        open_snap is None or close_snap.id != open_snap.id)
    if has_closing:
        closing_inventory = round(close_snap.value, 2)
    else:
        # No fresh stock count this period: assume purchases were sold.
        closing_inventory = opening_inventory
    cogs = round(max(opening_inventory + stock_purchases_total - closing_inventory, 0.0), 2)
    gross_profit = round(revenue_total - cogs, 2)
    net_profit = round(gross_profit - operating_total, 2)

    income_statement = {
        "revenue_items": _group_items(sales),
        "revenue_total": round(revenue_total, 2),
        "of_which_credit_sales": round(credit_sales, 2),
        "cogs": {
            "opening_inventory": opening_inventory,
            "stock_purchases": stock_purchases_total,
            "closing_inventory": closing_inventory,
            "total": cogs,
        },
        "gross_profit": gross_profit,
        "expense_items": _group_items(operating),
        "expense_total": operating_total,
        "net_profit": net_profit,
    }

    # ---------- Cash Flow Statement (cash basis) ----------
    inflows = []
    for m in ("cash", "transfer", "pos"):
        amt = sum(t.amount for t in sales if (t.payment_method or "cash") == m)
        if amt > 0:
            inflows.append({"label": f"Sales received by {METHOD_LABEL[m]}",
                            "amount": round(amt, 2)})
    cash_in = round(sum(i["amount"] for i in inflows), 2)
    cash_out = round(sum(t.amount for t in expenses
                         if (t.payment_method or "cash") in PAID), 2)
    opening_cash = round(_net_cash(before), 2)
    net_flow = round(cash_in - cash_out, 2)
    cash_flow = {
        "opening_cash": opening_cash,
        "inflows": inflows,
        "cash_in": cash_in,
        "cash_out": cash_out,
        "net_cash_flow": net_flow,
        "closing_cash": round(opening_cash + net_flow, 2),
    }

    # ---------- Balance Sheet (as of end date) ----------
    receivables = round(sum(t.amount for t in upto_end
                            if t.type == "sale"
                            and (t.payment_method or "cash") == "owed"), 2)
    payables = round(sum(t.amount for t in upto_end
                         if t.type != "sale"
                         and (t.payment_method or "cash") == "owed"), 2)
    cash_position = cash_flow["closing_cash"]
    total_assets = round(cash_position + receivables + closing_inventory, 2)
    equity = round(total_assets - payables, 2)
    balance_sheet = {
        "as_of": end.isoformat(),
        "cash": cash_position,
        "receivables": receivables,
        "inventory": closing_inventory,
        "total_assets": total_assets,
        "payables": payables,
        "total_liabilities": payables,
        "equity": equity,
    }

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "prepared_on": date.today().isoformat(),
        "business": user.name or f"Trader {user.phone[-4:]}",
        "transaction_count": len(in_range),
        "income_statement": income_statement,
        "cash_flow": cash_flow,
        "balance_sheet": balance_sheet,
        "notes": [
            "Prepared automatically from transactions recorded on Finvox.",
            "Income statement uses accrual basis: credit sales are counted as revenue.",
            "Cost of goods sold = opening inventory + stock purchases - closing inventory. "
            "Inventory values are as reported by the trader (e.g. 'my stock worth 80k').",
            "If no stock count was reported in the period, closing inventory is assumed "
            "equal to opening inventory (all purchases treated as sold).",
            "Cash flow uses cash basis: only money actually received or paid.",
            "No opening balances before the first recorded transaction.",
            "These statements are unaudited.",
        ],
    }
