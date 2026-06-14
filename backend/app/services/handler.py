"""Core message handler, shared by the WhatsApp webhook and the dev simulator."""
from datetime import date, datetime

from sqlalchemy.orm import Session

from ..config import settings
from ..models import User
from . import gemini, ledger

WELCOME = (
    "\U0001f44b Welcome to *Finvox*, your AI bookkeeping padi!\n\n"
    "Just tell me your sales and expenses by text or voice note, in English, "
    "Pidgin, Hausa, Yoruba or Igbo. Example:\n"
    "_\"I sell 5 crates of egg, 3000 naira each\"_\n\n"
    "Ask me anytime: _\"how my market today?\"_\n\n"
    "\U0001f4d2 Your personal ledger (save this link):\n{link}"
)

HELP = (
    "I'm Finvox, your AI bookkeeper. You can:\n"
    "• Record: \"I sold 3 bags of rice for 15k\"\n"
    "• Record expense: \"I buy fuel 2000\"\n"
    "• Get summary: \"how much I make today?\"\n"
    "• Voice notes work too, just talk!"
)


def get_or_create_user(db: Session, phone: str, name: str | None = None) -> tuple[User, bool]:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user, False
    user = User(phone=phone, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def ledger_link(user: User) -> str:
    return f"{settings.FRONTEND_URL}/ledger/{user.token}"


def _parse_date(s: str | None) -> date | None:
    try:
        return datetime.strptime(s or "", "%Y-%m-%d").date()
    except ValueError:
        return None


async def handle_incoming(db: Session, phone: str,
                          text: str | None = None,
                          audio_bytes: bytes | None = None,
                          audio_mime: str | None = None,
                          name: str | None = None) -> str:
    """Process one inbound message, return the reply text.

    Privacy: audio_bytes are used for this single Gemini call and then
    discarded, never persisted anywhere.
    """
    user, is_new = get_or_create_user(db, phone, name)
    source = "voice" if audio_bytes is not None else "text"

    parsed = gemini.parse_message(text=text, audio_bytes=audio_bytes,
                                  audio_mime=audio_mime)
    # Explicitly drop audio reference; only extracted text survives.
    audio_bytes = None  # noqa: F841

    intent = parsed.get("intent")
    if intent == "log" and parsed.get("transactions"):
        saved = ledger.save_transactions(db, user, parsed, source)
        reply = ledger.confirmation_message(saved, db, user)
        if not is_new:
            reply += f"\n\n\U0001f4d2 Full ledger: {ledger_link(user)}"
    elif intent == "stock_update" and parsed.get("stock_value"):
        snap = ledger.save_snapshot(db, user, float(parsed["stock_value"]))
        reply = (f"\U0001f4e6 Noted! Stock value recorded: {ledger.naira(snap.value)} "
                 f"as of {snap.snap_date.isoformat()}.\n"
                 "This will appear as Inventory in your financial statements.")
    elif intent == "summary":
        start = _parse_date(parsed.get("start_date")) or date.today()
        end = _parse_date(parsed.get("end_date")) or date.today()
        focus = parsed.get("summary_focus") or "all"
        reply = ledger.summary_message(
            ledger.range_summary(db, user, start, end), focus)
        reply += f"\n\n\U0001f4d2 Full statement: {ledger_link(user)}"
    else:
        reply = parsed.get("reply") or HELP

    if is_new:
        reply = WELCOME.format(link=ledger_link(user)) + "\n\n" + reply
    return reply
