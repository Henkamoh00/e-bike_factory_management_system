# 🔧 Developer Maintenance Guide

Quick reference for common changes. If you're looking for "where do I edit X?", check here first.

---

## ↩️ Chassis Return Reasons

The return reason list is an **Enum** — hardcoded, not free text. It exists in **three places** and all three must match exactly (character-for-character) or requests will fail with `422`:

| File | What to edit |
|---|---|
| `invoicing/schemas.py` | `ChassisReturnReason` enum |
| `ReturnFormModal.vue` | `reasonOptions` array |
| `PostSaleTrackingView.vue` | `OTHER_REASON_LABEL` constant (must match the "other" value) |

To add/remove/rename a reason: update all three, then update `FAULT_STAGE_MAP` in `ReturnFormModal.vue` if the reason should auto-open a fault (currently only chassis/electrical faults do).

---

## 📑 Assembly Stages

Stages (`تجميع_الهيكل`, `توصيل_الكهرباء_والغلاف`, `تجميع_كامل`) are defined in `app/models.py` → `AssemblyStage` enum.

Stage order/validation rules (what can follow what) live in `app/assembly_crud.py` → `_validate_stage_transition()`.

Display labels are duplicated in the frontend in **every file that shows a stage name**: `AssemblyFormModal.vue`, `ChassisOverviewList.vue`, `FaultsTab.vue`, `FaultRepairModal.vue`, `ReturnFormModal.vue`. There's no shared constant — if you add a stage, grep for `تجميع_الهيكل` across `frontend/src/` to find every label map that needs updating.

---

## 🔑 Roles & Tab Permissions

Roles are **database rows**, not code — managed from the UI (Settings → Roles). No code change needed to add a new role.

If you add a new **tab** (a new feature area):
1. Add its ID to `ALL_TAB_IDS` in `app/schemas.py` (backend)
2. Add it to `TAB_DEFINITIONS` in `useTabPermissions.js` (frontend) — must use the **same ID string**
3. Protect its routes with `require_tab("your_tab_id")` or `require_any_tab(...)` in the relevant router
4. If it's a full standalone page (like Invoices/Inventory) rather than a dashboard tab, add it to `standalonePages` in `DashboardView.vue` and register the route in `router/index.js`

`admin` always has every tab regardless of what's stored — don't try to "fix" this, it's intentional (see `_attach_role()` in `auth_crud.py`).

---

## 💰 Money / Decimal Fields

Every new endpoint returning a monetary amount **must** use a Pydantic `Decimal` field in its response schema. Never return a raw `dict` with a `Decimal` inside — FastAPI silently converts it to `float`, which loses precision on real currency values.

Never write `amount or 0` — `Decimal("0.00")` is falsy in Python. Use `amount if amount is not None else Decimal("0")`.

---

## 🕐 Time Handling

**Never** use `datetime.utcnow()` or compare an aware datetime to a naive one directly. Always go through `app/time_utils.py`:

| Need | Function |
|---|---|
| Current time to store | `utcnow()` |
| Normalize a DB value before comparing | `ensure_utc(dt)` |
| Display to the user | `to_local(dt)` / `format_local(dt)` |
| A filter value from a `<input type="date">` | `local_naive_to_utc(dt)` — interprets naive input as Algiers time |
| "Start of today/month/year" boundary | `local_start_of_day_utc(year, month, day)` |

If Algiers ever adopts DST or the business expands to another timezone, `APP_TZ` in `time_utils.py` is the single place to change.

---

## 🗑️ Soft Delete Pattern

Every deletable entity (`Worker`, `Customer`, `BikeType`, `BikeColor`, `User`) follows the same shape: `is_deleted` boolean + `deleted_by_id` FK. To add soft-delete to a new entity, copy the pattern from `workers_crud.py` (`soft_delete_worker`, `get_archived_workers`, `restore_worker`) — including the duplicate-name check on restore.

Don't hard-delete anything unless you're intentionally replicating the narrow exception in `invoices_crud.py::_hard_delete_invoice_with_last_item` (a brand-new invoice with zero payments — pure data-entry correction).

---

## 📜 Audit Logging

Call `audit_crud.log_action(db, action, entity_type, entity_id, user_id, entity_label=..., details=...)` right after `db.commit()` for any create/update/delete/cancel/restore. It's best-effort — a logging failure is swallowed and never breaks the calling operation. Don't wrap it in your own try/except; it already handles that internally.

`entity_type` values that already exist are listed in `logs.py` → `ENTITY_CHOICES`. Add a new value there when you introduce a new entity type, or it won't show up as a filter option in the Logs tab.

---

## 🧾 Invoice PDF / QR Verification

- PDF layout: `invoicing/pdf_generator.py` — each section is a separate `_draw_*()` function, called in order at the bottom of `generate_invoice_pdf()`.
- Company name/address come from `COMPANY_NAME` / `COMPANY_ADDRESS` env vars — don't hardcode them again.
- **Never change the field order or format in `verification.py::_canonical_payload()`** — doing so invalidates every QR code already printed on existing invoices (their signature will no longer match).
- Arabic text needs `_ar()` before drawing; numbers/English text don't.

---

## 🏗️ Adding a New Domain Module (like `invoicing/` or `inventory/`)

Follow the existing package layout exactly:
your_module/
├── models.py # SQLAlchemy models, import Base from app.database
├── schemas.py # Pydantic schemas
├── your_crud.py # business logic
└── routers/
└── your_router.py

Register the router in `app/main.py`. Import the module in `migrations/env.py` (next to `import invoicing.models`) so Alembic's autogenerate can see its tables.

---

## ✅ Before You Commit

```bash
cd backend
poetry run flake8 . --count --show-source --statistics
poetry run pytest test_suite/ -v --tb=short
poetry run pytest test_suite_invoices/ -v --tb=short
```

If you touched anything in `app/models.py`, `invoicing/models.py`, or `inventory/models.py`:
```bash
poetry run alembic revision --autogenerate -m "describe your change"
```
Then **review the generated migration file manually** before committing — autogenerate misses some changes (e.g. renamed columns show as drop+add and will lose data on real databases).