# DjPOS — Repository Overview

Django-based open-source Point of Sale with inventory, bundles, stock tracking, sales, and REST APIs. Currency defaults to **PKR**.

## Purpose

Single-operator POS for recording sales, managing stock (items, categories, bundles), and viewing basic analytics. Ships with server-rendered UI plus Django REST Framework APIs.

## Tech stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.10–3.13 (pinned via `.python-version`) |
| Package manager | [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`) |
| Framework | Django 5.x |
| API | Django REST Framework |
| DB (local) | SQLite when `POSTGRES_HOST` is unset |
| DB (deploy) | PostgreSQL (`psycopg2-binary`) |
| Tests | pytest + pytest-django |
| Deploy | Docker / Docker Compose, Render (`render.yaml`), Gunicorn |

## Layout

```
DjPOS/
├── config/           # Project settings, root URLconf, WSGI/ASGI
├── pos/              # Sales UI, customers, cart/sale models, analytics API
├── inventory/        # Categories, items, bundles, stock logs, CRUD UI
├── utils/            # Shared business logic (StockManager, ESC/POS receipts)
├── templates/        # Django templates (base + pos + inventory)
├── static/           # CSS, JS, images
├── roadmap/          # Implementation notes / verification
├── manage.py
├── pyproject.toml    # Dependencies & tool config (uv)
├── uv.lock           # Locked dependency graph
└── OVERVIEW.md       # This file
```

## Apps & domain model

### `pos`

| Model | Role |
| --- | --- |
| `Customer` | Optional buyer on a sale (name, email, phone) |
| `Sale` | Transaction: discount, tax, total, paid, change |
| `CartItem` | Line on a sale — either an `Item` or a `Bundle` |

Web routes (under `/pos/`): sale panel, sale history, receipt.  
API (under `/pos/api/`): customers, sales, analytics.

### `inventory`

| Model | Role |
| --- | --- |
| `Category` | Groups items; auto `identifier` from name |
| `Item` | SKU, qty, cost/retail/wholesale, active/ingredient flags |
| `Bundle` / `BundleItem` | Packaged deals (items and nested bundles) |
| `StockLog` | Stock deltas with reason, revenue, cost |

Web routes (under `/inventory/`): categories, items, bundles, stats.  
API (under `/inventory/api/`): categories, items, bundles, stock_logs.

### `utils`

- `StockManager` — deduct / restock with logging
- `receipt_escpos` — network thermal receipt printing when web print is off

## Request flow

```
Browser / API client
        │
        ▼
config/urls.py  →  /pos/ | /inventory/ | /admin/
        │
        ├─ Template views (CBVs / FBV)
        └─ DRF routers (ViewSets)
                │
                ▼
         models + utils.StockManager
                │
                ▼
         SQLite or PostgreSQL
```

## Key URLs

| Path | Description |
| --- | --- |
| `/` | Redirects to `/pos/` |
| `/admin/` | Django admin |
| `/pos/` | POS home / sale UI |
| `/pos/api/` | Customers, sales, analytics |
| `/inventory/` | Inventory home |
| `/inventory/stats/` | Sold / restocked overview |
| `/inventory/api/` | Categories, items, bundles, stock logs |

## Configuration

Set via environment (see `config/settings.py`):

| Variable | Default / notes |
| --- | --- |
| `DEBUG` | `True` |
| `DJANGO_SECRET_KEY` | insecure default for local only |
| `ALLOWED_HOSTS` | comma-separated hosts |
| `POSTGRES_*` | If `POSTGRES_HOST` empty → SQLite |
| `USE_WEB_PRINT` | `true` = browser print; `false` = ESC/POS |
| `PRINTER_HOST` / `PRINTER_PORT` | Thermal printer (default port 9100) |
| `RECEIPT_STORE_NAME` | Receipt header |

## Commands (uv)

```bash
# Install (creates .venv, syncs lockfile)
uv sync

# Dev server
uv run python manage.py runserver 0.0.0.0:8002

# Migrations
uv run python manage.py migrate

# Superuser
uv run python manage.py createsuperuser

# Seed sample inventory
uv run python manage.py seed_dummy_inventory

# Tests
uv run pytest

# Add a dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>
```

Convenience scripts `./setup.sh` and `./run.sh` (and Windows `.bat` counterparts) wrap the same uv workflow.

## Testing

- Config: `[tool.pytest.ini_options]` in `pyproject.toml`
- Suites: `inventory/tests/`, `pos/tests/`
- Run: `uv run pytest`

## Deployment notes

- **Docker**: `Dockerfile` + `docker-compose.yaml` (web on port 8000)
- **Render**: `render.yaml` / `Procfile`
- Production should set `DEBUG=False`, a real `DJANGO_SECRET_KEY`, and PostgreSQL env vars

## Related docs

- [README.md](README.md) — quick start
- [roadmap/implementation_plan.md](roadmap/implementation_plan.md) — architecture roadmap
- [walkthrough.md](walkthrough.md) — setup scripts & inventory stats notes
