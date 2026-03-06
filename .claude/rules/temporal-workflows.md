# Temporal Workflows (Repo Conventions)

This repo runs Temporal workflows via the Python SDK with strict determinism and a layered worker architecture.

## Source of Truth (Files)

- **Base classes**: `app/cli/temporal/core/base.py` (`Activity`, `Workflow`, `ScheduleWorkflow`, `LaunchpadCLIBaseModel`)
- **Worker registration**: `app/core/cli_settings.py` (`WorkerQueues`, `get_workers_config()`)
- **Workflow starter**: `app/cli/temporal/starter.py`
- **Workflow mapper**: `app/cli/temporal/main.py`

## Architecture

Three supervisor-managed worker processes:
- **WORKER_1_PROCESS**: All onboarding workflows (9 products + Jeeves space creation)
- **WORKER_2_PROCESS**: All deprovisioning workflows
- **WORKER_3_PROCESS**: Utility workflows (onboard orchestration, payment verification, cert expiry, webhooks, deployment)

## Per-Product Structure

Each product has its own package under `app/cli/temporal/<product>/`:
```
app/cli/temporal/veritable/
  workflows/
    onboarding.py
    deprovisioning.py
    deployment.py         # (some products have extra workflows)
```

Activities are shared across products in `app/cli/temporal/activities/`.

## Must-Follow Rules

- **No I/O in workflows**: workflows orchestrate only; any DB/network/file I/O belongs in **activities**.
- **Determinism**:
  - Never call `datetime.now()` or `random` in workflow code.
  - Avoid reading environment/config at runtime inside workflow execution.
- **Activities**:
  - Must subclass `Activity` and implement `get_timeout()`, `get_retry_policy()`, and `defn()`.
  - Input/output models must subclass `LaunchpadCLIBaseModel`.
- **Registration**: Every new workflow must be added to `app/core/cli_settings.py` in the appropriate worker process and queue.
- **Scheduled workflows**: Subclass `ScheduleWorkflow`, implement `get_schedule_spec()`. Register in `get_schedules()`.

## Supported Products

Veritable, Jeeves, Dexit, Penknife, Practifly, PricedX, ZSegment, HDP, Muspell
