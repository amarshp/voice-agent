"""Generate a bolna agent payload from our tool schemas + system prompt.

Emits `bolna_agent.json` — the exact body you POST to bolna's `/agent` endpoint.
Keeps a single source of truth: tools come from src/schemas.TOOL_SCHEMAS, the prompt
from src/prompt.build_system_prompt, business data from config/business.yaml.

bolna maps cleanly onto what we already built:
  - api_tools.tools        == our OpenAI-format TOOL_SCHEMAS (verbatim)
  - api_tools.tools_params == {tool_name: {url, method, param}}, where `param` uses
                              bolna's $var markers to inject the LLM's arguments into
                              the JSON body POSTed to our webhook.

Env (all optional; sane demo defaults):
  WEBHOOK_BASE   public base URL of our tool service (default a placeholder ngrok URL).
                 NOTE: bolna's SSRF guard blocks localhost/private IPs — expose the
                 service via ngrok, or set BOLNA_TOOL_URL_HOST_ALLOWLIST on the bolna side.
  TELEPHONY      twilio (demo) | plivo | exotel
  STT_PROVIDER   deepgram (default) | sarvam
  LLM_PROVIDER   gemini (default) | openai | azure
  SARVAM_VOICE / SARVAM_VOICE_ID / SARVAM_MODEL / SARVAM_LANG  Sarvam TTS voice knobs.

Run:  python scripts/build_bolna_agent.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from prompt import build_system_prompt  # noqa: E402
from schemas import TOOL_SCHEMAS  # noqa: E402
from tools import config  # noqa: E402

WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "https://YOUR-NGROK-SUBDOMAIN.ngrok.app").rstrip("/")
TELEPHONY = os.environ.get("TELEPHONY", "twilio")
STT_PROVIDER = os.environ.get("STT_PROVIDER", "deepgram")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")  # Groq = fast; OPENAI_BASE_URL in .env


def _strict_tools() -> list:
    """Set strict:false on each tool. Groq's strict mode demands every property be in
    `required` + additionalProperties:false everywhere; we have optional fields (notes),
    so disable strict (bolna defaults it to True)."""
    out = []
    for t in TOOL_SCHEMAS:
        t = json.loads(json.dumps(t))  # deep copy
        t["function"]["strict"] = False
        out.append(t)
    return out


def _tools_params() -> dict:
    """Map each tool -> {url, method, param($var markers)} for bolna."""
    params: dict[str, dict] = {}
    for t in TOOL_SCHEMAS:
        fn = t["function"]
        name = fn["name"]
        props = fn["parameters"].get("properties", {})
        required = fn["parameters"].get("required", list(props))
        # bolna var-markers are {"$var": "field"} dicts (type-safe JSON substitution).
        # Only template REQUIRED fields — an optional field the LLM omits would otherwise
        # be sent as the literal {"$var": ...} marker and fail server-side validation.
        param = {k: {"$var": k} for k in props if k in required}
        params[name] = {
            "url": f"{WEBHOOK_BASE}/tools/{name}",
            "method": "POST",
            "param": param,
        }
    return params


def _transcriber() -> dict:
    if STT_PROVIDER == "sarvam":
        return {"provider": "sarvam", "model": "saarika:v2.5", "language": "en-IN",
                "stream": True, "encoding": "linear16"}
    # endpointing = ms of silence before Deepgram finalizes -> lower = snappier replies
    # (but too low cuts callers off mid-sentence, e.g. spelling a phone number).
    # endpointing = ms of silence before finalizing. Too low -> chops mid-sentence when the
    # caller pauses (drops words, splits "my name is X and my number is Y" into fragments);
    # too high -> slow to reply. interim_timeout raises the force-finalize fallback so a
    # natural pause mid-utterance doesn't split. Groq's fast LLM absorbs the extra wait.
    return {"provider": "deepgram", "model": "nova-3", "language": "en-IN",
            "stream": True, "encoding": "linear16",
            "endpointing": int(os.environ.get("ENDPOINTING", "700")),
            "interim_timeout": float(os.environ.get("INTERIM_TIMEOUT", "2.5"))}


def _llm_agent() -> dict:
    # bolna's native GeminiLLM (provider "google") is buggy in this build (aiohttp attr,
    # dict.strip). Route Gemini through bolna's OpenAI path instead: provider "openai"
    # + model "gemini-2.5-flash", with OPENAI_BASE_URL pointed at Gemini's
    # OpenAI-compatible endpoint (set in bolna's .env). Uses the battle-tested OpenAiLLM.
    # provider "openai" == the OpenAiLLM path (accumulator/tools proven). OPENAI_BASE_URL in
    # bolna's .env decides the actual backend (Groq for low latency). model is a Groq model.
    if LLM_PROVIDER == "native_google":
        provider, model = "google", "gemini-2.5-flash"
    elif LLM_PROVIDER == "gemini":
        provider, model = "openai", "gemini-2.5-flash"   # if OPENAI_BASE_URL points at Gemini
    else:                                                # default: Groq via OpenAI-compat
        # gpt-oss-120b (OpenAI open model on Groq): 5/5 reliable structured tool-calls +
        # fast. llama-3.3-70b flaked live (emitted <function=...> text -> spoke code).
        provider, model = "openai", os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")
    return {
        "agent_type": "simple_llm_agent",
        "agent_flow_type": "streaming",
        "llm_config": {"provider": provider, "model": model, "temperature": 0.3,
                       "max_tokens": 300},
    }


def _synthesizer() -> dict:
    # Sarvam Bulbul. bolna's SarvamSynthesizer uses voice_id/model/language and
    # resamples to 8kHz for telephony. SarvamConfig requires `voice` too (unused by
    # the synth) so we set both to the speaker name.
    #   Warm female receptionist voices:
    #     bulbul:v3 -> priya, neha, ritu    (v3 = latest/best realism)
    #     bulbul:v2 -> manisha              (Sarvam labels it "warm & friendly")
    #   Supported languages: en-IN, hi-IN, and 9 more Indic codes.
    speaker = os.environ.get("SARVAM_VOICE_ID", os.environ.get("SARVAM_VOICE", "priya"))
    # stream=False -> bolna uses Sarvam's per-request REST TTS, not a persistent
    # websocket. Avoids the 408 "socket idle too long" crash that ends the call when
    # the socket sits open with no text (no preloaded greeting) before the caller speaks.
    return {
        "provider": "sarvam",
        "stream": os.environ.get("SARVAM_STREAM", "true").lower() == "true",  # streaming = lower latency
        "audio_format": "wav",
        "provider_config": {
            "voice": speaker,
            "voice_id": speaker,
            "model": os.environ.get("SARVAM_MODEL", "bulbul:v3"),
            "language": os.environ.get("SARVAM_LANG", "en-IN"),
            "speed": float(os.environ.get("SARVAM_SPEED", "1.0")),
        },
    }


def build_payload() -> dict:
    cfg = config()
    io = {"format": "wav", "provider": TELEPHONY}
    return {
        "agent_config": {
            "agent_name": cfg["name"],
            "agent_type": "other",
            "agent_welcome_message": os.environ.get(
                "WELCOME_MSG", f"Hello! Welcome to {cfg['name']}. How can I help you today?"),
            "tasks": [
                {
                    "task_type": "conversation",
                    "task_config": {
                        "hangup_after_silence": 30,   # don't hang up on brief silence mid-tool-call
                        "check_if_user_online": False,
                        # require 3 words before treating it as a real interruption (default 1
                        # made the bot cut itself off on echo/one stray word)
                        "number_of_words_for_interruption": 3,
                    },
                    "toolchain": {
                        "execution": "parallel",
                        "pipelines": [["transcriber", "llm", "synthesizer"]],
                    },
                    "tools_config": {
                        "input": io,
                        "output": io,
                        "transcriber": _transcriber(),
                        "llm_agent": _llm_agent(),
                        "synthesizer": _synthesizer(),
                        "api_tools": {
                            "tools": _strict_tools(),
                            "tools_params": _tools_params(),
                        },
                    },
                }
            ],
        },
        "agent_prompts": {"task_1": {"system_prompt": build_system_prompt()}},
    }


def main() -> None:
    payload = build_payload()
    out = ROOT / "bolna_agent.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  telephony={TELEPHONY}  stt={STT_PROVIDER}  llm={LLM_PROVIDER}  tts=sarvam")
    print(f"  webhook base={WEBHOOK_BASE}")
    print(f"  tools: {', '.join(p['function']['name'] for p in TOOL_SCHEMAS)}")
    if "YOUR-NGROK" in WEBHOOK_BASE:
        print("  ! set WEBHOOK_BASE to a public URL (ngrok) — bolna blocks localhost.")


if __name__ == "__main__":
    main()
