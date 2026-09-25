#!/bin/bash
# run.sh - Linux/Mac running script for DJPOS

if [ "$1" = "terminal" ]; then
  export APP_ROLE=terminal
  export DEVICE_ID="${DEVICE_ID:-TILL1}"
  export DEVICE_KEY="${DEVICE_KEY:?Set DEVICE_KEY first - do NOT commit it}"
  export CENTRAL_URL="${CENTRAL_URL:-http://127.0.0.1:8000}"
  export RUN_SYNC_WORKER=1
  python manage.py migrate
  python manage.py sync_now      # first pull: org, users, catalog
  exec python manage.py runserver 0.0.0.0:8001
fi

echo "Starting DJPOS Server..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment '.venv' not found."
    echo "Please run ./setup.sh first to install dependencies."
    exit 1
fi

## Checking if uv is initialized in this directory
if [ ! -f ".python-version" ] && [ ! -d ".venv" ]; then
    echo "Error: uv not initialized in this directory."
    echo "Please run 'uv init' first."
    exit 1
fi


# Using uv to sync the virtual environment
if command -v uv &> /dev/null; then
    uv sync
else
    echo "Error: uv command not found. Please install uv and initialize the virtual environment."
    exit 1
fi


# Starting the server
echo "Starting Django server on http://127.0.0.1:8002/ ..."
uv run python manage.py runserver 0.0.0.0:8002
