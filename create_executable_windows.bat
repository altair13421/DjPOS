@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv is required. Install it from https://docs.astral.sh/uv/
    exit /b 1
)

uv sync --locked
if errorlevel 1 exit /b %ERRORLEVEL%

uv run python manage.py collectstatic --noinput
if errorlevel 1 exit /b %ERRORLEVEL%

uv run pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --noconsole ^
  --name "DJPOS-Till" ^
  --collect-all django ^
  --collect-all webview ^
  --collect-all qtpy ^
  --collect-all PyQt6 ^
  --collect-all pos ^
  --collect-all inventory ^
  --collect-all users ^
  --collect-all sync ^
  --add-data "templates;templates" ^
  --add-data "staticfiles;staticfiles" ^
  launcher.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo Build complete: %~dp0dist\DJPOS-Till.exe
