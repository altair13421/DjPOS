# Setup Scripts and Inventory Stats View

## Overview

Setup & run scripts and the Inventory Stats View for sold / restocked items.

## 1. Setup & Run Scripts

Helper scripts use [uv](https://docs.astral.sh/uv/) against `pyproject.toml` / `uv.lock`.

- `setup.bat` / `setup.sh`: `uv sync`, then `uv run python manage.py migrate`
- `run.bat` / `run.sh`: `uv run python manage.py runserver 0.0.0.0:8002`

## 2. Inventory Stats

See `/inventory/stats/` for sold and restocked overview.
