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


def menu_categories() -> list[str]:
    """Short category names for the menu overview."""
    return [s["section"].split(" (")[0].strip() for s in config().get("menu", [])]


def menu_lookup(query: str) -> list[dict]:
    """Return menu items matching a dish name / category / keyword. Small slice so the
    tool result stays cheap in the LLM context (menu-as-tool to keep the prompt tiny)."""
    q = (query or "").strip().lower()
    veg = q in ("veg", "vegetarian", "veg options", "vegetarian options", "pure veg")
    out: list[dict] = []
    for sec in config().get("menu", []):
        sec_name = sec["section"]
        sec_match = bool(q) and q in sec_name.lower()
        for it in sec["items"]:
            name, desc = it["name"], str(it.get("desc", ""))
            hay = f"{name} {desc} {sec_name}".lower()
            if veg:
                ok = ("veg" in desc.lower()) and ("non-veg" not in desc.lower())
            else:
                ok = sec_match or (bool(q) and all(w in hay for w in q.split()))
            if ok:
                out.append({
                    "name": name,
                    "price": it.get("price"),
                    "desc": it.get("desc"),
                    "category": sec_name.split(" (")[0].strip(),
                })
    return out


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
