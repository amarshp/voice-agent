# Laptop quick-start — run bolna locally, take a real test call

Runs the whole voice bot from your laptop for a demo. bolna (orchestrator) runs in
Docker on the laptop; our **tool service is already on Render** (public, always-on) so
bookings still land in Google Sheets. Cost ≈ ₹0 beyond the phone number + a few
minutes of provider usage.

> Laptop = fine for a demo. It must stay **on and awake** during calls. For a real
> 24/7 line, move bolna to a small VPS later (same steps, different machine).

## Architecture (laptop mode)
```
You call Twilio US number
   -> Twilio  --(ngrok tunnel)-->  bolna twilio-app + bolna-app  (Docker, your laptop)
                                      |  STT Deepgram / LLM Gemini / TTS Sarvam(priya)
                                      |  function tools ---HTTPS--> Render tool service
                                      |                                   -> Google Sheet
```
Only bolna is on the laptop. The tools + Sheet are on Render/Google — always up.

## 0. Prereqs (one-time)
- **Docker Desktop** installed and running.
- **ngrok account** → copy your authtoken (free).
- **Twilio trial** → a US number + Account SID + Auth Token (no India KYC).
- Provider keys: **Deepgram**, **Sarvam**, **Gemini** (Google AI key).
- **Render tool service deployed** → note its URL, e.g. `https://cali-burrito-tools.onrender.com`.

## 1. Clone bolna
```bash
git clone https://github.com/bolna-ai/bolna.git
cd bolna/local_setup
```

## 2. Configure env
```bash
cp .env.sample .env
```
Fill these in `.env` (only the ones for our stack):
```
DEEPGRAM_AUTH_TOKEN=...
SARVAM_API_KEY=...
GOOGLE_API_KEY=...            # Gemini
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
CALL_TRANSFER_WEBHOOK_URL=    # optional; for human transfer wiring
```
Our tools are on Render (public https), so you do **NOT** need
`BOLNA_TOOL_URL_HOST_ALLOWLIST` — the SSRF guard only blocks localhost/private IPs.

## 3. ngrok token + region
Edit `local_setup/ngrok-config.yml`:
```yaml
region: in          # change us -> in for India (lower latency)
authtoken: <your-ngrok-authtoken>
```

## 4. Build the agent config (points bolna at your Render tools)
From THIS repo (voice-agent):
```bash
WEBHOOK_BASE=https://cali-burrito-tools.onrender.com \
STT_PROVIDER=deepgram LLM_PROVIDER=gemini TELEPHONY=twilio \
SARVAM_VOICE_ID=priya SARVAM_MODEL=bulbul:v3 \
.venv/Scripts/python scripts/build_bolna_agent.py     # writes bolna_agent.json
```

## 5. Start bolna (Docker)
```bash
cd bolna/local_setup
chmod +x start.sh && ./start.sh
# or: docker compose up -d bolna-app twilio-app     # + redis, ngrok
```
Containers: bolna-app (:5001), twilio-app (:8001), ngrok (dashboard :4040), redis.

## 6. Create the agent
```bash
curl -X POST http://localhost:5001/agent \
  -H "Content-Type: application/json" \
  -d @bolna_agent.json
# -> returns { "agent_id": "..." }  (save it)
```

## 7. Wire the Twilio number to bolna (inbound)
1. Open the ngrok dashboard at http://localhost:4040 → copy the public URL for the
   **twilio-app** tunnel (`https://xxxx.ngrok.app`).
2. In the Twilio console → your number → **Voice → A call comes in** → set the webhook
   to that twilio-app ngrok URL (bolna's twilio server maps the call to your
   `agent_id`; see bolna telephony docs for the exact inbound path/param).

## 8. Warm Render, then call
Render free tier **sleeps after ~15 min idle** → first tool call can exceed bolna's
10 s timeout. Before demoing, wake it:
```bash
curl https://cali-burrito-tools.onrender.com/health
```
Then **call your Twilio number**. Try: "What time do you open?" → book a table →
"confirm my booking" → "I want a party of 40" (transfer). The booking appears in your
Google Sheet.

## 9. Tune the voice
Rebuild step 4 with `SARVAM_VOICE_ID=neha` or `manisha`+`SARVAM_MODEL=bulbul:v2`,
re-create the agent (step 6), call again. Pick by ear on the real 8 kHz line.

## Gotchas
- **Laptop sleep = dropped calls.** Disable sleep / keep it plugged & awake.
- **ngrok free** URLs change on restart → re-set the Twilio webhook after each restart.
- **Render cold start** → keep-warm with a periodic `/health` ping during the demo, or
  upgrade Render to a paid always-on instance.
- **Latency:** home Wi-Fi jitter can hurt voice naturalness; wired ethernet helps. A
  Singapore VPS is smoother for a real line.
