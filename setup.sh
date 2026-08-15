#!/bin/bash
# setup.sh - Linux/Mac setup script for DJPOS (uv)

set -euo pipefail

echo "Setting up DJPOS with uv..."

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed."
    echo "Install it from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "Syncing dependencies from pyproject.toml / uv.lock..."
uv sync

echo "Running migrations..."
uv run python manage.py migrate

echo "Setup complete! To start the server, run:"
echo "  ./run.sh"
echo "or:"
echo "  uv run python manage.py runserver 0.0.0.0:8002"
