#!/bin/bash
# run.sh - Linux/Mac running script for DJPOS (uv)

set -euo pipefail

echo "Starting DJPOS Server..."

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed."
    echo "Install it from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Virtual environment '.venv' not found. Running uv sync..."
    uv sync
fi

echo "Starting Django server on http://127.0.0.1:8002/ ..."
uv run python manage.py runserver 0.0.0.0:8002
