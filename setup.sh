#!/bin/bash
# setup.sh - Linux/Mac setup script for DJPOS

echo "Setting up DJPOS..."

## Checking if uv is installed, and setting up evironment using it.
if command -v uv &> /dev/null; then
    echo "uv is installed. Initializing virtual environment..."
    uv init
    if [ ! -f "requirements.txt" ]; then
        echo "Error: requirements.txt not found. Please ensure you are in the correct directory."
        exit 1
    fi
    uv add -r requirements.txt
    uv sync
    echo "Virtual environment setup complete."
    echo "running Django Migrations"
    uv run python manage.py migrate
    echo "Setup complete. You can now run the server using ./run.sh"
    exit 0

else
    echo "Error: uv command not found. Please install uv first."
    exit 1
fi
