# POS Implementation Roadmap (Modular & Clean Architecture)

## Goal Description
Transform the current skeleton into a functional single-user POS (Admin-focused) with a **highly modular architecture**. The system will feature:
1.  **Strict Modular Design**: Logic separated into `utils/`, constants into `choices.py`, and API into `api/` packages.
2.  **Modern Django Patterns**: Class-Based Views (CBVs/ViewSets) exclusively, TextChoices for enums.
3.  **Comprehensive Testing**: Full `pytest` suite from day one.
4.  **Feature Set**: Profit/Sales Analytics, Advanced Inventory (Bundles, Cost), and Stock Deductions.

## User Review Required
> [!IMPORTANT]
> **Refactoring**: I will restructure the app logic.
> *   **Utils**: A dedicated `utils/` package at the project root for business logic (e.g., `StockManager`).
> *   **Choices**: Enums (like `StockChangeReason`) will live in `choices.py` to keep models clean.
> *   **API**: Views will be strictly Class-Based (ViewSets) for consistency and testability.

## Proposed Changes

### Phase 1: Structure & Data Models
Establish the clean architecture first.

#### [NEW] [utils/stock_manager.py](file:///home/xraydisk/Programming/DjPOS/utils/stock_manager.py)
*   **Create root `utils` package**.
*   **`StockManager` class**: Encapsulate all inventory logic here.
    *   `deduct_stock(item, quantity, reason)`
    *   `restock_item(item, quantity)`
    *   This ensures `views.py` remains thin and logic is reusable.

#### [NEW] [inventory/choices.py](file:///home/xraydisk/Programming/DjPOS/inventory/choices.py)
*   **`StockChangeReason`**: Define `TextChoices` here.
    *   `SALE = "SALE", "Sale"`
    *   `RESTOCK = "RESTOCK", "Restock"`
    *   `WASTE = "WASTE", "Refill"` (etc.)

#### [MODIFY] [inventory/models.py](file:///home/xraydisk/Programming/DjPOS/inventory/models.py)
*   Import `StockChangeReason` from `.choices`.
*   **Add `cost_price`** to `Item`.
*   **Add `Bundle` model** (Many-to-Many with `Item`).
*   **Add `StockLog` model** (using `StockChangeReason`).

---

### Phase 2: API & Business Logic Integration
Connect the API using Class-Based Views and the new Utils.

#### [MODIFY] [pos/api/views.py](file:///home/xraydisk/Programming/DjPOS/pos/views.py)
*   **Refactor to `pos/api/views.py`** (if not already split, we keep `views.py` but ensure it uses CBVs).
*   **`SaleViewSet` (CBV)**:
    *   Override `perform_create` to call `StockManager.deduct_stock()`.
    *   Do *not* put logic directly in the view.

#### [NEW] [pos/api/analytics.py](file:///home/xraydisk/Programming/DjPOS/pos/api/analytics.py)
*   **`AnalyticsViewSet(ViewSet)`**:
    *   `@action(detail=False) daily_sales`: Returns sales data.
    *   `@action(detail=False) top_items`: Returns bestsellers.
    *   `@action(detail=False) profit`: Returns profit data.
    *   Calculations should ideally move to `utils/analytics.py` to keep this view clean.

---

### Phase 3: Testing & Configuration
Ensure stability with `pytest`.

#### [NEW] [pytest.ini](file:///home/xraydisk/Programming/DjPOS/pytest.ini)
*   Configure `DJANGO_SETTINGS_MODULE` and python files.

#### [NEW] [inventory/tests/test_logic.py](file:///home/xraydisk/Programming/DjPOS/inventory/tests/test_logic.py)
*   **Test `StockManager` directly**:
    *   `test_deduct_stock_success`: Verify count decreases and log is created.
    *   `test_insufficient_stock`: Verify error is raised (if applicable).

#### [NEW] [inventory/tests/test_models.py](file:///home/xraydisk/Programming/DjPOS/inventory/tests/test_models.py)
*   `test_bundle_creation`: Verify bundles link to items correctly.

## Verification Plan

### Automated Tests (Pytest)
*   **Run**: `pytest`
*   **Coverage**:
    *   Unit tests for `utils/stock_manager.py` (Pure logic tests).
    *   Integration tests for `SaleViewSet` (API tests).
    *   Model tests for `Bundle` and `StockLog`.

### Manual Verification
1.  Run `pytest` to ensure all tests pass.
2.  Use the API (via Swagger/Browsable API) to:
    *   Create a Bundle.
    *   Sell a Bundle.
    *   Check `StockLog` entries via Admin to confirm the `reason` is recorded correctly as "Sale".
