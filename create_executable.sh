#!/bin/bash

uv run python manage.py collectstatic --noinput
uv run pyinstaller --noconsole \
  --collect-all webview --collect-all qtpy --collect-all PyQt6 \
  --add-data "staticfiles:staticfiles" \
  launcher.py
