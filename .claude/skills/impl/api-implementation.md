---
name: api-implementation
description: Patterns for creating FastAPI route handlers, registration, and policy.
---

## Route Handler

1. Create/update handler in `app/routes/<module>.py`
2. Add `operation_id`, `response_model`, `status_code`, `tags`
3. Product-scoped routes take `{product}` path parameter

## Registration

1. Register route in `app/routes/__init__.py` (if new module)
2. Add policy entry to `app/core/pycasbin/policy.csv`
3. Run `uv run python app/pre_commit_checks.py` to verify sync

## Key Decisions

| Decision | Convention |
|----------|-----------|
| Auth required? | `/api/v1/` = yes (Keycloak), self-signup routes = conditional |
| Status code | POST=201, GET=200, PUT=200, DELETE=204 |
| Error responses | `ServerErrorModel.initialize()` codes via `.exc()` |
| DB access | `DBManager()` → `db.fetch_one/fetch_all/execute` |
| Product routing | `ProductEnum` validation on `{product}` path param |
