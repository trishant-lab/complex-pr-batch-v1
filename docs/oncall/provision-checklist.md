# Tenant provision checklist

complex-pr batch note — oncall runbook fragment.

## Pre-checks
- Confirm product settings via `describe_for_oncall()`
- Refuse empty required fields (`require_field`)
- Correlation id present on the Temporal workflow

## During incident
1. Capture redacted settings block for Slack
2. Classify failure (`timeout` / `auth` / `not_found` / hardening code)
3. Re-run with the same correlation id — do not invent a parallel resource name

## After
- Update provision checklist
- File follow-up if a template/path fell through a silent fallback

## Related
- Temporal hardening package: `app/cli/temporal/hardening`
- Core oncall util: `app/core/oncall_util`
