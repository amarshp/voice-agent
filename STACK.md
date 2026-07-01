# California Burrito Voice Agent — Stack Decision (2026)

Goal: customer dials a **+91** number, talks to an AI that sounds like a natural
**Indian-English** speaker, can answer FAQs (hours, menu), **book** appointments,
**review/list** bookings, **write to Google Sheets**, and **escalate/transfer** to a
human phone number. Low volume (few calls/day demo). Cheap ideally ~$0, but
**voice quality/performance is the priority**.

---

## The 3 findings that shape everything

1. **No +91 number for a bare individual.** Every legit provider gates +91 behind
   **business KYC**. Escape hatch: free **Udyam (MSME) registration** (Aadhaar+PAN,
   self-declared, ~5 min, no turnover minimum). BUT KYC strictness differs:
   - **Exotel** accepts sole-proprietor + **Udyam/MSME cert** + PAN → Udyam works. ✅
   - **Plivo** public India page asks for **COI + GST** (stricter than Udyam). ⚠️
   - **Bolna** number = "identity documents," unspecified — verify which reg it needs.
   Do this first; it's the gating delay. No CPaaS sells +91 to an unregistered individual.

2. **Inbound-only bot is DLT-exempt.** DLT/TRAI outbound rules don't apply to a bot
   that only *answers* calls. (Add outbound reminders later → DLT applies.)

3. **Cascaded (STT+LLM+TTS) beats all-in-one for Indian realism.** Global
   speech-to-speech models (OpenAI Realtime) sound generic-American and can't be
   pinned to a native Indian accent. Cascaded lets you hand-pick a native Indian
   TTS voice (Sarvam) — the single biggest lever for "indistinguishable from human."
   (Only S2S with a real Indian voice = Amazon Nova 2 Sonic `kiara`/`arjun`.)

> Reality caveat: phone audio is **8kHz narrowband**. All vendor demos are 24kHz
> studio. Native-Indian voices (Sarvam, Azure Aarti/Arjun) survive 8kHz far better
> than "accent-overlay" global voices (ElevenLabs/Cartesia).

---

## Build strategy: fork, don't hand-roll (2026 GitHub research)

Indian devs converge on a **cascaded STT→LLM→TTS** pipeline orchestrated by
**Bolna / Pipecat / LiveKit**, fed **mulaw/alaw audio over a WebSocket** from
**Exotel or Plivo**, with **Sarvam** for Indic/Hinglish (+ Deepgram English fallback),
LLM via **LiteLLM → Gemini/Azure**, and business actions as **LLM function-calling
tools**. Ship self-hosted in Docker. Our Phase-1 tool service = exactly the tools
you bolt on (book / list / write-sheet / transfer).

| Repo | Stars / License | Fit | Use for |
|---|---|---|---|
| **bolna-ai/bolna** | 684 · **MIT** · live | ★ highest | Fork as orchestrator — already has Sarvam+Deepgram+**Exotel+Plivo**+LiteLLM. Self-hosted = you bring your own Exotel → **Udyam KYC, no company, full BYOK** |
| pipecat-ai/pipecat | 13k · BSD-2 · live | ★ code-first alt | Max control; Sarvam STT/TTS + Exotel/Plivo transports documented. (Check open issue #3783 "Sarvam broken" first) |
| livekit/agents | 11k · Apache-2 · live | strong transfer | Best built-in SIP **human-transfer**; `livekit-plugins-sarvam`. Heavier infra |
| sarvamai/sarvam-ai-cookbook | 164 · Apache-2 · official | reference | Correct Sarvam API + telephony codecs (`saaras:v3`, mulaw/alaw) |
| dograh-hq/dograh | 4.7k · BSD-2 · live | visual builder | Self-host Vapi-alt w/ drag-drop flow + admin UI (on Pipecat) |
| exotel/Agent-Stream | 14 · MIT · official | glue | Copy Exotel WebSocket media-stream framing (mulaw, interruption) |

**Avoid:** voxos-ai/bolna (stale 2024 fork — use upstream), vocode (unmaintained),
plivo/AI-Voice-Agents (no license = reference only), AGPL repos.

**Refined recommendation:** fork **self-hosted bolna-ai/bolna** + **Exotel** (+91 via
Udyam KYC) + Sarvam + Deepgram + Gemini, and register our Phase-1 tools as its
function tools. This collapses old Path A/C into one: managed-quality orchestration
(don't reinvent) + solo-dev-friendly KYC + full BYOK + Sarvam realism. Hosted Bolna
(below) only if you'd rather not run Docker and have a company's CIN+GST.

## Two viable paths

### Path A — Bolna  (best product IF you have a registered company)
`Bolna +91 DID (Plivo) → Bolna Indian-server routing → Sarvam STT + Azure OpenAI LLM + Sarvam Bulbul v3 TTS`

- India-native, handles telephony/SIP compliance. Setup: **hours.**
- **HARD GATE — number KYC needs CIN + GST (a registered company: Pvt Ltd/LLP).**
  Udyam sole-prop is NOT accepted by Bolna/Plivo for the number. (Bolna changelog
  29 Sep 2025: compliance app mandatory before buying dedicated numbers.)
- **Indian routing forbids BYOK.** Any custom API key → calls route via **US servers**
  (kills +91 latency/compliance). So you MUST use Bolna's built-in providers:
  - STT: Sarvam / Deepgram / Azure (built-in) ✅ Sarvam supported
  - TTS: Sarvam / Cartesia / Azure / ElevenLabs (built-in) ✅ Sarvam Bulbul supported
  - **LLM: Azure OpenAI ONLY.** No Gemini/Claude on Indian routing.
- Indian routing also requires **Plivo** specifically (not Vobiz) for the number.
- Net: realism (Sarvam) survives; you lose Gemini/BYOK; you need a company for the number.
- **Maybe-dodge:** BYO an Exotel number (Udyam KYC) into Bolna → unclear if it skips
  Bolna's CIN check. Docs silent → Bolna support ticket to confirm.

### Path B — Vapi + Exotel  (alternative; compliance NOT proven — do not assume)
`Exotel +91 DID → SIP → Vapi (BYOK) → same STT/LLM/TTS`

- **Vapi explicitly blocks Indian numbers** (its own docs: TRAI needs Indian SIP
  termination, Vapi is US-hosted). Exotel *can* route +91 to SIP, but **no primary
  source confirms Exotel→Vapi is compliant/works.** Get it in writing from Exotel/Vapi
  before relying on it. Only pick this if Bolna doesn't fit.
- Vapi custom TTS = a **webhook returning raw PCM** (not paste-an-API-key); Sarvam
  needs a small custom TTS server. Extra concurrency = $10/line/mo.

### Path C — Exotel + self-host  (RECOMMENDED for a solo dev with no company)
`Exotel +91 DID (Udyam KYC ✅) → Exotel AgentStream (bidirectional WebSocket) → your Mumbai VPS (LiveKit/Pipecat) → Deepgram/Sarvam STT + Gemini LLM + Sarvam Bulbul v3 TTS`

- **Only path that works on Udyam sole-prop KYC** — Exotel accepts it; no company needed.
- You terminate audio on a Mumbai VPS → India-compliant, low latency, **full BYOK**
  (Sarvam + Gemini free tier, your keys, at cost). Realism thesis fully intact.
- Cost: Exotel prepaid floor (~₹1,700/mo effective) + your API costs. Near-zero marginal.
- You own turn-taking tuning, deployment, monitoring. Setup: **days, not hours.**
- This is the honest solo-dev path when forming a company isn't worth it.

---

## Component picks (both paths)

| Layer | Pick | Why | Price |
|---|---|---|---|
| **TTS** (most important) | **Sarvam Bulbul v3** | Best native Indian realism; won blind 8kHz test; nails Indian names + Hinglish | ₹30/10k chars (~$0.032/min spoken); ₹1,000 free credit |
| TTS alt (latency) | Cartesia Sonic | ~40ms TTFB, near-native Hinglish | mid |
| TTS fallback (SLA) | Azure Neural en-IN Aarti/Arjun | Native, ~105ms, 500k chars/mo free | $16/1M chars |
| **STT** | **Deepgram Nova-3 `en-IN`** | Strong on 8kHz telephony, low latency | ~$0.0077–0.0092/min streaming (not the $0.0058 batch rate) |
| STT alt (heavy Hinglish) | Sarvam Saarika | India-native, best code-switching | ~$0.008–0.018/min |
| **LLM** | **Gemini 2.5 Flash** | Best latency/reliability/cost; good tool calls | $0.30/$2.50 per Mtok (~$0.01/call) |
| LLM fallback | **Claude Haiku 4.5** | Best tool-arg reliability — use where a bad arg corrupts a booking | $1/$5 per Mtok |
| **Telephony** | Exotel (Path A) / Plivo (Path B) | +91, India-compliant | Plivo ₹250/mo + ₹0.60/min in |
| **Data store** | **Google Sheets API + service account** | Free at this scale (300 read+300 write/min, no daily cap). Use **idempotent booking IDs + append-only log** to survive races/duplicate/partial writes | **$0** |
| **Transfer** | Native `transferCall` tool (Vapi) / SIP REFER (self-host) | AI fee stops on transfer; only telephony continues | telephony only |

---

## Cost — Path A (Bolna), per 3-min call

| Item | Basis | Cost |
|---|---|---|
| Bolna platform (incl. telephony) | 3 min × $0.06 | $0.18 |
| STT (Deepgram, BYOK) | 3 × ~$0.008 | ~$0.024 |
| LLM (Gemini Flash, BYOK) | ~25k in / 1k out | ~$0.010 |
| TTS (Sarvam, ~1,500 bot chars) | ₹30/10k | ~$0.045 |
| **Total** | | **~$0.26/call (~$0.09/min)** |

- **~5–10 calls/day ≈ $40–80/mo** + $5/mo number. Bolna $5 + Sarvam ₹1,000 free credits cover early demo → **effectively $0 to start**.
- **Path C self-host** ≈ **$0.03/min** (~$10–25/mo), floored by number rental. Near-$0 marginal, paid in effort.
- Latency, not price, is the real UX risk: PSTN→STT→LLM→TTS→PSTN round trip. Deploy any
  self-hosted orchestration **near Mumbai**; test on real 8kHz calls, not studio demos.

## Skip
- OpenAI Realtime as primary (no Indian voice)
- Twilio for the number (no domestic +91 local, toll-free only, address-outside-India rule)
- Bland AI ($299+ floor, closed)
- Vapi + Plivo combo (doesn't work — see Path A note)

## Verify before committing (in priority order)
1. **Bolna +91 number KYC** — which docs (Udyam enough, or COI+GST?) + activation time.
2. Sarvam Bulbul v3 realism on **real 8kHz calls** with your worst cases: noisy caller,
   Hinglish code-mixing, menu-item names, address spelling, interruptions, uncle/aunty speech.
3. If Path B: get **Exotel↔Vapi +91 compliance in writing** — do NOT assume it works.
4. Live Deepgram Nova-3 streaming rate + Gemini free-tier RPM/RPD caps in your own console.
5. DLT scope: stays exempt only while **inbound-only**. Any outbound callback/reminder/
   SMS/WhatsApp confirmation → TCCCPR/DLT + 140/1600-series rules kick in.

## Ethics/legal note
"Human shouldn't discern it's AI" — inbound is DLT-exempt so no legal disclosure
requirement in India today, but many jurisdictions/consumers expect disclosure.
Product decision, not a blocker.

---

## First concrete steps
1. **Udyam registration** (free) → unlocks +91 KYC.
2. Sign up **Bolna** ($5 free), **Sarvam** (₹1,000 free), **Deepgram**, **Gemini** keys.
3. In Bolna: buy a +91 number ($5/mo), submit KYC, confirm which docs it needs.
4. Create Google Sheet + service account; share sheet to its email.
5. Build tool webhooks (book / list / write-sheet / transfer) — small Node/Python service,
   idempotent booking IDs + append-only log.
6. Configure Bolna agent: system prompt (California Burrito persona), BYOK Sarvam TTS +
   Deepgram STT + Gemini LLM, attach the 4 tools.
7. Test on real 8kHz calls before showing anyone. The build (steps 4–6) is runnable
   before KYC clears — only the live phone test waits on the number.
