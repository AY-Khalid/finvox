# Finvox — Your AI Bookkeeping Padi 🎤📒

Voice-first AI bookkeeping for Nigerian informal traders, built for the **OPay National Innovation Challenge 2026**.

A trader sends a WhatsApp text or voice note ("I sell 5 crates of egg, 3000 naira each" — in English, Pidgin, Hausa, Yoruba or Igbo). Gemini AI extracts the transaction, logs it to their ledger, and replies with a confirmation + running profit. First-time users automatically get an account and a private link to their bank-statement-style ledger (a Next.js PWA).

**Privacy:** voice notes are processed in memory and destroyed immediately. Only the extracted text is stored.

## Stack ($0 to run)

| Layer | Tech | Cost |
|---|---|---|
| Backend | FastAPI + SQLAlchemy | free |
| AI | Google Gemini API (`gemini-2.5-flash`) | free tier |
| DB | SQLite (local) → Supabase Postgres (prod) | free |
| Messaging | WhatsApp Cloud API (Meta test number) | free |
| Frontend/PWA | Next.js 15 | free |
| Hosting | Vercel (frontend) + Render (backend) | free |

---

## 1. Run locally

### Backend (Python 3.11+)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env → paste your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

You should see: `Finvox backend up — console-mode (no WhatsApp token) | Gemini live | db=sqlite`

### Frontend

```powershell
cd frontend
pnpm install
copy .env.local.example .env.local
pnpm dev
```

Open http://localhost:3000 — landing page. (API docs: http://localhost:8000/docs)

---

## 2. Test WITHOUT WhatsApp (dev simulator)

The backend has a simulator endpoint so you can test the entire flow before touching Meta. In a new terminal (or use the Swagger UI at `/docs`):

```powershell
curl -X POST http://localhost:8000/dev/simulate -H "Content-Type: application/json" -d "{\"phone\": \"2348012345678\", \"name\": \"Khalid\", \"text\": \"I sell 5 crates of egg, 3000 naira each\"}"
```

Expected: a JSON reply containing "✅ Recorded", today's totals, and (first message only) a welcome + ledger link like `http://localhost:3000/ledger/AbC123...`. **Open that link in the browser** — you'll see the bank-statement table.

More tests:

```powershell
# expense
curl -X POST http://localhost:8000/dev/simulate -H "Content-Type: application/json" -d "{\"phone\": \"2348012345678\", \"text\": \"I buy fuel 2k\"}"

# pidgin summary
curl -X POST http://localhost:8000/dev/simulate -H "Content-Type: application/json" -d "{\"phone\": \"2348012345678\", \"text\": \"how my market today?\"}"
```

If `GEMINI_API_KEY` is empty, a tiny built-in mock parser handles simple English patterns — useful for checking wiring, but use the real key for proper testing.

**PWA check:** in Chrome DevTools → Application → Manifest, or on your phone: open the site → menu → "Add to Home Screen". The ledger works offline after first load (cached by the service worker).

---

## 3. Connect real WhatsApp (free test number)

1. Go to https://developers.facebook.com → create an account → **Create App** → type **Business**.
2. In the app dashboard, **Add Product → WhatsApp → Set up**. Meta gives you:
   - a free **test phone number** (this is your Finvox number for now),
   - a **temporary access token** (expires ~24h; fine for dev),
   - the **Phone number ID**.
3. Under *API Setup*, add your own WhatsApp number to the **recipient list** (up to 5 test recipients, verified by SMS code). Team members' numbers too.
4. Put the token + phone number ID in `backend/.env`:
   ```
   WHATSAPP_TOKEN=EAAG...
   WHATSAPP_PHONE_NUMBER_ID=123456789012345
   ```
5. **Expose your local backend** so Meta can reach it. Easiest free option — no signup:
   ```powershell
   # install once: winget install Cloudflare.cloudflared
   cloudflared tunnel --url http://localhost:8000
   ```
   Copy the `https://....trycloudflare.com` URL it prints. (ngrok works too.)
6. In Meta dashboard → WhatsApp → **Configuration → Webhook**:
   - Callback URL: `https://YOUR-TUNNEL-URL/webhook`
   - Verify token: `finvox-verify-2026` (must match `WHATSAPP_VERIFY_TOKEN` in `.env`)
   - Click **Verify and save**, then **subscribe to the `messages` field**.
7. From your phone, WhatsApp the test number: *"I sell 3 bags of rice 15k"*. Finvox replies. Send a **voice note** — it works too, and the audio is never stored.
8. Update `frontend/.env.local` → `NEXT_PUBLIC_WHATSAPP_NUMBER` with the test number (digits only) so the landing page "Get Started" button opens the right chat.

**Going permanent (later, still free):** business verification on Meta + register your own number (a number NOT currently on WhatsApp — a cheap new SIM works) + generate a permanent token via System User. Replies to user-initiated messages (service conversations) are free.

---

## 4. Deploy for $0

**Database — Supabase:** create a project at https://supabase.com → Project Settings → Database → copy the **URI** connection string → set it as `DATABASE_URL` on the backend host. Tables are created automatically on first boot.

**Backend — Render:** push this repo to GitHub → https://render.com → New → Web Service → pick the repo, root dir `backend`:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `GEMINI_API_KEY`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `DATABASE_URL` (Supabase URI), `FRONTEND_URL` (your Vercel URL), `DEV_MODE=false`.
- Free tier sleeps after 15 min idle; first message after a nap takes ~30s. Acceptable for the demo; UptimeRobot (free) can ping `/api/health` every 10 min to keep it warm.
- Point the Meta webhook at `https://your-app.onrender.com/webhook` (replaces the tunnel).

**Frontend — Vercel:** import the repo → root dir `frontend` → framework Next.js → env vars `NEXT_PUBLIC_API_URL` (Render URL) and `NEXT_PUBLIC_WHATSAPP_NUMBER`. Done — PWA included.

**AWS:** not needed. Keep the $100 credit for scaling later.

---

## Project structure

```
backend/
  app/
    main.py            FastAPI app + CORS + startup
    config.py          env settings
    db.py, models.py   SQLAlchemy (User, Transaction)
    routes/
      webhook.py       WhatsApp webhook (verify + receive)
      api.py           /api/ledger/{token} for the PWA
      dev.py           /dev/simulate (local testing)
    services/
      gemini.py        AI parsing (text + voice, 5 languages)
      whatsapp.py      Cloud API client (console mode if no token)
      ledger.py        summaries, confirmations
      handler.py       core message flow + auto account creation
frontend/
  app/
    page.jsx           landing page (Get Started → wa.me link)
    ledger/[token]/    bank-statement ledger page
  public/
    manifest.json, sw.js, icons   PWA
```
