#!/bin/sh
# start.sh — launches Python proxy sidecar + nginx with graceful signal handling.
# DEVOPS-H3: set -eu, capture PIDs, propagate SIGTERM/SIGINT.
# DEVOPS-L3: uvicorn logs are NOT silenced; they stream to container stdout/stderr.
#
# /bin/sh on Alpine is BusyBox ash. It supports -e and -u but NOT `wait -n`
# or `-o pipefail` reliably — this script avoids both.
set -eu

PROXY_PID=""
NGINX_PID=""

# Graceful shutdown: forward SIGTERM/SIGINT to children, then wait.
cleanup() {
    trap - TERM INT
    echo "[start.sh] received shutdown signal, stopping children..."
    [ -n "${PROXY_PID:-}" ] && kill -TERM "$PROXY_PID" 2>/dev/null || true
    [ -n "${NGINX_PID:-}" ] && kill -QUIT "$NGINX_PID" 2>/dev/null || true
    # `wait` without args waits for ALL background jobs of this shell.
    wait 2>/dev/null || true
    exit 0
}
trap cleanup TERM INT

# Launch Python proxy sidecar in background.
# Bind to 127.0.0.1 only — nginx is the only consumer, no external exposure.
# Uvicorn logs go to container stdout/stderr (observability).
cd /opt/proxy
python3 -m uvicorn main:app \
    --host 127.0.0.1 \
    --port 8081 \
    --workers 1 \
    --log-level info &
PROXY_PID=$!
echo "[start.sh] proxy started (pid=$PROXY_PID)"

# Launch nginx backgrounded so we can `wait` on both children.
nginx -g 'daemon off;' &
NGINX_PID=$!
echo "[start.sh] nginx started (pid=$NGINX_PID)"

# Wait for both children. If either exits, `wait` (with explicit PIDs) returns
# with that child's status — non-zero triggers Railway container restart.
wait "$PROXY_PID" "$NGINX_PID"
