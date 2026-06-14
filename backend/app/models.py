# v3: counterparty column
import secrets
from datetime import datetime, date

from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_token() -> str:
    return secrets.token_urlsafe(16)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=new_token)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user", order_by="Transaction.created_at.desc()"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # "sale" | "expense"
    payment_method: Mapped[str] = mapped_column(String(16), default="cash")  # cash | transfer | pos | owed
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)  # expenses: "stock" | "operating"
    counterparty: Mapped[str | None] = mapped_column(String(120), nullable=True)  # customer/supplier name
    item: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float)  # total in naira
    raw_text: Mapped[str] = mapped_column(Text)   # extracted text ONLY (audio never stored)
    source: Mapped[str] = mapped_column(String(8), default="text")  # "text" | "voice"
    txn_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="transactions")


class InventorySnapshot(Base):
    """Trader-reported value of goods in stock, e.g. 'my stock worth 80k'."""
    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    value: Mapped[float] = mapped_column(Float)
    snap_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    """Anonymous in-app feedback collected from the landing-page popup."""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    page: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
