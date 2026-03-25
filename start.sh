#!/bin/sh
# Start proxy in background (OPTIONAL — if Python or deps missing, nginx still works)
if command -v python3 >/dev/null 2>&1 && [ -f /opt/proxy/main.py ]; then
  python3 -c "import uvicorn" 2>/dev/null && \
    (cd /opt/proxy && python3 -m uvicorn main:app --host 0.0.0.0 --port 8081 --workers 1 --log-level warning > /dev/null 2>&1 &) || \
    echo "[start.sh] Proxy deps missing, skipping proxy"
else
  echo "[start.sh] Python3 or proxy not available, skipping proxy"
fi

# Start nginx in foreground (Railway monitors this process)
exec nginx -g "daemon off;"
