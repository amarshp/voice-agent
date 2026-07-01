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

## Two viable paths

### Path A — Bolna  (RECOMMENDED: India-native, sidesteps the compliance trap)
`Bolna buys +91 DID (Plivo/Vobiz) → Bolna orchestration (BYOK) → Deepgram Nova-3 STT + Gemini 2.5 Flash LLM + Sarvam Bulbul v3 TTS`

- India-native platform. **Buys the +91 number for you** ($5/mo via Plivo/Vobiz) and
  handles the Indian telephony/SIP compliance under the hood → **avoids the Vapi
  India-SIP-termination block entirely.**
- **BYOK** (bring your own keys) for STT/LLM/TTS → Sarvam + Deepgram plug in at cost.
- $0.06/min platform, $5 free credit, no monthly floor. Has function/tool calling + transfer.
- 10+ Indic languages incl. Hinglish native. Setup: **hours.**
- **Open item:** exact KYC for the +91 number = "identity documents" (not specified;
  likely inherits Plivo/Vobiz business reg). Confirm before building. See KYC note below.

### Path B — Vapi + Exotel  (alternative; compliance NOT proven — do not assume)
`Exotel +91 DID → SIP → Vapi (BYOK) → same STT/LLM/TTS`

- **Vapi explicitly blocks Indian numbers** (its own docs: TRAI needs Indian SIP
  termination, Vapi is US-hosted). Exotel *can* route +91 to SIP, but **no primary
  source confirms Exotel→Vapi is compliant/works.** Get it in writing from Exotel/Vapi
  before relying on it. Only pick this if Bolna doesn't fit.
- Vapi custom TTS = a **webhook returning raw PCM** (not paste-an-API-key); Sarvam
  needs a small custom TTS server. Extra concurrency = $10/line/mo.

### Path C — Self-host LiveKit/Pipecat + Plivo  (cheapest marginal; most effort)
`Plivo +91 DID → your Mumbai VPS running LiveKit Agents (OSS) → same STT/LLM/TTS`

- You terminate SIP/media on an Indian VPS yourself → Plivo works, near-zero marginal cost.
- You own turn-taking tuning, deployment, monitoring. Setup: **days.**
- Only worth it past demo stage / higher volume.

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
