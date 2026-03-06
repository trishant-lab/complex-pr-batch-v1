# Review Feature Changes

**Usage**: `/feature:review [scope]`

Review code changes before committing — check correctness, patterns, security, and completeness against the Linear ticket.

Argument: file paths, explicit base branch, or "all". Optionally include extra context.

Examples:
- `/feature:review all`
- `/feature:review against production`
- `/feature:review app/cli/temporal/activities/`

## Steps

### 1. Determine Review Scope

**Do NOT start the review until the base branch is confirmed.**

1. **Check for an active PR** from the current branch: `gh pr list --head <current-branch> --json baseRefName,url --limit 1`.
   - If a PR exists: use its base branch as the diff target. Show the PR URL for context.
2. **If no PR exists and no explicit branch in the argument**: ask the user which branch to diff against.
3. **If an explicit branch is in the argument** (e.g. "against production"): use that branch.

Once the base branch is known:
- `git diff <base>...HEAD` for committed changes.
- `git diff` and `git diff --cached` for unstaged/staged WIP changes.

**Infer the Linear ticket**: from the branch name (e.g. `feat/VER-670` → `VER-670`), the PR description, or the user's argument. If found, fetch it via Linear MCP tools and extract acceptance criteria.

### 2. Correctness Review

**Logic & Async**
- Verify all async functions are properly `await`ed.
- Check for race conditions in concurrent operations.
- Check error handling — specific exceptions caught, not bare `except`.

**Data Flow**
- Verify request validation via Pydantic models (not manual checks).
- Check SQL templates use parameterized binding (`{{ var }}`), not string concatenation.
- Verify `| sqlsafe` is only used for trusted/computed values, never user input.

**Temporal Workflows**
- No I/O in workflow code (only in activities).
- Activities have `get_timeout()` and `get_retry_policy()`.
- Models extend `LaunchpadCLIBaseModel`.
- Workflows registered in `app/core/cli_settings.py`.

### 3. Pattern Compliance

**Routes** (`app/routes/`)
- [ ] Uses `get_db_manager()` for DB access
- [ ] Error handling uses `ServerErrorModel.initialize()` codes
- [ ] Policy.csv entry exists for new routes

**Workflows** (`app/cli/temporal/`)
- [ ] Extends `Workflow`, `ScheduleWorkflow`, or `Activity` base class
- [ ] Activities have `get_timeout()` and `get_retry_policy()`
- [ ] No I/O in workflow code
- [ ] Registered in `app/core/cli_settings.py`

**Models** (`app/models/`)
- [ ] Pydantic V2 syntax (`@field_validator`, `model_config`)
- [ ] `X | None` not `Optional[X]`

**Templates** (`app/cli/temporal/<product>/templates/`)
- [ ] JSON templates are valid JSON
- [ ] Template variables use proper Jinja2 syntax

### 4. Security Check

- [ ] No hardcoded secrets, API keys, or tokens
- [ ] No SQL injection vectors (`| sqlsafe` on user input)
- [ ] No `eval()`, `exec()`, `subprocess(shell=True)` without justification
- [ ] No PII in log statements
- [ ] File operations use OpenDAL (not `open()`/`pathlib`/`tempfile`)

### 5. Completeness Check

**Ticket-driven (if a Linear ticket was found):**
- Map each acceptance criterion from the ticket to specific code changes in the diff.
- Flag criteria with no matching code as CRITICAL if required, or NOTE if optional/stretch.
- Distinguish between "missing — not yet done" vs "missing — likely forgotten".

**Artifact checklist (for new/changed code):**

New routes require:
- [ ] Pydantic request/response models
- [ ] SQL templates in `app/sql/`
- [ ] Error codes in `app/exceptions/error_codes.py`
- [ ] `policy.csv` entry

New workflows require:
- [ ] Workflow registered in `app/core/cli_settings.py`
- [ ] Activity with timeout and retry policy
- [ ] Input/output models extending `LaunchpadCLIBaseModel`

New products require:
- [ ] Product added to `ProductEnum` in `app/models/product.py`
- [ ] Product settings in `app/core/product_settings/`
- [ ] Workflow package under `app/cli/temporal/<product>/`
- [ ] Templates directory with keycloak realm, env config, etc.

### 6. Report

```
## Code Review: <scope>

### Status: APPROVE | REQUEST_CHANGES | NEEDS_DISCUSSION

### Findings

CRITICAL (must fix):
- <file>:<line> - <issue> -> <fix>

WARNING (should fix):
- <file>:<line> - <issue> -> <fix>

SUGGESTION (nice to have):
- <file>:<line> - <suggestion>

### Ticket Coverage (if Linear ticket found)

| Requirement | Status | Code |
|---|---|---|
| <acceptance criterion> | MET / MISSING / WIP | <file(s) or "missing"> |

### Summary
<1-2 sentence summary of review>
```

## Rules

- Be constructive — pair every issue with a concrete fix.
- Focus on correctness and security, not style (ruff handles formatting).
- Flag missing artifacts (policy.csv, worker registration) as CRITICAL.
- Check the dependency flow: `app/core/` must not import from `app/routes/` or `app/cli/`.
