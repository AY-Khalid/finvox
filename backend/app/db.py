# v3: counterparty migration
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (register models)
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """Tiny in-place migration for columns added after first release."""
    from sqlalchemy import text
    stmts = [
        "ALTER TABLE transactions ADD COLUMN payment_method VARCHAR(16) DEFAULT 'cash'",
        "ALTER TABLE transactions ADD COLUMN counterparty VARCHAR(120)",
        "ALTER TABLE transactions ADD COLUMN category VARCHAR(16)",
    ]
    with engine.connect() as conn:
        for s in stmts:
            try:
                conn.execute(text(s))
                conn.commit()
            except Exception:
                pass  # column already exists
