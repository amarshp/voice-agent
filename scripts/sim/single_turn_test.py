"""Faithful Twilio Media Stream simulator — full end-to-end self-test.
Echoes marks (like real Twilio), captures the bot's audio reply, decodes it,
and transcribes it via Deepgram to verify the bot actually spoke sensible words.
"""
import asyncio, json, base64, io, wave, audioop, os, sys
import requests, websockets

AID = sys.argv[1]
UTTER = sys.argv[2] if len(sys.argv) > 2 else "hello what time do you open today"
SKEY = os.environ["SARVAM_API_KEY"]
DKEY = os.environ["DEEPGRAM_AUTH_TOKEN"]


def tts_caller(text):
    r = requests.post("https://api.sarvam.ai/text-to-speech",
        headers={"api-subscription-key": SKEY, "Content-Type": "application/json"},
        json={"inputs":[text], "target_language_code":"en-IN", "speaker":"anushka",
              "model":"bulbul:v2", "speech_sample_rate":8000}, timeout=30)
    r.raise_for_status()
    wav = wave.open(io.BytesIO(base64.b64decode(r.json()["audios"][0])))
    return audioop.lin2ulaw(wav.readframes(wav.getnframes()), 2)   # mulaw 8k


async def run():
    ulaw = tts_caller(UTTER)
    resp = bytearray(); marks = 0; clears = 0
    async with websockets.connect(f"ws://localhost:5001/chat/v1/{AID}", max_size=None) as ws:
        await ws.send(json.dumps({"event":"connected","protocol":"Call","version":"1.0.0"}))
        await ws.send(json.dumps({"event":"start","streamSid":"MZtest","start":{"streamSid":"MZtest","callSid":"CAtest","tracks":["inbound"],"mediaFormat":{"encoding":"audio/x-mulaw","sampleRate":8000,"channels":1}}}))
        stop = asyncio.Event()

        async def receiver():
            nonlocal marks, clears
            try:
                while not stop.is_set():
                    d = json.loads(await ws.recv())
                    ev = d.get("event")
                    if ev == "media":
                        resp.extend(base64.b64decode(d["media"]["payload"]))
                    elif ev == "mark":          # echo back like Twilio does on playback-complete
                        await ws.send(json.dumps({"event":"mark","streamSid":"MZtest","mark":{"name":d["mark"]["name"]}}))
                        marks += 1
                    elif ev == "clear":
                        clears += 1
            except Exception:
                pass
        rxt = asyncio.create_task(receiver())

        ts = 0
        async def frame(f):
            nonlocal ts
            await ws.send(json.dumps({"event":"media","streamSid":"MZtest","media":{"track":"inbound","chunk":str(ts//20),"timestamp":str(ts),"payload":base64.b64encode(f).decode()}}))
            ts += 20; await asyncio.sleep(0.02)
        import struct as _st, random as _rnd
        _noise = [audioop.lin2ulaw(b"".join(_st.pack("<h", _rnd.randint(-45,45)) for _ in range(160)), 2) for _ in range(20)]
        def silf(): return _noise[_rnd.randint(0,19)]                # comfort noise like a real line
        for _ in range(25): await frame(silf())                     # 0.5s lead
        for i in range(0, len(ulaw), 160):
            f = ulaw[i:i+160]
            if len(f) < 160: f += b"\xff"*(160-len(f))
            await frame(f)
        for _ in range(60): await frame(silf())                     # trailing -> endpoint
        # wait for the reply like a real call would: hold open until audio+mark settle, max ~22s
        last = 0; settle = 0
        for _ in range(1100):
            await frame(silf())
            if len(resp) > 200 and marks > 0:
                if len(resp) == last: settle += 1
                else: settle = 0
                last = len(resp)
                if settle > 50: break
        stop.set(); rxt.cancel()

    dur = len(audioop.ulaw2lin(bytes(resp), 2))/2/8000 if resp else 0
    print(f"RESPONSE: {len(resp)} mulaw bytes = {dur:.1f}s audio | marks_echoed={marks} clears={clears}")
    if len(resp) > 200:
        pcm = audioop.ulaw2lin(bytes(resp), 2)
        buf = io.BytesIO(); w = wave.open(buf, "wb")
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(pcm); w.close()
        try:
            dr = requests.post("https://api.deepgram.com/v1/listen?model=nova-3&language=en-IN",
                headers={"Authorization": f"Token {DKEY}", "Content-Type": "audio/wav"},
                data=buf.getvalue(), timeout=30)
            txt = dr.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
            print(f"BOT SAID (transcribed from its audio): '{txt}'")
        except Exception as e:
            print("transcribe failed:", e)
    print("VERDICT:", "PASS - bot replied with audio" if len(resp) > 800 else "FAIL - no/low audio")

asyncio.run(run())
