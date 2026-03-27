# Coding Patterns

Rules enforced when writing or modifying code in this repo.

## Dependency Flow (Enforced)

```
app/core/  ->  app/models/  ->  app/routes/  |  app/cli/  |  app/utils/
```

**Hard rules**:
- `app/core/` MUST NOT import from `app/routes/`, `app/cli/`, or `app/utils/`.
- `app/models/` are purely functional -- NO database queries, NO side effects.
- `app/routes/` may import from `app/models/`, `app/core/`, `app/exceptions/`.
- `app/cli/temporal/` may import from `app/models/`, `app/core/`.

## Forbidden Patterns

| Pattern | Use Instead |
|---------|-------------|
| `Optional[X]` | `X \| None` |
| Pydantic V1 (`@validator`, `class Config`) | Pydantic V2 (`@field_validator`, `model_config`) |
| Raw SQL string concatenation | Jinja2 SQL templates in `app/sql/` |
| `| sqlsafe` on user input | `{{ var }}` parameterized binding |
| `datetime.now()` in workflows | `workflow.now()` |
| Direct I/O in workflows | Use activities |
| `git add -A` or `git add .` | `git add <specific-files>` |
| `open()`, `tempfile`, `pathlib` for cloud files | OpenDAL via `app/utils/file_operations.py` |

## SQL Template Rules

- Use `{{ var }}` for parameterized binding (automatically handled by `SqlExtension` in `app/core/jinjasql.py`).
- `| sqlsafe` ONLY for trusted values: column names, `LIMIT`, `OFFSET`, `ORDER BY` direction.
- Never use `| sqlsafe` on user input or filter values.
- SQL template files live in `app/sql/` with product-specific subdirectories (`app/sql/penknife/`, `app/sql/muspell/`).

## Temporal Workflow Rules

- **No I/O in workflows**: workflows orchestrate only; any DB/network/file I/O belongs in **activities**.
- **Determinism**: never call `datetime.now()` or `random` in workflow code.
- **Activities** must implement `get_timeout()`, `get_retry_policy()`, and `defn()`.
- **Base classes**: `Activity`, `Workflow`, `ScheduleWorkflow` in `app/cli/temporal/core/base.py`.
- **Input models**: subclass `LaunchpadCLIBaseModel` (allows extra fields).
- **Worker registration**: all workflows must appear in `app/core/cli_settings.py`.

## Error Handling

- Use `ServerErrorModel.initialize("CODE")` to create error constants.
- Raise with `.exc(**params)` -- supports `str.format()` placeholders in `displayMessage`.
- Error codes follow the convention: C=Common, R=Route, T=Task; 1000=App, 2000=Internal, 3000=External, 4000=Config, 5000=Auth.
- Define domain errors near their usage, not in a global catch-all file.

## Dependency Vulnerability Resolution (OSV)

Pre-commit runs `osv-scanner` against `uv.lock`. When it flags a vulnerable package:

1. **Identify the fix version** from the osv-scanner output table (`FIXED VERSION` column).
2. **Update `pyproject.toml`** -- bump the pinned version to the fixed version (or higher).
3. **Regenerate the lock file**: `uv lock --upgrade-package <package-name>`.
4. **Re-run pre-commit** to confirm `osv-scanner` passes.
5. If `uv-sort` modifies `pyproject.toml` during commit, re-stage and commit again.
6. Exceptions can be added to `osv-scanner.config.toml` only when a fix is genuinely unavailable.

## Code Quality

- 120 character line length.
- Double quotes for strings.
- `ruff format` for formatting, `ruff check` for linting.
- No unused imports (except `__init__.py` F401 exemptions).
- UUID v7 for all primary keys.
- Async/await for all I/O operations.
