#!/usr/bin/env bash
# Redeploy the live site whenever origin/main moves.
# Run every minute by the mirai-autodeploy systemd timer (see infra/DEPLOY.md).
# If the build fails, `docker compose up --build` exits before replacing
# containers, so the previous version keeps serving.
set -euo pipefail

REPO=/opt/mirai
LOG=/var/log/mirai-autodeploy.log
cd "$REPO"

# Only one deploy at a time; skip this tick if one is still running.
exec 9>/run/mirai-autodeploy.lock
flock -n 9 || exit 0

git fetch -q origin main
local_sha=$(git rev-parse HEAD)
remote_sha=$(git rev-parse origin/main)
[ "$local_sha" = "$remote_sha" ] && exit 0

{
  echo "=== $(date -u +%FT%TZ) deploy ${local_sha:0:7} -> ${remote_sha:0:7}"
  git log --oneline "$local_sha..$remote_sha"
  if git pull -q --ff-only origin main && docker compose up -d --build 2>&1 | tail -20; then
    echo "=== $(date -u +%FT%TZ) OK now $(git rev-parse --short HEAD)"
  else
    echo "=== $(date -u +%FT%TZ) FAILED; previous containers left running"
  fi
} >>"$LOG" 2>&1
