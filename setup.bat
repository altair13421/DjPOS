@echo off
echo Setting up DJPOS with uv...

where uv >nul 2>&1
IF ERRORLEVEL 1 (
    echo Error: uv is not installed.
    echo Install it from https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo Syncing dependencies from pyproject.toml / uv.lock...
uv sync

echo Running migrations...
uv run python manage.py migrate

echo Setup complete! To start the server, run:
echo setup.bat then run.bat, or:
echo uv run python manage.py runserver 0.0.0.0:8002
pause
