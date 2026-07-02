#!/usr/bin/env bash
# Deploy the free browser voice demo (src/static/demo.html) to Vercel, baking in the
# current public bolna WebSocket (ngrok wss) URL + agent id. Re-run whenever the ngrok
# URL rotates or the agent id changes.
#
# Usage:
#   WSS=wss://<your-ngrok>.ngrok-free.dev AID=<agent_id> bash scripts/deploy_demo.sh
#
# Prereqs: vercel CLI logged in (amarshs-projects team). Bolna + ngrok must be running
# for the deployed page to actually connect.
set -e
WSS="${WSS:?set WSS to the ngrok wss URL, e.g. wss://xxxx.ngrok-free.dev}"
AID="${AID:?set AID to the bolna agent id}"
SCOPE="${SCOPE:-amarshs-projects}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

D="$(mktemp -d)"
sed -e "s|AGENT_ID_PLACEHOLDER|$AID|" \
    -e "s|ws://localhost:5001|$WSS|" \
    "$ROOT/src/static/demo.html" > "$D/index.html"

echo "Deploying demo (agent=$AID, ws=$WSS) ..."
cd "$D" && vercel deploy --prod --yes --scope "$SCOPE"
echo "Done -> https://california-burrito-demo.vercel.app"
