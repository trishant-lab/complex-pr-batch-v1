---
name: temporal
description: Checklist for creating Temporal workflows, activities, and schedule workflows in Launchpad. Use as a subtask skill during feature implementation.
---

## Use This When

- Creating new Temporal workflows for product onboarding/deprovisioning
- Creating activities for provisioning steps (K8s, DB, Keycloak, CloudFlare, etc.)
- Registering workflows/activities in `app/core/cli_settings.py`
- Creating scheduled workflows (cron-style)

## Workflow Checklist

1. **Create input model** extending `LaunchpadCLIBaseModel` (`app/cli/temporal/core/base.py`):
   - Place in `app/cli/models/<product>.py` for product-specific models.
   - Use for workflow input data (tenant details, provisioning config).

2. **Create activity class** extending `Activity` base:
   - Place in `app/cli/temporal/activities/<activity_name>.py`.
   - Implement `get_timeout()` — return `timedelta` for activity timeout.
   - Implement `get_retry_policy()` — return `RetryPolicy` for retry behavior.
   - Implement `defn()` — the actual activity logic (all I/O goes here).

3. **Create workflow class** extending `Workflow` or `ScheduleWorkflow`:
   - Place in `app/cli/temporal/<product>/workflows/onboarding.py` (or `deprovisioning.py`).
   - Implement `get_activities()` — list of activity classes used.
   - Implement `get_workflow_id()` — unique ID from input (e.g. tenant name + product).
   - Implement `run()` — orchestrate activities. **No I/O in workflows.**
   - Use `workflow.now()` instead of `datetime.now()`.

4. **Register** in `app/core/cli_settings.py`:
   - Add `WorkerQueues` entry if new queue needed.
   - Add workflow to appropriate worker process (WORKER_1 = onboarding, WORKER_2 = deprovisioning, WORKER_3 = utilities).
   - Import workflow class in `get_workers_config()`.

5. **Run sync check**: `uv run python app/pre_commit_checks.py` to verify worker config.

## Per-Product Structure

```
app/cli/temporal/<product>/
├── workflows/
│   ├── onboarding.py           # Product onboarding workflow
│   ├── deprovisioning.py       # Product deprovisioning workflow
│   └── deployment.py           # Optional: deployment workflow
├── templates/                  # Product-specific config templates
│   ├── keycloak_realm.json
│   ├── istio-rules.json
│   ├── integration-env-config.tmpl.json
│   └── production-env-config.tmpl.json
└── models/                     # Optional: product-specific models
```

## Worker Architecture

| Worker | Queues | Purpose |
|--------|--------|---------|
| WORKER_1_PROCESS | `*_onboarding`, `jeeves_space_creation` | All onboarding workflows (count: 3) |
| WORKER_2_PROCESS | `*_deboarding` | All deprovisioning workflows (count: 1) |
| WORKER_3_PROCESS | `onboard`, `kube_config_cert_expiry`, `verify_payment`, `veritable_deployment`, `webhooks` | Utility workflows (count: 1) |

## Common Activity Types

| Activity | File | Purpose |
|----------|------|---------|
| `postgres_setup.py` | DB creation, schema, user, grants |
| `keycloak_setup.py` | Realm creation, client config, user setup |
| `cloudflare_setup.py` | DNS records, R2 buckets, worker KV |
| `deployment_pod_creation.py` | K8s deployments, services, config maps |
| `one_password.py` | Credential management via 1Password |
| `minio_setup.py` | MinIO bucket creation, policies |

## Determinism Rules (Critical)

- **No** `datetime.now()`, `random`, `uuid4()` in workflow code.
- **No** environment/config reads at workflow runtime.
- **No** direct I/O (DB, HTTP, file) in workflow code.
- **Use** `workflow.now()` for current time.
- **Use** activities for all side effects.

## Supported Products

Veritable, Jeeves, Dexit, Penknife, Practifly, PricedX, ZSegment, HDP, Muspell

## Required References

| Reference | Purpose |
|-----------|---------|
| `.claude/rules/temporal-workflows.md` | Must-follow determinism rules |
| `.claude/rules/coding-patterns.md` | Implementation patterns |
| `.claude/common-operations.md` | Pre-commit check commands |
