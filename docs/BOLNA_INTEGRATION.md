# Phase 2 — wire our tools into bolna (orchestrator)

bolna runs the voice loop (telephony → STT → LLM → TTS → turn-taking) and calls our
tool webhooks by LLM function-calling. We do **not** rewrite any of that — we generate
its agent config from our existing schemas + prompt and point it at our service.

## How the pieces map (verified against bolna source)
| bolna config | our side |
|---|---|
| `api_tools.tools` | `src/schemas.TOOL_SCHEMAS` (identical OpenAI format) |
| `api_tools.tools_params[name]` | `{url: <base>/tools/<name>, method: POST, param: $var map}` |
| `agent_prompts.task_1.system_prompt` | `src/prompt.build_system_prompt()` |
| `transcriber / synthesizer / llm_agent` | Deepgram / Sarvam / Gemini (all built-in) |

bolna POSTs JSON to our webhook, substituting the LLM's arguments into the `$var`
markers → the body matches our `BookRequest` etc. exactly. No adapter needed.

## Gotcha: the SSRF guard
bolna's `validate_outbound_url` **blocks localhost / private IPs** for tool calls.
So our tool service must be reachable at a **public URL**. Two options:
- **ngrok** (simplest): `ngrok http 8000` → use the https URL as `WEBHOOK_BASE`.
- Or set `BOLNA_TOOL_URL_HOST_ALLOWLIST=host.docker.internal` on the bolna side and
  point the webhook at `host.docker.internal:8000`.

## Runbook

**1. Run our tool service (public).**
```bash
.venv/Scripts/python -m uvicorn app:app --app-dir src --port 8000
ngrok http 8000        # copy the https URL
```

**2. Generate the agent payload** (single source of truth):
```bash
WEBHOOK_BASE=https://<your-ngrok>.ngrok.app \
STT_PROVIDER=deepgram LLM_PROVIDER=gemini TELEPHONY=twilio \
.venv/Scripts/python scripts/build_bolna_agent.py      # writes bolna_agent.json
```
Set `SARVAM_VOICE/_VOICE_ID/_MODEL` to your real Sarvam Bulbul voice (defaults are
placeholders — verify in the Sarvam console).

**3. Bring up bolna** (from the cloned repo):
```bash
cd bolna/local_setup
cp .env.sample .env        # add DEEPGRAM_AUTH_TOKEN, SARVAM_API_KEY, GEMINI/OPENAI key,
                           # Twilio creds, REDIS, etc.
docker compose up          # starts bolna server + redis + telephony workers
```

**4. Create the agent:**
```bash
curl -X POST http://localhost:5001/agent \
  -H "Content-Type: application/json" \
  -d @bolna_agent.json
# -> returns an agent_id
```

**5. Talk to it.**
- **Text first** (no phone/keys for voice): use bolna's text/websocket client
  (`local_setup/quickstart_client.py`) against the agent_id — confirm a booking flows
  through to our store / Google Sheet.
- **Voice demo:** attach a **free Twilio US number** to the agent (no India KYC) and
  call it. Swap to an **Exotel +91** number (Udyam KYC) for the real India demo later.

## What "done" looks like for Phase 2
A call/text where: caller asks hours → answered from prompt; books a table → row lands
in the Google Sheet; asks to confirm → read back; asks for a person → transfer fires.
That's the same flow `harness.py` already proves locally — Phase 2 just puts real
voice + telephony in front of it.

## Notes
- Keep `book_appointment`'s idempotency: bolna may retry a tool on transient errors;
  our hash-based IDs already dedupe.
- `transfer_call` returns the target number; the actual dial/bridge is bolna's
  transfer mechanism on the telephony leg (configure the transfer number there too).
- LLM: demo uses Gemini (BYOK, US-routed — fine for a US demo). For India-routed
  production via hosted bolna you'd switch to Azure OpenAI; self-hosted has no such limit.
