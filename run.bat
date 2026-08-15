@echo off
echo Starting DJPOS Server...

where uv >nul 2>&1
IF ERRORLEVEL 1 (
    echo Error: uv is not installed.
    echo Install it from https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

IF NOT EXIST ".venv" (
    echo Virtual environment '.venv' not found. Running uv sync...
    uv sync
)

echo Starting Django server on 0.0.0.0:8002...
uv run python manage.py runserver 0.0.0.0:8002
pause
