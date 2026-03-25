#!/bin/sh
# Start proxy in background (optional — if it crashes, nginx still works)
cd /opt/proxy && PYTHONPATH=/opt/proxy/deps python3 -m uvicorn main:app --host 0.0.0.0 --port 8081 --workers 1 --log-level warning > /dev/null 2>&1 &

# Start nginx in foreground (Railway monitors this process)
exec nginx -g "daemon off;"
