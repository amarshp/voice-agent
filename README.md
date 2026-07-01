# California Burrito — Voice Agent

Inbound Indian-English phone bot: answers FAQs (hours/menu), books & lists table
reservations, escalates to a human. Actions are plain HTTP tools the voice
orchestrator (bolna/Pipecat) calls via LLM function-calling.

See [STACK.md](STACK.md) for the full stack decision, telephony/KYC reality, and the
open-source repos we build on.

## What's built (Phase 1)
- **Tool service** (`src/app.py`) — FastAPI webhooks: `book_appointment`,
  `list_bookings`, `transfer_call`, plus a single `/tools/dispatch` endpoint.
- **Store** (`src/store.py`) — repository pattern, append-only, idempotent booking IDs.
  Local JSON for dev; Google Sheets in prod (flip `STORE=sheets`).
- **System prompt** (`src/prompt.py`) — built from `config/business.yaml`, ready to
  paste into the orchestrator.
- **Call simulator** (`harness.py`) — plays a scripted call through the real tools.
  No phone, no LLM, no keys.

## Run
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest        # 9 tests
.venv/Scripts/python harness.py       # watch a simulated call
.venv/Scripts/python src/prompt.py    # print the system prompt
```

## Configure
Edit `config/business.yaml` — hours, menu, booking rules, human transfer number.

## Next (Phase 2+)
Fork `bolna-ai/bolna`, register these three webhooks as its function tools, add Sarvam
TTS + Deepgram STT + LLM keys, connect an Exotel +91 number. Demo can run first on a
free US/test number — the number is not needed to build or test the agent.
