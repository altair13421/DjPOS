#!/bin/bash
# run.sh - Linux/Mac running script for DJPOS

export ALLOWED_HOSTS="192.168.1.5,localhost,127.0.0.1"

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
if command -v uv &>/dev/null; then
  uv sync
  uv run python manage.py migrate
else
  echo "Error: uv command not found. Please install uv and initialize the virtual environment."
  exit 1
fi

if [ "$1" = "terminal" ]; then
  # read .env
  if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create a .env file with the required environment variables."
    cp terminal.env.example terminal.env
    echo "A sample .env file has been created as .env. Please edit it with your configuration."
    exit 1
  fi

  export $(grep -vE '^[[:space:]]*(#|$)' terminal.env | xargs)
  uv run python manage.py migrate

  if [ "$2" ]; then
    echo "Running terminal command: $2"
    uv run python manage.py $2
    exit 0
  fi

  uv run python manage.py sync_now # first pull: org, users, catalog
  uv run python manage.py runserver 0.0.0.0:8001
fi

if [ "$1" = "server" ]; then
  # read .env

  if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create a .env file with the required environment variables."
    cp server.env.example server.env
    echo "A sample .env file has been created as .env. Please edit it with your configuration."
    exit 1
  fi

  export $(grep -vE '^[[:space:]]*(#|$)' server.env | xargs)
  uv run python manage.py migrate

  if [ "$2" ]; then
    echo "Running Server command: $2"
    uv run python manage.py $2
    exit 0
  fi
  echo "Starting DJPOS Server..."
  # Starting the server
  echo "Starting Django server on http://127.0.0.1:8002/ ..."
  uv run python manage.py runserver 0.0.0.0:8002
fi
