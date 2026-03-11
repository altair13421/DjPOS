@echo off
echo Starting DJPOS Server...

IF NOT EXIST ".venv" (
    echo Error: Virtual environment '.venv' not found.
    echo Please run setup.bat first to install dependencies.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting Django server on 0.0.0.0:8002...
python manage.py runserver 0.0.0.0:8002
pause
