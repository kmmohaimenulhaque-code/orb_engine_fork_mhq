#!/bin/bash
# Quick demo launcher for Space Apps

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== NASA Orbit Simulator Demo ==="
echo "Starting backend..."

cd "$ROOT/backend"
if [ ! -d "venv" ]; then
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "API: http://localhost:8000/docs"
echo "Frontend: open frontend/index.html or serve it"
echo ""
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID 2>/dev/null" EXIT
wait
