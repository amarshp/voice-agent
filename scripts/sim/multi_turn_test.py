"""Multi-turn faithful Twilio simulator with mark-based turn sync.
Waits for each bot reply to finish (mark + settle) before the next utterance."""
import asyncio, json, base64, io, wave, audioop, os, sys, struct, random
import requests, websockets

# faint comfort-noise frame (like a real phone line) so Deepgram doesn't idle-close
_NOISE = [audioop.lin2ulaw(b"".join(struct.pack("<h", random.randint(-45, 45)) for _ in range(160)), 2) for _ in range(20)]
def cn():
    return _NOISE[random.randint(0, 19)]

AID = sys.argv[1]
TURNS = json.loads(sys.argv[2])
SKEY = os.environ["SARVAM_API_KEY"]; DKEY = os.environ["DEEPGRAM_AUTH_TOKEN"]


def tts(text):
    r = requests.post("https://api.sarvam.ai/text-to-speech",
        headers={"api-subscription-key": SKEY, "Content-Type": "application/json"},
        json={"inputs":[text],"target_language_code":"en-IN","speaker":"anushka","model":"bulbul:v2","speech_sample_rate":8000}, timeout=30)
    r.raise_for_status()
    w = wave.open(io.BytesIO(base64.b64decode(r.json()["audios"][0])))
    return audioop.lin2ulaw(w.readframes(w.getnframes()), 2)


def stt(mulaw):
    if len(mulaw) < 300: return "(no/low audio)"
    pcm = audioop.ulaw2lin(bytes(mulaw), 2)
    buf = io.BytesIO(); w = wave.open(buf,"wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(pcm); w.close()
    try:
        r = requests.post("https://api.deepgram.com/v1/listen?model=nova-3&language=en-IN",
            headers={"Authorization": f"Token {DKEY}", "Content-Type":"audio/wav"}, data=buf.getvalue(), timeout=30)
        return r.json()["results"]["channels"][0]["alternatives"][0]["transcript"] or "(silent)"
    except Exception as e:
        return f"(stt fail {e})"


async def main():
    cur = bytearray(); marks = [0]; ts = [0]
    async with websockets.connect(f"ws://localhost:5001/chat/v1/{AID}", max_size=None) as ws:
        await ws.send(json.dumps({"event":"connected","protocol":"Call","version":"1.0.0"}))
        await ws.send(json.dumps({"event":"start","streamSid":"MZc","start":{"streamSid":"MZc","callSid":"CAc","tracks":["inbound"],"mediaFormat":{"encoding":"audio/x-mulaw","sampleRate":8000,"channels":1}}}))
        stop = asyncio.Event()
        async def rx():
            try:
                while not stop.is_set():
                    d = json.loads(await ws.recv()); ev = d.get("event")
                    if ev == "media": cur.extend(base64.b64decode(d["media"]["payload"]))
                    elif ev == "mark":
                        await ws.send(json.dumps({"event":"mark","streamSid":"MZc","mark":{"name":d["mark"]["name"]}})); marks[0]+=1
            except Exception: pass
        asyncio.create_task(rx())

        async def frame(f):
            await ws.send(json.dumps({"event":"media","streamSid":"MZc","media":{"track":"inbound","chunk":str(ts[0]//20),"timestamp":str(ts[0]),"payload":base64.b64encode(f).decode()}}))
            ts[0]+=20; await asyncio.sleep(0.02)
        sil = b"\xff"*160
        for _ in range(15): await frame(cn())

        for turn in TURNS:
            cur.clear(); m0 = marks[0]
            u = tts(turn)
            for i in range(0, len(u), 160):
                f = u[i:i+160]
                if len(f) < 160: f += b"\xff"*(160-len(f))
                await frame(f)
            # wait for reply: keep stream alive with silence; break after mark + settle
            got_mark_at = None; last_len = 0; settle = 0
            for step in range(600):                       # up to ~12s
                await frame(cn())
                if marks[0] > m0:
                    if got_mark_at is None: got_mark_at = step
                    if len(cur) == last_len: settle += 1
                    else: settle = 0
                    last_len = len(cur)
                    if settle > 45: break                 # ~0.9s no new audio after mark
            print(f"YOU: {turn}")
            print(f"BOT: {stt(cur)}")
            print("-"*55)
            for _ in range(30): await frame(cn())          # inter-turn gap so we don't interrupt
        # HOLD open so any tool call from the last turn can execute + reply
        cur.clear(); m0 = marks[0]
        for _ in range(700): await frame(cn())             # ~14s hold
        print(f"POST-HOLD reply: {stt(cur)}")
        stop.set()

asyncio.run(main())
