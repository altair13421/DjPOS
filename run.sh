#!/bin/bash
# run.sh - Linux/Mac running script for DJPOS

echo "Starting DJPOS Server..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment '.venv' not found."
    echo "Please run ./setup.sh first to install dependencies."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Start the server
echo "Starting Django server on http://127.0.0.1:8002/ ..."
python manage.py runserver 0.0.0.0:8002
