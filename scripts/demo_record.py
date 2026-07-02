"""Record a full simulated call (caller + agent) to a WAV so you can HEAR the conversation.

Caller turns are synthesized in a distinct voice; the agent's real audio (ritu) is captured
from the live bolna ws. Both are laid into one 8 kHz timeline in order.

Run (inside the bolna container):
  python demo_record.py <agent_id> '["turn 1","turn 2",...]' /app/demoN.wav [caller_voice]
"""
import asyncio, json, base64, io, wave, audioop, os, sys, struct, random
import requests, websockets

_NOISE = [audioop.lin2ulaw(b"".join(struct.pack("<h", random.randint(-45, 45)) for _ in range(160)), 2) for _ in range(20)]
def cn(): return _NOISE[random.randint(0, 19)]

AID = sys.argv[1]
TURNS = json.loads(sys.argv[2])
OUT = sys.argv[3]
CALLER_VOICE = sys.argv[4] if len(sys.argv) > 4 else "kabir"   # male -> distinct from ritu
SKEY = os.environ["SARVAM_API_KEY"]
GAP = b"\xff" * 160 * 18   # ~0.36s silence between speakers (0xff = mulaw silence)


def tts(text, voice):
    r = requests.post("https://api.sarvam.ai/text-to-speech",
        headers={"api-subscription-key": SKEY, "Content-Type": "application/json"},
        json={"inputs": [text], "target_language_code": "en-IN", "speaker": voice,
              "model": "bulbul:v3", "speech_sample_rate": 8000}, timeout=30)
    r.raise_for_status()
    w = wave.open(io.BytesIO(base64.b64decode(r.json()["audios"][0])))
    return audioop.lin2ulaw(w.readframes(w.getnframes()), 2)


async def main():
    cur = bytearray(); marks = [0]; ts = [0]; timeline = bytearray()
    async with websockets.connect(f"ws://localhost:5001/chat/v1/{AID}", max_size=None) as ws:
        await ws.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
        await ws.send(json.dumps({"event": "start", "streamSid": "MZc", "start": {"streamSid": "MZc", "callSid": "CAc", "tracks": ["inbound"], "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}}))
        stop = asyncio.Event()

        async def rx():
            try:
                while not stop.is_set():
                    d = json.loads(await ws.recv()); ev = d.get("event")
                    if ev == "media": cur.extend(base64.b64decode(d["media"]["payload"]))
                    elif ev == "mark":
                        await ws.send(json.dumps({"event": "mark", "streamSid": "MZc", "mark": {"name": d["mark"]["name"]}})); marks[0] += 1
            except Exception: pass
        asyncio.create_task(rx())

        async def frame(f):
            await ws.send(json.dumps({"event": "media", "streamSid": "MZc", "media": {"track": "inbound", "chunk": str(ts[0] // 20), "timestamp": str(ts[0]), "payload": base64.b64encode(f).decode()}}))
            ts[0] += 20; await asyncio.sleep(0.02)

        async def wait_reply(m0, steps=700):
            last = 0; settle = 0
            for _ in range(steps):
                await frame(cn())
                if marks[0] > m0:
                    settle = settle + 1 if len(cur) == last else 0
                    last = len(cur)
                    if settle > 45: break

        # warm up, capture the welcome greeting
        for _ in range(15): await frame(cn())
        cur.clear(); m0 = marks[0]; await wait_reply(m0, 500)
        timeline.extend(bytes(cur)); timeline.extend(GAP)

        for turn in TURNS:
            u = tts(turn, CALLER_VOICE)
            timeline.extend(u); timeline.extend(GAP)      # caller audio
            cur.clear(); m0 = marks[0]
            for i in range(0, len(u), 160):
                f = u[i:i+160]
                if len(f) < 160: f += b"\xff" * (160 - len(f))
                await frame(f)
            await wait_reply(m0)
            timeline.extend(bytes(cur)); timeline.extend(GAP)  # agent reply
        # final hold so a last tool-call / hangup line is captured
        cur.clear(); m0 = marks[0]
        for _ in range(350): await frame(cn())
        if len(cur) > 500:
            timeline.extend(bytes(cur))
        stop.set()

    pcm = audioop.ulaw2lin(bytes(timeline), 2)
    w = wave.open(OUT, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(pcm); w.close()
    print(f"saved {OUT}  ({len(timeline)/8000.0:.1f}s)")

asyncio.run(main())
