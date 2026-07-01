"""Business logic for the agent tools: config load + booking validation."""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from schemas import BookRequest

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "business.yaml"


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


class BookingError(ValueError):
    """Raised when a booking violates business rules (caller-facing message)."""


def validate_booking(req: BookRequest, now: datetime) -> datetime:
    """Check a booking against config rules. Return parsed start time or raise."""
    b = config()["booking"]
    start = datetime.fromisoformat(req.start_time)

    if req.party_size > b["max_party_size"]:
        raise BookingError(
            f"we can only seat up to {b['max_party_size']} on a single reservation"
        )
    if start < now:
        raise BookingError("that time is in the past")
    if start > now + timedelta(days=b["max_days_ahead"]):
        raise BookingError(f"we take bookings up to {b['max_days_ahead']} days ahead")
    if not (b["open_hour"] <= start.hour <= b["close_hour"]):
        raise BookingError(
            f"our booking hours are {b['open_hour']}:00 to {b['close_hour']}:00"
        )
    return start
