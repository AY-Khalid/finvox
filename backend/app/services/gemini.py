"""Gemini AI service (v3): turns free-form text or voice notes (English, Pidgin,
Hausa, Yoruba, Igbo) into structured ledger data.

Privacy rule: audio bytes are processed in memory and NEVER written to disk
or the database. Only the extracted text is saved.
"""
import json
import re
from datetime import date

from ..config import settings

SYSTEM_PROMPT = """You are Finvox, an AI bookkeeper for Nigerian informal traders.
Today's date is {today}.

The user sends WhatsApp messages (text or voice) in English, Nigerian Pidgin,
Hausa, Yoruba or Igbo. Amounts are in Nigerian Naira unless stated otherwise.
Words like "k" mean thousand (e.g. "5k" = 5000).

Classify the message and respond ONLY with valid JSON in this exact shape:

{{
  "intent": "log" | "summary" | "stock_update" | "other",
  "transcript": "<what the user said, transcribed if audio, in original language>",
  "transactions": [
    {{
      "type": "sale" | "expense",
      "payment_method": "cash" | "transfer" | "pos" | "owed",
      "category": "<for expenses only: 'stock' or 'operating', else null>",
      "counterparty": "<name of the customer or supplier if mentioned, else null>",
      "item": "<short item description in English>",
      "quantity": <number or null>,
      "unit_price": <number or null>,
      "amount": <total number>,
      "date": "<YYYY-MM-DD, default today>"
    }}
  ],
  "start_date": "<YYYY-MM-DD or null>",
  "end_date": "<YYYY-MM-DD or null>",
  "summary_focus": "all" | "profit" | "sales" | "expenses" | "owed_to_me" | "i_owe",
  "stock_value": <number or null, only for intent "stock_update">,
  "reply": "<only for intent 'other': a short friendly reply in the user's language>"
}}

Rules:
- intent "log": the user reports sales, purchases, expenses or money spent.
  Extract EVERY transaction mentioned. Money received/sold = "sale".
  Money spent/bought stock/transport/expenses = "expense".
  If unit price and quantity are given, amount = quantity * unit_price.
- payment_method: "cash" unless stated otherwise. "transfer"/"alert"/"send am
  to my account" = transfer. "POS"/"machine"/"card" = pos. If the customer has
  NOT paid yet ("credit", "im go pay later", "dem dey owe me", "I borrow am") = "owed".
- category (expenses only): "stock" if buying goods to resell ("I buy 10 bags
  of rice for my shop", "bought stock 20k"). "operating" for running costs
  (fuel, transport, rent, data, food, repairs). null for sales.
- intent "stock_update": the user states the current value of goods they have
  ("my stock worth 80k", "goods remaining for shop na 50,000"). Set
  stock_value to that number. transactions must be [].
- counterparty: if a person or business name is mentioned ("Mama Ngozi take
  2 paint of garri, she go pay later", "I buy stock from Alhaji Musa"),
  capture the name exactly as said ("Mama Ngozi", "Alhaji Musa"). This is
  VERY important for "owed" transactions so the trader knows who owes who.
  null if no name is mentioned.
- intent "summary": the user asks for a report/summary/how much they made
  ("how my market today?", "send my account for last week"). Fill start_date
  and end_date (for "today" both are today; "this week" = Monday to today;
  "since last week Monday" = Monday of the PREVIOUS week to today).
  Set summary_focus:
  * "owed_to_me": who owes them / unpaid credit sales ("how much people dey
    owe me?", "wetin dem never pay me?")
  * "i_owe": what they owe others ("how much I dey owe?", "my debt nko?")
  * "profit": profit questions ("how much profit since last week Monday?")
  * "sales": sales only. "expenses": spending only ("wetin I don spend?")
  * "all": general ("how my market?", "send my summary")
- intent "other": greetings, questions, anything else. Write a short helpful
  reply in their language explaining what Finvox can do.
- transactions must be [] unless intent is "log".
- Never invent amounts. If no clear amount, use intent "other" and ask politely.
"""


def _client():
    from google import genai
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _extract_json(text: str) -> dict:
    """Parse JSON even if the model wraps it in markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    return json.loads(text)


def _mock_parse(text: str) -> dict:
    """Offline fallback when GEMINI_API_KEY is empty (local testing only).
    Understands simple patterns like 'sold rice 5000' / 'bought fuel 2k'."""
    t = (text or "").lower()
    if any(w in t for w in ("summary", "report", "account", "how much", "how my")):
        today = date.today().isoformat()
        focus = "all"
        if "owe me" in t:
            focus = "owed_to_me"
        elif "i owe" in t or "my debt" in t:
            focus = "i_owe"
        elif "profit" in t:
            focus = "profit"
        return {"intent": "summary", "transcript": text, "transactions": [],
                "start_date": today, "end_date": today,
                "summary_focus": focus, "reply": None}
    m = re.search(r"(sold|sell|bought|buy|spent|spend)\s+(.+?)\s+(?:for\s+)?(?:₦|n)?([\d,]+(?:\.\d+)?)\s*(k)?", t)
    if m:
        verb, item, num, k = m.groups()
        amount = float(num.replace(",", "")) * (1000 if k else 1)
        ttype = "sale" if verb in ("sold", "sell") else "expense"
        method = "transfer" if "transfer" in t else ("pos" if "pos" in t else
                 ("owed" if ("credit" in t or "owe" in t) else "cash"))
        nm = re.search(r"(?:from|to)\s+((?:[A-Z][a-z]+\s?){1,3})", text or "")
        cat = None
        if ttype == "expense":
            cat = "stock" if "stock" in item else "operating"
        return {"intent": "log", "transcript": text,
                "transactions": [{"type": ttype, "item": item.strip(), "quantity": None,
                                  "unit_price": None, "amount": amount,
                                  "payment_method": method, "category": cat,
                                  "counterparty": nm.group(1).strip() if nm else None,
                                  "date": date.today().isoformat()}],
                "start_date": None, "end_date": None, "reply": None}
    mw = re.search(r"(?:stock|goods|inventory)\s+(?:worth|na|is|remain\w*)\s*(?:₦|n)?([\d,]+(?:\.\d+)?)\s*(k)?", t)
    if mw:
        val = float(mw.group(1).replace(",", "")) * (1000 if mw.group(2) else 1)
        return {"intent": "stock_update", "transcript": text, "transactions": [],
                "start_date": None, "end_date": None, "stock_value": val, "reply": None}
    return {"intent": "other", "transcript": text, "transactions": [],
            "start_date": None, "end_date": None,
            "reply": "[MOCK MODE - no GEMINI_API_KEY set] Hi! Tell me what you sold or "
                     "bought, e.g. 'sold rice 5000', or ask for a 'summary'."}


def parse_message(text: str | None = None,
                  audio_bytes: bytes | None = None,
                  audio_mime: str | None = None) -> dict:
    """Send text or audio to Gemini and get structured intent + transactions.

    For audio: bytes stay in memory; caller must not persist them.
    """
    if not settings.GEMINI_API_KEY:
        return _mock_parse(text or "")

    from google.genai import types

    system = SYSTEM_PROMPT.format(today=date.today().isoformat())
    if audio_bytes is not None:
        contents = [
            types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime or "audio/ogg"),
            "Process this voice note per your instructions.",
        ]
    else:
        contents = [text or ""]

    client = _client()
    resp = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    try:
        data = _extract_json(resp.text)
    except (json.JSONDecodeError, TypeError):
        data = {"intent": "other", "transcript": text or "(voice note)",
                "transactions": [], "start_date": None, "end_date": None,
                "reply": "Sorry, I no fit understand that one. Try talk am again, "
                         "e.g. 'I sell 5 crates of egg, 3000 naira each'."}
    data.setdefault("transactions", [])
    return data
