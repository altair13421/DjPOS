#!/bin/bash
# run.sh - Linux/Mac running script for DJPOS

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
    uv run python manage.py migrate
else
    echo "Error: uv command not found. Please install uv and initialize the virtual environment."
    exit 1
fi


if [ "$1" = "terminal" ]; then
  if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create a .env file with the required environment variables."
    cp terminal.env.example terminal.env
    echo "A sample .env file has been created as .env. Please edit it with your configuration."
    exit 1
  fi

  # read .env
  export $(grep -v '^#' terminal.env | xargs)

  uv run python manage.py sync_now      # first pull: org, users, catalog
  uv run python manage.py runserver 0.0.0.0:8001
fi


if [ "$1" = "server" ]; then
    echo "Starting DJPOS Server..."

    if [ ! -f ".env" ]; then
        echo "Error: .env file not found. Please create a .env file with the required environment variables."
        cp server.env.example server.env
        echo "A sample .env file has been created as .env. Please edit it with your configuration."
        exit 1
    fi

    # read .env
    export $(grep -v '^#' server.env | xargs)

    # Starting the server
    echo "Starting Django server on http://127.0.0.1:8002/ ..."
    uv run python manage.py runserver 0.0.0.0:8002
fi
