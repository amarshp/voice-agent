"""Request/response models + the tool schemas the LLM calls."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class BookRequest(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=6)
    party_size: int = Field(..., ge=1)
    # Local start time, ISO 8601 e.g. "2026-07-02T20:00:00".
    start_time: str
    notes: str | None = None

    @field_validator("start_time")
    @classmethod
    def _valid_iso(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"start_time must be ISO 8601: {e}") from e
        return v


class Booking(BaseModel):
    id: str
    name: str
    phone: str
    party_size: int
    start_time: str
    status: str = "confirmed"      # confirmed | cancelled
    notes: str | None = None
    created_at: str


class ListRequest(BaseModel):
    phone: str | None = None       # filter by caller; None = all upcoming
    date: str | None = None        # YYYY-MM-DD filter


class TransferRequest(BaseModel):
    reason: str | None = None


# Tool schemas exposed to the LLM (OpenAI/Bolna/Vapi function-calling format).
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Reserve a table. Confirm name, phone, party size, and a "
                           "specific date+time with the caller before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "start_time": {
                        "type": "string",
                        "description": "ISO 8601 local, e.g. 2026-07-02T20:00:00",
                    },
                    "notes": {"type": "string"},
                },
                "required": ["name", "phone", "party_size", "start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_bookings",
            "description": "Look up existing reservations, optionally filtered by the "
                           "caller's phone or a date (YYYY-MM-DD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "date": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Escalate to a human staff member when the caller asks for a "
                           "person or has a request you cannot handle.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
]
