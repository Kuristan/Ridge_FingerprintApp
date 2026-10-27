#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
echo 'Open http://127.0.0.1:8000 in your browser. Ctrl+C stops the app.'
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
