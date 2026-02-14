# OSPOS

A Django-based **Open Source Point of Sale (OSPOS)** project with **POS** and **Inventory** apps, REST APIs via Django REST Framework, and Docker support.

## What it does

- **POS app** – Point of sale: manage **Customers** and **Sales** (transactions). Customers have name, email, phone; sales have an optional customer and a total.
- **Inventory app** – Stock: manage **Categories** and **Items**. Categories group items; items have name, SKU, quantity, unit price, and optional category.

Both apps expose:

- A basic web index page.
- A **REST API** (Django REST Framework) with list/create/read/update/delete for their models.

## Project structure

- `config/` – Django project settings and root URL config.
- `pos/` – POS app: `Customer`, `Sale` models; URLs and API under `/pos/` and `/pos/api/`.
- `inventory/` – Inventory app: `Category`, `Item` models; URLs and API under `/inventory/` and `/inventory/api/`.

## Requirements

- Python 3.10+
- PostgreSQL (when not using SQLite for local dev)

See `requirements.txt` for Python dependencies (Django, djangorestframework, psycopg2-binary).

## Quick start (local)

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run migrations (uses SQLite by default if no `POSTGRES_*` env vars are set):

   ```bash
   python manage.py migrate
   ```

3. (Optional) Create a superuser for the admin:

   ```bash
   python manage.py createsuperuser
   ```

4. Start the dev server:

   ```bash
   python manage.py runserver
   ```

- Admin: **http://127.0.0.1:8000/admin/**
- POS index: **http://127.0.0.1:8000/pos/**
- POS API: **http://127.0.0.1:8000/pos/api/** (customers, sales)
- Inventory index: **http://127.0.0.1:8000/inventory/**
- Inventory API: **http://127.0.0.1:8000/inventory/api/** (categories, items)

## Quick start (Docker)

The app runs with **Debian (bookworm-slim)** in the Dockerfile and **PostgreSQL** in Docker Compose.

1. From the project root:

   ```bash
   docker compose up --build
   ```

2. Migrations run on startup. Use the same URLs as above (e.g. **http://127.0.0.1:8000/**). To create an admin user inside the container:

   ```bash
   docker compose exec web python3 manage.py createsuperuser
   ```

## API overview

- **POS**
  - `GET/POST /pos/api/customers/` – list/create customers
  - `GET/PUT/PATCH/DELETE /pos/api/customers/<id>/` – single customer
  - `GET/POST /pos/api/sales/` – list/create sales
  - `GET/PUT/PATCH/DELETE /pos/api/sales/<id>/` – single sale

- **Inventory**
  - `GET/POST /inventory/api/categories/` – list/create categories
  - `GET/PUT/PATCH/DELETE /inventory/api/categories/<id>/` – single category
  - `GET/POST /inventory/api/items/` – list/create items
  - `GET/PUT/PATCH/DELETE /inventory/api/items/<id>/` – single item

Responses are JSON; pagination is enabled (page size 20).
