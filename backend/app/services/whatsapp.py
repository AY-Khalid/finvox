"""WhatsApp Cloud API client.

Console mode: if WHATSAPP_TOKEN is empty, outgoing messages are printed to the
terminal instead of sent, so you can develop with zero WhatsApp setup.
"""
import httpx

from ..config import settings

GRAPH = "https://graph.facebook.com"


def _base() -> str:
    return f"{GRAPH}/{settings.WHATSAPP_API_VERSION}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}


async def send_text(to: str, body: str) -> None:
    if not settings.WHATSAPP_TOKEN:
        print(f"\n[console-mode WhatsApp] -> {to}:\n{body}\n")
        return
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:4096]},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_base()}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers=_headers(), json=payload,
        )
        if r.status_code >= 400:
            print(f"[whatsapp] send failed {r.status_code}: {r.text}")


async def download_media(media_id: str) -> tuple[bytes, str]:
    """Fetch a voice note. Returns (bytes, mime_type). Bytes are kept in
    memory only, never written to disk (privacy requirement)."""
    async with httpx.AsyncClient(timeout=60) as client:
        meta = await client.get(f"{_base()}/{media_id}", headers=_headers())
        meta.raise_for_status()
        info = meta.json()
        media = await client.get(info["url"], headers=_headers())
        media.raise_for_status()
        return media.content, info.get("mime_type", "audio/ogg")
