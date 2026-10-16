#!/bin/sh
# Offline Replay demo: local API + Next.js, no Docker, DB, network provider, or LLM needed.
set -eu
mkdir -p .tmp .npm-cache
demo_root=$(pwd)
export TMPDIR="$demo_root/.tmp" TEMP="$demo_root/.tmp" TMP="$demo_root/.tmp"
export NPM_CONFIG_CACHE="$demo_root/.npm-cache"
export ENABLE_REPLAY=true RECORDINGS_DIR="$demo_root/recordings" LLM_PROVIDER=mock
export NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
if [ ! -f recordings/dev001-engineering.json ]; then
  echo "Missing engineering replay snapshot; run the build_dev_replay module." >&2
  exit 1
fi
if [ -x apps/api/.venv/Scripts/python ]; then
  demo_python=.venv/Scripts/python
else
  demo_python=.venv/bin/python
fi
(cd apps/api && "$demo_python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
(cd apps/web && npm run dev -- --hostname 127.0.0.1)
