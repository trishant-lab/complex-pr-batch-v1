---
name: checklist-temporal
description: Temporal workflow and activity standards. Loaded during review and implementation.
---

- No I/O in workflow code — only in activities
- No `datetime.now()`, `random`, `uuid4()` in workflows — use `workflow.now()`
- No environment/config reads at workflow runtime
- Activities implement `get_timeout()` and `get_retry_policy()`
- Activities called via `run_activity()` helper
- Models extend `LaunchpadCLIBaseModel`
- Registered in `app/core/cli_settings.py` (correct worker process and queue)
- Per-product workflows in `app/cli/temporal/<product>/workflows/`
