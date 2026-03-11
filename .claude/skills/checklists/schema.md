---
name: checklist-schema
description: Database schema and migration standards. Loaded during review and implementation.
---

- UUID v7 for primary keys (or `gen_random_uuid()`)
- `TIMESTAMPTZ` for all timestamps
- `"camelCase"` column names (quoted in SQL)
- `-- migrate:up` and `-- migrate:down` sections present
- Changes must be backwards-compatible — no destructive column renames without a migration strategy
- Product-specific SQL in `app/sql/<product>/` subdirectories
