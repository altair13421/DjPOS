@echo off
echo Setting up DJPOS...

IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Running migrations...
python manage.py migrate

echo Setup complete! To start the server, run:
echo .venv\Scripts\activate
echo python manage.py runserver
pause
