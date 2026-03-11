#!/bin/bash
# setup.sh - Linux/Mac setup script for DJPOS

echo "Setting up DJPOS..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running migrations..."
python manage.py migrate

echo "Setup complete! To start the server, run:"
echo "source .venv/bin/activate"
echo "python manage.py runserver"
