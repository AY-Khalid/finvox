"""WhatsApp Cloud API webhook endpoints."""
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..services import whatsapp
from ..services.handler import handle_incoming

router = APIRouter()


@router.get("/webhook")
async def verify(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    """Meta calls this once when you register the webhook URL."""
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhook")
async def receive(request: Request, db: Session = Depends(get_db)):
    """Inbound WhatsApp messages. Always returns 200 fast so Meta doesn't retry."""
    body = await request.json()
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = {c["wa_id"]: c.get("profile", {}).get("name")
                            for c in value.get("contacts", [])}
                for msg in value.get("messages", []):
                    phone = msg.get("from")
                    name = contacts.get(phone)
                    mtype = msg.get("type")

                    if mtype == "text":
                        reply = await handle_incoming(
                            db, phone, text=msg["text"]["body"], name=name)
                    elif mtype in ("audio", "voice"):
                        media_id = msg.get("audio", {}).get("id")
                        audio, mime = await whatsapp.download_media(media_id)
                        # Audio stays in memory; handler discards it after parsing.
                        reply = await handle_incoming(
                            db, phone, audio_bytes=audio, audio_mime=mime, name=name)
                        del audio  # destroyed; only extracted text was saved
                    else:
                        reply = ("For now I understand text and voice notes. "
                                 "Try: \"I sell 5 crates of egg, 3000 each\"")

                    await whatsapp.send_text(phone, reply)
    except Exception as e:  # never let an error cause Meta retry storms
        print(f"[webhook] error: {e}")
    return {"status": "ok"}
