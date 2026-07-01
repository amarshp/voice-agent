#!/usr/bin/env bash
# Re-apply the bolna @master patches into the running bolna-app container.
# Needed after `docker compose up --force-recreate` (writable layer is reset).
# These patches fix bugs that block Gemini(OpenAI-compat)+Sarvam+tools on bolna 0.10.123.
#   - quickstart_server.py       : adds the /voice inbound-TwiML route (Twilio Media Streams)
#   - sarvam_synthesizer.py      : base64-decode the HTTP TTS response (bytes, not str)
#   - task_manager.py            : http-transcription path forwards only final transcripts
#                                  (fixes ".strip() on dict"); + full traceback on run() errors
#   - tool_call_accumulator.py   : normalize tool_call index None->0 (Gemini compat) — the
#                                  KeyError:0 that aborted every tool call
#   - openai_llm.py              : (clean copy)
set -e
C=local_setup-bolna-app-1
D=$(cd "$(dirname "$0")" && pwd)
docker cp "$D/quickstart_server.py"     $C:/app/quickstart_server.py
docker cp "$D/sarvam_synthesizer.py"    $C:/usr/local/lib/python3.10/site-packages/bolna/synthesizer/sarvam_synthesizer.py
docker cp "$D/task_manager.py"          $C:/usr/local/lib/python3.10/site-packages/bolna/agent_manager/task_manager.py
docker cp "$D/tool_call_accumulator.py" $C:/usr/local/lib/python3.10/site-packages/bolna/llms/tool_call_accumulator.py
docker cp "$D/openai_llm.py"            $C:/usr/local/lib/python3.10/site-packages/bolna/llms/openai_llm.py
echo "patches applied; restarting bolna-app..."
(cd "$D/../bolna/local_setup" && docker compose restart bolna-app)
echo "done."
