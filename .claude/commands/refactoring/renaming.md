Rename a symbol (variable, function, class, file) across the Launchpad codebase.

## Steps

1. Accept the old name and new name from the argument.
2. Determine the symbol type:
   - Python variable, function, or class name.
   - File or directory name.
   - Database column or table name (in SQL templates and migrations).
   - Pydantic model or field name.
   - Error code constant.
   - Temporal workflow or activity name.
   - Product enum value.
3. Find all references to the symbol:
   - **Source code**: imports, usages, type references across `app/`.
   - **SQL templates**: References in `app/sql/` Jinja2 templates (column names, table names).
   - **Migrations**: References in `db/migrations/` (requires new migration for DB renames).
   - **Configuration**: `policy.csv` (operation IDs), `worker_settings.py`, product settings.
   - **Error codes**: `app/exceptions/error_codes.py`, exception files.
   - **Models**: Pydantic field aliases in `app/models/` (check `alias` and `by_alias`).
   - **Templates**: Product template files under `app/cli/temporal/<product>/templates/`.
4. If renaming a route `operation_id`:
   - Update the route decorator in `app/routes/`.
   - Update `app/core/pycasbin/policy.csv`.
   - Run `uv run python app/pre_commit_checks.py` to verify sync.
5. If renaming a database column:
   - Create a new migration: `dbmate new rename_<old>_to_<new>`.
   - Update all SQL templates in `app/sql/` that reference the column.
   - Update Pydantic models if field names changed.
6. If renaming a Temporal workflow or activity:
   - Update the class name and `@workflow.defn`/`@activity.defn(name=...)`.
   - Update `app/core/cli_settings.py` worker configuration.
   - Update any `get_workflow_id()` methods that use the class name.
   - Check for in-flight workflows that reference the old name.
7. If renaming a product:
   - Update `ProductEnum` in `app/models/product.py`.
   - Update product settings in `app/core/product_settings/`.
   - Update workflow package directory `app/cli/temporal/<product>/`.
   - Update template directory and all template files.
   - Update `WorkerQueues` in `app/core/cli_settings.py`.
8. Preview all changes before applying:
   - Show each file that will be modified with the specific line changes.
   - Highlight any ambiguous matches that might be false positives.
9. Apply changes across all files simultaneously.
10. Run verification:
    - `ruff format . && ruff check --fix .`
    - `uv run python app/pre_commit_checks.py`

## Format

```
Rename: <old-name> -> <new-name>
Type: <function|variable|class|file|column|operation_id|workflow|activity|product>

Files affected: <N>
  - <file>:<line> - <context of change>

Cross-cutting updates:
  - [ ] policy.csv updated (if operation_id)
  - [ ] SQL templates updated (if column/table)
  - [ ] Migration created (if column/table)
  - [ ] worker_settings.py updated (if workflow/activity)
  - [ ] Product settings updated (if product)
  - [ ] Templates updated (if product/workflow)

Verification:
  - Ruff: <pass/fail>
  - Pre-commit checks: <pass/fail>
```

## Rules

- Show a preview of all changes and get confirmation before applying.
- Handle case sensitivity: distinguish `myFunc`, `MyFunc`, `MY_FUNC`.
- Do not rename symbols in virtual environments or dependency directories.
- Preserve casing conventions: snake_case for Python, camelCase for DB columns and JSON, PascalCase for classes.
- Check for string literals that reference the symbol name (API routes, error messages, SQL column names).
- Update both the symbol and related names (e.g., renaming `Dexit` should also update `DexitOnboardingWorkflow`, `DexitDeProvisioningWorkflow`, `dexit_onboarding` queue, etc.).
- For database renames, always create a migration — never modify existing migrations.
- For Temporal workflow renames, consider in-flight workflow compatibility.
