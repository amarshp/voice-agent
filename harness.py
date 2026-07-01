"""Local call simulator — plays a scripted conversation through the REAL tools.

No phone, no LLM, no external keys. A tiny rule-based router stands in for the LLM
so you can watch the full booking flow (FAQ -> book -> list -> reject -> transfer)
and confirm the reservation actually lands in the store.

Run:  python harness.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))

# Use a throwaway store so the demo is repeatable.
os.environ.setdefault("STORE", "json")
os.environ.setdefault("BOOKINGS_PATH", "data/demo_bookings.json")
Path("data").mkdir(exist_ok=True)
Path(os.environ["BOOKINGS_PATH"]).write_text("[]", encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402
import app as app_module  # noqa: E402
from tools import config  # noqa: E402

client = TestClient(app_module.app)
CFG = config()
PHONE = "+919812345678"


def tomorrow(hour: int) -> str:
    d = (datetime.now() + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0)
    return d.isoformat(timespec="seconds")


def caller(line: str) -> None:
    print(f"\n\033[36mCaller:\033[0m {line}")


def agent(line: str) -> None:
    print(f"\033[32m Agent:\033[0m {line}")


def tool(name: str, args: dict) -> dict:
    """What the LLM would do: call a tool, get the envelope back."""
    r = client.post("/tools/dispatch", json={"name": name, "arguments": args}).json()
    print(f"   \033[90m↳ tool {name}({args}) -> ok={r['ok']}\033[0m")
    return r


def faq_hours() -> str:
    hrs = "; ".join(f"{k} {v}" for k, v in CFG["hours"].items())
    return f"We're open {hrs}."


def faq_menu() -> str:
    first = CFG["menu"][0]
    picks = ", ".join(i["name"] for i in first["items"][:3])
    return f"Popular ones are {picks}. Want me to run through the full menu?"


def main() -> None:
    print("=" * 64)
    print(f"  {CFG['name']} — simulated inbound call (tools are REAL)")
    print("=" * 64)

    agent(f"Thanks for calling {CFG['name']}, how can I help you?")

    # 1) FAQ — no tool needed (LLM answers from system prompt)
    caller("Hi, what time do you guys open?")
    agent(faq_hours())

    caller("Nice, what's good on the menu?")
    agent(faq_menu())

    # 2) Booking — LLM collects details then calls the tool
    caller("Can I book a table for 4 tomorrow at 8 in the evening? Name's Amarsh.")
    agent("Sure Amarsh — what's a good phone number for the booking?")
    caller("98123 45678")
    r = tool("book_appointment", {
        "name": "Amarsh", "phone": PHONE, "party_size": 4,
        "start_time": tomorrow(20)})
    agent(r["message"])

    # 3) Read back existing bookings
    caller("Can you just confirm what you've got for me?")
    r = tool("list_bookings", {"phone": PHONE})
    if r["data"]:
        bk = r["data"][0]
        agent(f"Yes — table for {bk['party_size']} at {bk['start_time']}, "
              f"reference {bk['id']}. See you then!")
    else:
        agent("Hmm, I don't see anything under that number.")

    # 4) Rejected booking — business rule (3 AM is outside hours)
    caller("Actually can I also book one for 3 AM tonight?")
    r = tool("book_appointment", {
        "name": "Amarsh", "phone": PHONE, "party_size": 2,
        "start_time": tomorrow(3)})
    agent(r["message"] + " Would something in the evening work instead?")

    # 5) Escalation — transfer to a human
    caller("No worries. Actually I want to plan a big office party, 40 people.")
    r = tool("transfer_call", {"reason": "large event / catering enquiry"})
    agent(r["message"])

    print("\n" + "=" * 64)
    print(f"  Store file: {os.environ['BOOKINGS_PATH']}  (booking persisted ✔)")
    print("=" * 64)


if __name__ == "__main__":
    main()
