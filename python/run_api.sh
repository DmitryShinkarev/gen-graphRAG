#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):$PYTHONPATH"
source venv/bin/activate
exec uvicorn api.server:app --host 0.0.0.0 --port 8000 "$@"
