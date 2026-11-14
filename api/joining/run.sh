#!/usr/bin/env bash
# The joining check: start the real API on a throwaway database and folder, run Thomas's typed
# client through the whole demo against it, and clean up. Exits 0 only when the whole flow passed.
# Needs MongoDB running (docker start mirai-mongo) and the virtualenv at .venv.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PORT=8765
DB=mirai_joining
WORK="$(mktemp -d)"
SERVER_PID=""

cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
  .venv/bin/python -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017').drop_database('$DB')" || true
  rm -rf "$WORK"
}
trap cleanup EXIT

[ -d web/node_modules ] || npm --prefix web ci

PDF="$WORK/book.pdf"
.venv/bin/python -c "
import sys
from api.tests.helpers import make_pdf
open(sys.argv[1], 'wb').write(make_pdf(3))" "$PDF" 2>/dev/null

mkdir -p "$WORK/data"
MONGODB_URI="mongodb://localhost:27017/$DB" DATA_DIR="$WORK/data" PIPELINE=stub RENDER=stub \
  .venv/bin/python -m uvicorn api.main:app --port "$PORT" >"$WORK/server.log" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 50); do
  curl -sf "http://127.0.0.1:$PORT/api/books" >/dev/null && break
  kill -0 "$SERVER_PID" 2>/dev/null || { cat "$WORK/server.log"; echo "server did not start" >&2; exit 1; }
  sleep 0.2
done
curl -sf "http://127.0.0.1:$PORT/api/books" >/dev/null || { cat "$WORK/server.log"; echo "server did not answer" >&2; exit 1; }

status=0
JOINING_API="http://127.0.0.1:$PORT" JOINING_PDF="$PDF" \
  npx --prefix web vitest run --root web --config ../api/joining/vitest.config.ts || status=$?
[ "$status" -eq 0 ] || { echo "--- server log ---"; tail -40 "$WORK/server.log"; }
exit "$status"
