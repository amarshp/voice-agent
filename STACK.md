# California Burrito Voice Agent — Stack Decision (2026)

Goal: customer dials a **+91** number, talks to an AI that sounds like a natural
**Indian-English** speaker, can answer FAQs (hours, menu), **book** appointments,
**review/list** bookings, **write to Google Sheets**, and **escalate/transfer** to a
human phone number. Low volume (few calls/day demo). Cheap ideally ~$0, but
**voice quality/performance is the priority**.

---

## The 3 findings that shape everything

1. **No +91 number for a bare individual.** Every legit provider (Plivo, Exotel,
   Twilio) gates +91 behind **business KYC**. Escape hatch: free **Udyam (MSME)
   registration** — Aadhaar + PAN, self-declared, ~5 min, no turnover minimum.
   Makes a solo dev eligible. Do this first; it's the gating delay.

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

### Path A — Vapi + Exotel  (RECOMMENDED for the demo: best quality per hour of effort)
`Exotel +91 DID → SIP → Vapi (bring-your-own keys) → Deepgram Nova-3 STT + Gemini 2.5 Flash LLM + Sarvam Bulbul v3 TTS`

- Vapi handles the hard part (turn-taking, endpointing, barge-in) out of the box.
- You write 4 tool webhooks: `book`, `list_bookings`, `write_sheet`, `transfer`.
- **Plivo does NOT work with Vapi** (TRAI needs Indian SIP termination; Vapi is US-hosted).
  Exotel terminates in India then bridges to Vapi → compliant. This is the one
  integration step most likely to need an Exotel support ticket — verify hands-on.
- Setup: **hours.**

### Path B — Self-host LiveKit/Pipecat + Plivo  (cheapest; more effort)
`Plivo +91 DID → your Indian VPS running LiveKit Agents (OSS) → same STT/LLM/TTS`

- You terminate SIP/media on an Indian VPS yourself → Plivo (cheapest number, ₹250/mo) is fine.
- Drops Vapi's $0.05/min platform fee → near-zero marginal cost.
- You own turn-taking tuning, deployment, monitoring. Setup: **days.**
- Only worth it past demo stage / higher volume. Break-even vs Vapi is thousands of min/mo.

---

## Component picks (both paths)

| Layer | Pick | Why | Price |
|---|---|---|---|
| **TTS** (most important) | **Sarvam Bulbul v3** | Best native Indian realism; won blind 8kHz test; nails Indian names + Hinglish | ₹30/10k chars (~$0.032/min spoken); ₹1,000 free credit |
| TTS alt (latency) | Cartesia Sonic | ~40ms TTFB, near-native Hinglish | mid |
| TTS fallback (SLA) | Azure Neural en-IN Aarti/Arjun | Native, ~105ms, 500k chars/mo free | $16/1M chars |
| **STT** | **Deepgram Nova-3 `en-IN`** | Strong on 8kHz telephony, low latency | ~$0.0058/min |
| STT alt (heavy Hinglish) | Sarvam Saarika | India-native, best code-switching | ~$0.008–0.018/min |
| **LLM** | **Gemini 2.5 Flash** | Best latency/reliability/cost; good tool calls | $0.30/$2.50 per Mtok (~$0.01/call) |
| LLM fallback | **Claude Haiku 4.5** | Best tool-arg reliability — use where a bad arg corrupts a booking | $1/$5 per Mtok |
| **Telephony** | Exotel (Path A) / Plivo (Path B) | +91, India-compliant | Plivo ₹250/mo + ₹0.60/min in |
| **Data store** | **Google Sheets API + service account** | Free at this scale (300 read+300 write/min, no daily cap) | **$0** |
| **Transfer** | Native `transferCall` tool (Vapi) / SIP REFER (self-host) | AI fee stops on transfer; only telephony continues | telephony only |

---

## Cost — Path A (Vapi), per 3-min call

| Item | Basis | Cost |
|---|---|---|
| Telephony inbound | 3 min | ~$0.02 |
| STT (Deepgram, full call) | 3 × $0.0058 | ~$0.017 |
| LLM (Gemini Flash) | ~25k in / 1k out | ~$0.010 |
| TTS (Sarvam, ~1,500 bot chars) | ₹30/10k | ~$0.045 |
| Vapi platform | 3 min × $0.05 | $0.15 |
| **Total** | | **~$0.24/call (~$0.08/min)** |

- **~5–10 calls/day ≈ $36–72/mo** + number rental. Vapi $10 + Sarvam ₹1,000 free credits cover early demo → **effectively $0 to start**.
- **Path B self-host** ≈ **$0.03/min** (~$10–25/mo), floored by the number rental. Near-$0 marginal, paid in effort.

## Skip
- OpenAI Realtime as primary (no Indian voice)
- Twilio for the number (no domestic +91 local, toll-free only, address-outside-India rule)
- Bland AI ($299+ floor, closed)
- Vapi + Plivo combo (doesn't work — see Path A note)

## Verify before committing
1. Exotel↔Vapi inbound SIP for +91 (support ticket likely).
2. Gemini/Groq free-tier RPM/RPD caps in your own account/region.
3. Amazon Nova 2 Sonic per-min price *if* you ever go the S2S route.

## Ethics/legal note
"Human shouldn't discern it's AI" — inbound is DLT-exempt so no legal disclosure
requirement in India today, but many jurisdictions/consumers expect disclosure.
Product decision, not a blocker.

---

## First concrete steps
1. **Udyam registration** (free) → unlocks +91 KYC.
2. Sign up **Vapi** ($10 free), **Sarvam** (₹1,000 free), **Deepgram**, **Gemini** keys.
3. Sign up **Exotel**, get a +91 DID, open SIP-to-Vapi ticket.
4. Create Google Sheet + service account; share sheet to its email.
5. Build 4 tool webhooks (book / list / write-sheet / transfer) — small Node/Python service.
6. Configure Vapi assistant: system prompt (California Burrito persona), Sarvam TTS, Deepgram STT, Gemini LLM, attach 4 tools.
