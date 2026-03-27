---
name: jinja2-sql
description: Jinja2 SQL templating patterns for this repo. Covers query writing, custom filters (bind, sqlsafe, inclause), DBManager execution, and file organization. Use PROACTIVELY when writing or modifying .sql files, database queries, or DBManager calls.
---

## Architecture Overview

SQL queries are Jinja2 templates stored as `.sql` files. They are loaded by `JinjaSql` (custom engine in `app/core/jinjasql.py`), which auto-binds all `{{ variables }}` into parameterized queries, then executed against PostgreSQL via `asyncpg`.

```
Python code                    Jinja2 Template              asyncpg
───────────                    ───────────────              ──────
db.fetch_all(                  app/sql/get_tenant.sql       SELECT ... WHERE id = $1
  "get_tenant.sql",       →    {{ tenant_id }}         →    values: [uuid]
  tenant_id=uuid
)
```

**Key guarantee:** Every `{{ variable }}` is automatically parameter-bound. You never build raw SQL strings in Python.

## Directory Structure

```
app/sql/
├── get_tenant.sql              # Flat files at root level
├── create_tenant.sql
├── get_plans.sql
├── delete.sql
├── penknife/                   # Product-specific subdirectories
│   └── *.sql
└── muspell/
    └── *.sql
```

### File Naming

| Pattern | Convention | Examples |
|---------|-----------|---------|
| Simple CRUD | `verb_noun.sql` | `get_tenant.sql`, `create_tenant.sql` |
| By identifier | `get_noun_by_field.sql` | `get_tenant_by_name.sql`, `get_email_template_by_product.sql` |
| Product-specific | `product/verb_noun.sql` | `penknife/get_config.sql` |

Flat structure at root. Use product subdirectories only for product-specific queries.

## Custom Filters

The `JinjaSql` engine (`app/core/jinjasql.py`) registers these filters:

### `bind` (auto-applied)
Every `{{ variable }}` is automatically wrapped with `| bind` by the `SqlExtension` during lexing. You never need to use this manually.

```sql
-- You write:
WHERE tenantname = {{ tenant_name }}

-- Engine sees:
WHERE tenantname = {{ (tenant_name) | bind("tenant_name") }}

-- Output:
WHERE tenantname = $1    (with tenant_name value bound)
```

### `sqlsafe` — Raw SQL insertion (no binding)

**`sqlsafe` bypasses all parameter binding. Misuse = SQL injection.**

Allowed uses — strictly limited to:

| Allowed | Example | Reason |
|---------|---------|--------|
| `OFFSET` / `LIMIT` | `OFFSET {{ offset \| sqlsafe }}` | Integer pagination values |
| Table/column names | `{{ table \| sqlsafe }}` | Only in generic templates |

**NEVER use `sqlsafe` on:**
- User-provided values (search terms, status strings, filter values)
- Query fragments built from user input

```sql
-- BAD: sqlsafe on a search value — SQL injection
ILIKE '%%{{ data["value"] | sqlsafe }}%%'

-- GOOD: Let auto-binding handle all values
ILIKE {{ '%' ~ data["value"] ~ '%' }}
```

### `inclause` — Lists/arrays to PostgreSQL arrays
Converts Python lists/tuples to `array[...]::type[]` syntax with proper type casting.

```sql
-- Python: tenant_ids=[uuid1, uuid2]
AND id = ANY({{ tenant_ids | inclause }}::uuid[])
```

Type inference is automatic:
- `UUID` values → `::uuid[]`
- `dict` values → `::json[]`
- Other → no cast suffix

## Common SQL Patterns

### 1. Simple WHERE

```sql
SELECT * FROM customer
WHERE tenantname = {{ tenant_name }} AND product = LOWER({{ product }});
```

### 2. Conditional WHERE Clauses

Use `{% if %}` with `is defined` guards for optional filters:

```sql
SELECT * FROM customer
WHERE 1 = 1
{% if tenant_name is defined %}
    AND tenantname = {{ tenant_name }}
{% endif %}
{% if product is defined %}
    AND product = LOWER({{ product }})
{% endif %}
```

### 3. CTE (Common Table Expression)

```sql
WITH customer_insert AS (
    INSERT INTO customer (orgname, tenantname, email, product)
    VALUES ({{ orgname }}, {{ tenantname }}, {{ email }}, LOWER({{ product }}))
    RETURNING id
)
INSERT INTO provisioningstatus (customerid, status, errors)
VALUES ((SELECT id FROM customer_insert), {{ status }}, {{ errors }})
RETURNING customerid AS id;
```

### 4. String Pattern Matching

```sql
WHERE tenantname ILIKE {{ '%' ~ search_term ~ '%' }}
```

### 5. Multi-Row INSERT

```sql
INSERT INTO emails (product, template_name, subject, body)
VALUES
{% for email in emails %}
    ({{ email.product }}, {{ email.template_name }}, {{ email.subject }}, {{ email.body }})
    {% if not loop.last %}, {% endif %}
{% endfor %}
```

### 6. RETURNING Clause

```sql
INSERT INTO customer (orgname, tenantname, email)
VALUES ({{ orgname }}, {{ tenantname }}, {{ email }})
RETURNING id, tenantname;
```

## DBManager API (`app/core/db.py`)

### Query Methods

| Method | Returns | Use Case |
|--------|---------|----------|
| `fetch_all(sqlfile, **kwargs)` | `list[Record]` | SELECT returning multiple rows |
| `fetch_one(sqlfile, **kwargs)` | `Record` | SELECT returning single row |
| `execute(sqlfile, **kwargs)` | `None` | INSERT/UPDATE/DELETE without return |
| `execute_many(queries)` | `None` | Multiple queries in one transaction |

### Usage Examples

```python
from app.core.db import DBManager

db = DBManager()

# Single row fetch
tenant = await db.fetch_one("get_tenant_by_name.sql", tenant_name=name, product=product)

# Multi-row fetch
plans = await db.fetch_all("get_plans.sql", product=product)

# Insert with RETURNING
result = await db.execute("create_tenant.sql", orgname=org, tenantname=name, email=email, ...)
```

## Anti-Patterns

### 1. NEVER use string concatenation for SQL

```python
# BAD
query = f"SELECT * FROM customer WHERE id = '{customer_id}'"

# GOOD
result = await db.fetch_one("get_tenant.sql", tenant_id=customer_id)
```

### 2. NEVER use `join(',')` to bypass parameter binding

```sql
-- BAD: Injects raw values
WHERE id IN ({{ ids | join(',') }})

-- GOOD: Proper binding
WHERE id = ANY({{ ids | inclause }}::uuid[])
```

### 3. NEVER use `sqlsafe` on user input

```sql
-- BAD
WHERE status = {{ status | sqlsafe }}

-- GOOD
WHERE status = {{ status }}
```

### 4. Use Jinja2 concatenation for LIKE, not PostgreSQL `||`

```sql
-- BAD
WHERE name ILIKE '%%' || {{ term }} || '%%'

-- GOOD
WHERE name ILIKE {{ '%' ~ term ~ '%' }}
```

## Migrations (dbmate)

```bash
dbmate new add_myfeature_table    # Create new migration
python db/migrate.py              # Apply migrations
```

### Migration Template

```sql
-- db/migrations/YYYYMMDDHHMMSS_add_myfeature_table.sql

-- migrate:up
CREATE TABLE IF NOT EXISTS myfeature (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" VARCHAR(255) NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- migrate:down
DROP TABLE IF EXISTS myfeature;
```

## Key Files

| File | Purpose |
|------|---------|
| `app/core/db.py` | DBManager, asyncpg pool |
| `app/core/jinjasql.py` | Custom JinjaSql engine with filters (bind, sqlsafe, inclause) |
| `app/sql/` | Jinja2 SQL templates |
| `db/migrations/` | dbmate migration files |
| `db/migrate.py` | Migration runner |
