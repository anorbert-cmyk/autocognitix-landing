#!/bin/sh
# Start proxy in background (optional — if it crashes, nginx still works)
cd /opt/proxy && PYTHONPATH=/opt/proxy/deps python3 -m uvicorn main:app --host 0.0.0.0 --port 8081 --workers 1 --log-level warning 2>&1 | head -1 &

# Start nginx in foreground (Railway monitors this process)
exec nginx -g "daemon off;"
