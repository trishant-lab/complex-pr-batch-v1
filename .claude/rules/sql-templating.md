# SQL Templating (Repo Conventions)

This repo uses **Jinja2-templated SQL** executed via **asyncpg** (no ORM). Binding is enforced by the custom Jinja lexer.

## Source of Truth (Files)

- **Jinja SQL engine & filters**: `app/core/jinjasql.py`
- **SQL templates**: `app/sql/*.sql` and `app/sql/<product>/*.sql`
- **DB access**: `app/core/db.py` (`DBManager`)

## Must-Follow Rules

- **No string concatenation**: never build raw SQL strings in Python.
- **Parameter binding**: always use `{{ var }}` -- binding is automatically applied by `SqlExtension` in `app/core/jinjasql.py`.
- **`sqlsafe` is dangerous**:
  - Allowed only for trusted, computed values (LIMIT/OFFSET, column names).
  - Never use `| sqlsafe` on user input or filter values.

## File Conventions

- SQL templates live in `app/sql/` at the root level.
- Product-specific queries go in subdirectories: `app/sql/penknife/`, `app/sql/muspell/`.
- Use descriptive names: `get_tenant.sql`, `insert_tenant.sql`, `update_subscription.sql`.
