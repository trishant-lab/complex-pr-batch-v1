# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Launchpad is a multi-tenant onboarding and provisioning microservice used by multiple 314e products (Veritable, Jeeves, Dexit, Penknife, Practifly, PricedX, ZSegment, HDP, Muspell). It handles self-signup flows, tenant creation, billing integration (Stripe, Lago), and orchestrates complex provisioning workflows via Temporal (Kubernetes resources, databases, DNS, cloud storage, Keycloak realms). Built with FastAPI, AsyncPG, Jinja2 SQL templating, and Temporal workflows.

## Commands

See `.claude/common-operations.md` for the full command reference. Key commands:

```bash
uv sync --frozen                      # Install dependencies
ruff format . && ruff check .         # Format + lint
uv run pytest --cov=./app test/ -s -v -W ignore::DeprecationWarning:opentelemetry.instrumentation.dependencies --cov-report term-missing
uv run python app/pre_commit_checks.py  # Validate OpenAPI spec + worker config sync
dbmate new {name}                     # Create migration in db/migrations/
```

Pre-commit hooks: `uv-sort`, `ruff-format`, `ruff`, `bandit`, `osv-scanner`, `gitleaks`, `pre_commit_checks.py`. When `osv-scanner` blocks: see `.claude/rules/coding-patterns.md`.

## Architecture

### Dependency Flow
```
app/core/ -> app/models/ -> app/routes/ | app/cli/ | app/utils/
```
**`app/core/` must not import from other app directories.** Models are purely functional -- no database queries in model files.

### Key Layers

- **API Server**: `app/main.py` (`fastapi_app`), prefix `/api/v1/`
- **Routes**: `app/routes/` (provisioning, tenant, users, email templates, deployment, webhooks) + `app/routes/self_signup/` (signup, plans, add-ons, subscriptions, OTP, session)
- **Temporal Workers**: `app/cli/temporal/` — 3 supervisor-managed processes, per-product workflow packages, 60+ activities. Base classes in `core/base.py`.
- **Database**: AsyncPG + Jinja2 SQL templates in `app/sql/` (no ORM). `DBManager` in `app/core/db.py`.
- **Config**: JSON via `APP_CONFIG_DIR` + OpenDAL. Product configs in `app/core/product_settings/`.
- **Auth**: Keycloak OAuth2 + PyCasbin RBAC (`app/core/pycasbin/`)
- **Products**: `ProductEnum` in `app/models/product.py` (8 products, each with workflow package + config + templates)

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
