#!/bin/bash

pyinstaller --onefile --name DJPOS-Till ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  launcher.py