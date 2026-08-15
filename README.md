# DJPOS

A Django-based **Open Source Point of Sale (DJPOS)** project with **POS** and **Inventory** apps, REST APIs via Django REST Framework, and Docker support.

For a fuller map of apps, models, and commands, see [OVERVIEW.md](OVERVIEW.md).

## What it does

- **POS app** – Point of sale: manage **Customers** and **Sales** (transactions). Customers have name, email, phone; sales have an optional customer and a total.
- **Inventory app** – Stock: manage **Categories**, **Items**, and **Bundles**. Categories group items; items have name, SKU, quantity, prices, and optional category.

Both apps expose:

- A basic web UI.
- A **REST API** (Django REST Framework) with list/create/read/update/delete for their models.

## Project structure

- `config/` – Django project settings and root URL config.
- `pos/` – POS app: `Customer`, `Sale`, `CartItem`; URLs and API under `/pos/` and `/pos/api/`.
- `inventory/` – Inventory app: `Category`, `Item`, `Bundle`, `StockLog`; URLs and API under `/inventory/` and `/inventory/api/`.
- `utils/` – Shared logic (`StockManager`, receipt printing).

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs and manages the Python version from `.python-version`)
- PostgreSQL (when not using SQLite for local dev)

Dependencies live in `pyproject.toml` and are locked in `uv.lock`.

## Quick start (local, uv)

1. Sync the environment and install dependencies:

   ```bash
   uv sync
   ```

   Or use the helper script:

   ```bash
   ./setup.sh          # Windows: setup.bat
   ```

2. Run migrations (uses SQLite by default if no `POSTGRES_*` env vars are set):

   ```bash
   uv run python manage.py migrate
   ```

3. (Optional) Create a superuser for the admin:

   ```bash
   uv run python manage.py createsuperuser
   ```

4. Start the dev server:

   ```bash
   uv run python manage.py runserver 0.0.0.0:8002
   ```

   Or:

   ```bash
   ./run.sh             # Windows: run.bat
   ```

- Admin: **http://127.0.0.1:8002/admin/**
- POS index: **http://127.0.0.1:8002/pos/**
- POS API: **http://127.0.0.1:8002/pos/api/** (customers, sales, analytics)
- Inventory index: **http://127.0.0.1:8002/inventory/**
- Inventory API: **http://127.0.0.1:8002/inventory/api/** (categories, items, bundles, stock_logs)

## Tests

```bash
uv run pytest
```

## Quick start (Docker)

The app runs with **Debian (bookworm-slim)** and **uv** in the Dockerfile.

1. From the project root:

   ```bash
   docker compose up --build
   ```

2. Migrations run on startup. Use the same URLs as above on port **8000**. To create an admin user inside the container:

   ```bash
   docker compose exec web uv run python manage.py createsuperuser
   ```

## API overview

- **POS**
  - `GET/POST /pos/api/customers/` – list/create customers
  - `GET/PUT/PATCH/DELETE /pos/api/customers/<id>/` – single customer
  - `GET/POST /pos/api/sales/` – list/create sales
  - `GET/PUT/PATCH/DELETE /pos/api/sales/<id>/` – single sale
  - `/pos/api/analytics/` – sales analytics actions

- **Inventory**
  - `GET/POST /inventory/api/categories/` – list/create categories
  - `GET/PUT/PATCH/DELETE /inventory/api/categories/<id>/` – single category
  - `GET/POST /inventory/api/items/` – list/create items
  - `GET/PUT/PATCH/DELETE /inventory/api/items/<id>/` – single item
  - Bundles and stock logs under `/inventory/api/bundles/` and `/inventory/api/stock_logs/`

Responses are JSON; pagination is enabled (page size 20).
