# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Launchpad is a multi-tenant onboarding and provisioning microservice used by multiple 314e products (Veritable, Jeeves, Dexit, Penknife, Practifly, PricedX, ZSegment, HDP, Muspell). It handles self-signup flows, tenant creation, billing integration (Stripe, Lago), and orchestrates complex provisioning workflows via Temporal (Kubernetes resources, databases, DNS, cloud storage, Keycloak realms). Built with FastAPI, AsyncPG, Jinja2 SQL templating, and Temporal workflows.

## Commands

### Dependencies
```bash
uv sync --frozen          # Install all dependencies (requires uv package manager)
pre-commit install        # Set up pre-commit hooks
```

### Running Locally
```bash
# Start API server
uvicorn app.main:fastapi_app --port 8000

# Start Temporal workers (via supervisor)
IS_CLI=TRUE supervisord -c /etc/services.d/launchpadcli/supervisord.conf
```

### Linting & Formatting
```bash
ruff format .             # Format code
ruff check .              # Lint
ruff check --fix .        # Lint with auto-fix
```

### Testing
```bash
# Run full test suite with coverage
uv run pytest --cov=./app test/ -s -v \
  -W ignore::DeprecationWarning:opentelemetry.instrumentation.dependencies \
  --cov-report term-missing

# Run a single test file
uv run pytest test/test_file.py -s -v

# Run a single test
uv run pytest test/test_file.py::TestClass::test_method -s -v
```

### Database Migrations
```bash
dbmate new {migration_name}    # Create new migration in db/migrations/
python db/migrate.py           # Apply migrations (requires APP_CONFIG_FILE)
```

Migration files live in `db/migrations/` (SQL with `-- migrate:up` / `-- migrate:down` sections). Atlas Go migrations in `atlas_go/`.

### Pre-commit Checks
Pre-commit hooks run: `uv-sort`, `ruff-format`, `ruff`, `bandit`, `osv-scanner`, `gitleaks`, and a custom `app/pre_commit_checks.py` that validates OpenAPI spec and worker config sync.

When `osv-scanner` blocks a commit due to a vulnerable dependency: update the version in `pyproject.toml`, run `uv lock --upgrade-package <pkg>`, and re-commit. See `.claude/rules/coding-patterns.md` for the full process.

### Docker Build
```bash
./docker-build.sh         # Custom multi-stage build
```

## Architecture

### Dependency Flow
```
app/core/ -> app/models/ -> app/routes/ | app/cli/ | app/utils/
```
**`app/core/` must not import from other app directories** (except standard lib and third-party). Models are purely functional -- no database queries in model files.

### Key Layers

**API Server** (`app/main.py`): FastAPI app as `fastapi_app`. API prefix is `/api/v1/`.

**Routes** (`app/routes/`):

| Route prefix | Module | Purpose |
|---|---|---|
| `/provisioning/{product}` | `provisioning.py` | Trigger tenant provisioning workflow |
| `/deprovisioning/{product}` | `deprovisioning.py` | Trigger tenant deprovisioning |
| `/tenant/{product}` | `tenant.py` | List/update tenants |
| `/product` | `product.py` | List products |
| `/User/{product}` | `users.py` | User management |
| `/EmailTemplate/{product}` | `email_templates.py` | Email template CRUD |
| `/deployment/{product}` | `deployment.py` | K8s deployment ops |
| `/webhooks/billing` | `webhooks/billing_events.py` | Lago invoice webhooks |

**Self-Signup Routes** (`app/routes/self_signup/`):

| Route prefix | Module | Purpose |
|---|---|---|
| `/signup/{product}` | `signup.py` | User registration |
| `/plans/{product}` | `plans.py` | Pricing plans |
| `/addOns/{product}` | `add_ons.py` | Product add-ons |
| `/coupon/{product}` | `coupon.py` | Coupon validation |
| `/subscriptions/{product}` | `subscriptions.py` | Subscription management |
| `/onboard` | `onboard.py` | Start onboarding workflow |
| `/session/{product}` | `user_session.py` | Session/token management |
| `/otp/{product}` | `user_otp.py` | OTP generation/validation |
| `/portalLink/{product}` | `tenant_link.py` | Portal link generation |

**Temporal Workers** (`app/cli/temporal/`): Three supervisor-managed worker processes with queue-based workflow routing (`app/core/cli_settings.py`). Per-product workflow packages:
- `veritable/`, `jeeves/`, `dexit/`, `penknife/`, `practifly/`, `pricedx/`, `zsegment/`, `hdp/`, `muspell/`
- Each contains `workflows/onboarding.py` and optionally `deprovisioning.py`
- 60+ activities in `activities/` (K8s, Postgres, Keycloak, CloudFlare, DNS, 1Password, email, billing)
- Base classes in `app/cli/temporal/core/base.py`: `Activity`, `Workflow`, `ScheduleWorkflow`

**Database** (`app/core/db.py`): AsyncPG with connection pooling. Raw SQL via Jinja2-templated queries in `app/sql/` (no ORM). `DBManager` provides `fetch_all`, `fetch_one`, `execute`, `execute_many`.

**Configuration** (`app/core/settings.py`): Loaded from JSON config files via `APP_CONFIG_DIR` env var using OpenDAL. Separate product configs in `app/core/product_settings/`. Accessed via `get_settings()` singleton.

**Authentication & Authorization**:
- Keycloak for OAuth2/OIDC (`app/core/oauth2.py`)
- PyCasbin for RBAC (`app/core/pycasbin/`)
- Middleware stack order (important): PrometheusMiddleware -> AuthorizationMiddleware -> AuthenticationMiddleware -> CORSMiddleware -> LoggerMiddleware

**Products** (`app/models/product.py`): `ProductEnum` with 8 supported products. Each product has its own Temporal workflow package, config settings, and Keycloak realm/template files.

### Key Patterns
- **Async-first**: All I/O uses async/await
- **Pydantic V2** for all request/response models
- **UUID v7** for primary keys
- **OpenDAL** for cloud-agnostic blob/file storage
- **Jinja2 SQL** templates in `app/sql/` -- no raw SQL string concatenation
- **S6 overlay** for process management in Docker (uvicorn server + Temporal workers)
- **Per-product provisioning**: Each product is a self-contained workflow package

## Code Change Discipline
- **DRY within a single file** -- when making the same structural change on multiple lines in one file, stop and consider whether a utility function, helper, or (for Jinja SQL) a custom filter would be better than duplicating the pattern. Propose the abstraction before applying the repetitive change.
- Only modify files and code directly related to the requested task. No unsolicited refactoring.

## Code Quality

- **Line length**: 120 characters
- **Python target**: 3.13 (runtime), ruff targets 3.13
- **Formatter**: ruff format (double quotes)
- **Imports**: Sorted by uv-sort; unused imports in `__init__.py` are allowed (F401 ignored)
- **Security scanning**: bandit (severity low-low), gitleaks for secrets, osv-scanner for dependency vulnerabilities

## Git Workflow

Branch strategy, merge rules, and release process are defined in `.claude/rules/git-workflow.md`. Always follow these rules for branch creation, PRs, and releases.

## Error Handling

- **Error model**: `ServerErrorModel` in `app/exceptions/error_code_mapper.py`
- **Exception class**: `LaunchpadHTTPException`
- **Error codes**: `app/exceptions/error_codes.py` (C=Common, R=Route, T=Task; 1000=App, 2000=Internal, 3000=External, 4000=Config, 5000=Auth)
- **Pattern**: `ServerErrorModel.initialize("C1000")` then `raise ERROR.exc(**params)`
