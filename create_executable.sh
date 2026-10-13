#!/bin/bash

uv run pyinstaller --noconsole --onefile --name "DJPOS-Till" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  launcher.py
