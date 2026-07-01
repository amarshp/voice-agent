"""Tool webhooks the voice agent (Bolna/Vapi) calls during a call.

Endpoints return small JSON the LLM can read back to the caller. Every response
uses a consistent envelope: {ok, message, data}.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import ValidationError

load_dotenv()  # read .env (STORE/SHEET_ID/GOOGLE_SERVICE_ACCOUNT_JSON); no-op if absent

from schemas import BookRequest, ListRequest, TransferRequest
from store import get_store
from tools import BookingError, config, validate_booking

app = FastAPI(title="California Burrito Voice Agent — Tools")
store = get_store()


def _now() -> datetime:
    tz = ZoneInfo(config().get("timezone", "Asia/Kolkata"))
    return datetime.now(tz).replace(tzinfo=None)


def envelope(ok: bool, message: str, data=None) -> dict:
    return {"ok": ok, "message": message, "data": data}


@app.get("/health")
def health() -> dict:
    return envelope(True, "up", {"store": type(store).__name__})


@app.post("/tools/book_appointment")
def book_appointment(req: BookRequest) -> dict:
    try:
        validate_booking(req, _now())
    except BookingError as e:
        return envelope(False, f"Sorry, {e}.")
    booking, created = store.add(req, created_at=_now().isoformat())
    if not created:
        return envelope(
            True, "That reservation is already on our books.",
            booking.model_dump(),
        )
    return envelope(
        True,
        f"Booked for {booking.name}, party of {booking.party_size}, "
        f"at {booking.start_time}. Reference {booking.id}.",
        booking.model_dump(),
    )


@app.post("/tools/list_bookings")
def list_bookings(req: ListRequest) -> dict:
    rows = store.list(phone=req.phone, date=req.date)
    if not rows:
        return envelope(True, "No reservations found.", [])
    return envelope(
        True, f"Found {len(rows)} reservation(s).",
        [b.model_dump() for b in rows],
    )


@app.post("/tools/transfer_call")
def transfer_call(req: TransferRequest) -> dict:
    number = config().get("transfer_number")
    # The orchestrator performs the actual dial/transfer; we return the target.
    return envelope(
        True, "Transferring you to a team member now, please hold.",
        {"transfer_to": number, "reason": req.reason},
    )


# Some orchestrators post {name, arguments} to a single webhook. Support that too.
@app.post("/tools/dispatch")
def dispatch(payload: dict) -> dict:
    name = payload.get("name") or payload.get("tool")
    args = payload.get("arguments") or payload.get("args") or {}
    try:
        if name == "book_appointment":
            return book_appointment(BookRequest(**args))
        if name == "list_bookings":
            return list_bookings(ListRequest(**args))
        if name == "transfer_call":
            return transfer_call(TransferRequest(**args))
    except ValidationError as e:
        return envelope(False, "Missing or invalid details.", {"errors": e.errors()})
    return envelope(False, f"Unknown tool: {name}")
