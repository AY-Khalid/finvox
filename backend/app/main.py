from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routes import api, dev, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mode = "console-mode (no WhatsApp token)" if not settings.WHATSAPP_TOKEN else "live WhatsApp"
    ai = "Gemini live" if settings.GEMINI_API_KEY else "MOCK parser (no Gemini key)"
    print(f"Finvox backend up: {mode} | {ai} | db={settings.DATABASE_URL.split('://')[0]}")
    if settings.WHATSAPP_TOKEN and not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("WARNING: WHATSAPP_TOKEN is set but WHATSAPP_PHONE_NUMBER_ID is empty. "
              "Replies will fail to send. Paste your Phone number ID from "
              "Meta dashboard > WhatsApp > API Setup into backend/.env.")
    yield


app = FastAPI(title="Finvox API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ledger tokens are unguessable; tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(api.router)
app.include_router(dev.router)


@app.get("/")
def root():
    return {"app": "Finvox", "docs": "/docs"}
