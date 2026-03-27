---
name: function-naming
description: Naming conventions for all Launchpad code artifacts — routes, models, SQL, workflows, activities, and products.
---

## Use This When

- Naming new route handlers or API paths
- Naming Pydantic models, SQL files, or error codes
- Naming Temporal workflows, activities, or worker queues
- Adding new products to the system

## Naming Tables

### Route Handlers

| Artifact | Convention | Example |
|----------|-----------|---------|
| Handler function | `snake_case`: `verb_domain` | `provision_tenant`, `get_plans` |
| Router prefix | lowercase | `/provisioning`, `/tenant`, `/plans` |
| Path params | `{product}`, `{tenant_id}` | `/provisioning/{product}` |

### Pydantic Models

| Artifact | Convention | Example |
|----------|-----------|---------|
| Request model | `DomainRequest` | `ProvisioningRequest`, `SignupRequest` |
| Response model | `DomainResponse` | `TenantResponse`, `PlanResponse` |
| Enum | `DomainEnum` / descriptive | `ProductEnum`, `BillingPeriod` |

### SQL Files

| Artifact | Convention | Example |
|----------|-----------|---------|
| File name | `verb_noun.sql` (snake_case) | `get_tenant.sql`, `create_space.sql` |
| By identifier | `get_noun_by_field.sql` | `get_tenant_by_name.sql` |
| Product-specific | `product/verb_noun.sql` | `penknife/get_config.sql` |
| Column names | `"camelCase"` (quoted) | `"tenantname"`, `"createdAt"`, `"approvedBy"` |

### Temporal

| Artifact | Convention | Example |
|----------|-----------|---------|
| Workflow class | `ProductActionWorkflow` | `VeritableOnboardingWorkflow`, `DexitDeProvisioningWorkflow` |
| Activity class | descriptive name | `PostgresSetup`, `KeycloakSetup`, `CloudflareSetup` |
| Activity file | `snake_case.py` | `postgres_setup.py`, `keycloak_setup.py` |
| Task queue | `product_action` | `veritable_onboarding`, `dexit_deboarding` |
| Workflow package | `app/cli/temporal/<product>/` | `app/cli/temporal/veritable/` |

### Error Codes

| Artifact | Convention | Example |
|----------|-----------|---------|
| Common error | `C<NNNN>` | `C1000` (app), `C2001` (DB), `C3001` (external), `C5001` (auth) |
| Route error | `R<NNNN>` | `R1001` (customer not found), `R1010` (tenant conflict) |
| Task error | `T<NNNN>` | Task/workflow errors |
| Error constant | `ServerErrorModel.initialize("CODE")` | `ServerErrorModel.initialize("R1002")` |

### Products

| Artifact | Convention | Example |
|----------|-----------|---------|
| Enum value | lowercase | `veritable`, `jeeves`, `dexit` |
| Settings class | `ProductSettings` (PascalCase) | `VeritableSettings`, `DexitSettings` |
| Settings file | `app/core/product_settings/<product>.py` | `veritable.py`, `dexit.py` |
| Worker queue | `product_onboarding` / `product_deboarding` | `veritable_onboarding` |
| Template dir | `app/cli/temporal/<product>/templates/` | `veritable/templates/` |

## Casing Rules Summary

| Context | Convention |
|---------|-----------|
| Python functions, variables | `snake_case` |
| Python classes | `PascalCase` |
| DB column names | `"camelCase"` (quoted in SQL) |
| API path segments | `camelCase` or lowercase |
| Error codes | `UPPERCASE` prefix + number |
| Worker queues | `snake_case` |
| SQL file names | `snake_case.sql` |

## Required References

| Reference | Purpose |
|-----------|---------|
| `.claude/rules/coding-patterns.md` | Implementation order, forbidden patterns |
