#!/bin/bash
set -e
PORT="${PORT:-8080}"
echo "Starting SSC Review Agent API on port $PORT..."
exec python -m uvicorn agent.api:app --host 0.0.0.0 --port "$PORT" --workers 1