# Common Operations Reference

Centralized reference for frequently used commands. **Reference this file instead of duplicating commands across workflow/command files.**

## Code Quality

### Formatting & Linting
```bash
ruff format .                                    # Format all files
ruff format --check .                           # Check formatting (CI)
ruff check .                                    # Lint (no auto-fix)
ruff check --fix .                              # Lint with auto-fix
```

### Pre-commit Checks
```bash
uv run python app/pre_commit_checks.py          # Validate OpenAPI spec and worker config sync
```

## Testing

### Run Tests
```bash
# Full suite with coverage
uv run pytest --cov=./app test/ -s -v \
  -W ignore::DeprecationWarning:opentelemetry.instrumentation.dependencies \
  --cov-report term-missing

# Single test file
uv run pytest test/test_file.py -s -v

# Single test
uv run pytest test/test_file.py::TestClass::test_method -s -v
```

## Database

### Migrations
```bash
dbmate new <migration_name>                     # Create new migration
python db/migrate.py                            # Apply migrations (requires APP_CONFIG_FILE)
dbmate status                                   # Check migration status
```

## Security

```bash
bandit -r app/ -ll                              # Security scan
```

## Dependency Management

```bash
uv sync                                         # Install dependencies
uv sync --frozen                                # Install with locked versions
```

## Git Operations

```bash
git add <specific-files>                        # Stage specific files (never git add -A)
```

## Environment Variables

```bash
export APP_CONFIG_DIR="/path/to/config"          # Set config directory
export DEPLOYMENT="integration"                  # Set deployment environment (integration/production)
```

## Docker

```bash
./docker-build.sh                               # Build Docker image (multi-stage)
```
