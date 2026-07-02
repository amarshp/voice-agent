# Cost Analysis — Self-Hosted vs. Managed (Bolna Cloud)

A real per-minute + monthly cost breakdown for running this voice agent, comparing
**self-hosting** (our stack on a VPS) against a **managed platform** (Bolna Cloud).
All figures in ₹ at ~$1 = ₹83.

> TL;DR: managed hosting is cheaper for a tiny POC (its per-minute model has no fixed
> floor), but **self-hosting is ~2–2.5× cheaper at production volume** because you skip
> the platform fee and the marked-up voice. Break-even is ~300 min/month.

---

## 1. Per-minute cost breakdown ($/min)

| Component | Bolna Cloud | Self-host (our stack) | Notes |
|---|---|---|---|
| Telephony | $0.010 | $0.009 (Twilio) | ~same |
| **Platform fee** | **$0.020** | **$0** | we run the orchestrator ourselves |
| **Voice / TTS** | **$0.050** | **~$0.016 (Sarvam)** | managed marks up the voice ~3× |
| LLM | $0.009 | $0.005 (gpt-4o-mini) / $0.030 (gpt-4o) | |
| Transcriber (STT) | $0.009 | ~$0.007 (Deepgram) | ~same |
| **Total / min** | **$0.098** | **$0.037 (mini) / $0.062 (gpt-4o)** | |
| Fixed infra / month | $0 (bundled) | ~₹1,500 (VPS) | see §3 |

**Key insight:** on the managed platform, *Voice ($0.05) + Platform fee ($0.02) = $0.07/min
of overhead* you don't pay when self-hosting. The managed "server cost" is bundled into the
per-minute platform fee — i.e. you rent the box by the minute instead of owning it.

---

## 2. Total monthly cost by volume (VPS included for self-host)

| Minutes / month | Self-host + gpt-4o-mini | Self-host + gpt-4o | Bolna Cloud ($0.098/min) |
|---|---|---|---|
| **100** (POC) | ₹1,760 | ₹2,015 | **₹815** |
| **~300** (break-even) | ₹2,280 | ₹2,760 | ₹2,440 |
| **500** | **₹2,800** | ₹4,075 | ₹4,065 |
| **1,000** | **₹4,100** | ₹6,650 | ₹8,130 |
| **2,000** | **₹6,700** | ₹11,800 | ₹16,260 |
| **5,000** | **₹14,500** | ₹27,250 | ₹40,650 |
| **10,000** | **₹27,500** | ₹53,000 | ₹81,300 |

**Effective ₹/min** falls from ₹17.6 → **₹2.75** for self-host as the VPS amortizes, while
managed stays flat at **~₹8.1/min**.

---

## 3. Why the fixed VPS matters (rent vs. own)

The managed platform's `$0.02/min` platform fee *is* your server cost — just charged
per-minute instead of a flat monthly fee:

| Minutes / month | Managed platform fee ($0.02/min) | Your flat VPS |
|---|---|---|
| 100 | ₹166 | ₹1,500 |
| 1,000 | ₹1,660 | ₹1,500 |
| 5,000 | ₹8,300 | ₹1,500 |
| 10,000 | ₹16,600 | ₹1,500 |

The rented "server" crosses the owned VPS at **~900 min/month** — and that's *before* the
voice markup. Rent wins for a short/small POC; own wins decisively at real volume.

---

## 4. Performance trade-offs (cost isn't everything)

| Dimension | Self-host | Managed |
|---|---|---|
| Response latency | ~1.5–2s (measured) | ~1.5–2s |
| Voice quality / model choice | **full control** (tuned) | their defaults |
| Uptime / redundancy | single VPS (~99.5%) | **managed (~99.9%)** |
| Burst concurrency | ~5–15 calls / 4 GB VPS; scale by sizing up | **auto-scales** |
| Control / tuning / BYOK | **full** | limited |
| Ops burden | you own it | **hands-off** |

---

## 5. Recommendation

- **POC (~100 min/mo):** managed is ~₹1k/mo cheaper — trivial, but it drags in KYC / no-BYOK
  limits and you'd rebuild the whole tuned stack on their platform.
- **Production ("a lot" of minutes):** **self-host on a VPS + gpt-4o-mini** — ~2–2.5× cheaper,
  full control, no KYC wall, and you set it up once (no migration).

*Assumptions: VPS ₹1,500/mo (4 GB, India region); Deepgram ₹0.6/min; Sarvam ₹1.0/min;
gpt-4o ₹2.7/min; gpt-4o-mini ₹0.3/min; telephony ₹0.7/min; managed rate from published
pricing ($0.098/min all-in). Adjust to your real monthly minutes to find your exact winner.*
