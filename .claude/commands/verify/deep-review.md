# Parallel Review Pipeline

**Usage**: `/verify:deep-review [against <base-branch>] [fix]`

Launches review agents in parallel — each with a different perspective — then consolidates into one deduplicated, prioritized report. Always runs `code-reviewer` + `critiq`; adds `database-reviewer` **only when the diff touches a PostgreSQL surface** (implicit triggering — never run a reviewer with nothing to review).

## 1. Determine Scope

**Do NOT start until the base branch is confirmed.**

1. Check for active PR: `gh pr list --head <current-branch> --json baseRefName,url --limit 1`
2. If no PR and no explicit branch: ask the user.
3. Get changed files: `git diff <base>...HEAD --name-only`
4. Infer Linear ticket from branch name (e.g. `feat/VER-622` → `VER-622`) → fetch with `mcp__linear__get_issue` if found.
5. **Decide which reviewers are relevant (implicit triggering):**
   - `code-reviewer` and `critiq` → always run.
   - `database-reviewer` → run **only if** a changed path touches a PostgreSQL surface. Trigger if any changed path matches:
     - `db/migrations/` or `app/sql/` (Jinja SQL templates), **or**
     - `app/core/db.py` (`DBManager`), **or**
     - a changed `.py` that calls `db.fetch_all|fetch_one|fetch_val|execute` or handles a billing/money value (Stripe/Lago amounts).
   - If nothing matches, **skip it and say so** in the report (`database-reviewer: not triggered — no PG surface in diff`). Never spawn it to produce an empty review.

## 2. Spawn Agents in Parallel (2 or 3)

Use the Agent tool to launch the relevant agents simultaneously, in a single message. Pass each the base branch and changed file list.

### Agent 1 — Code Reviewer

**Agent type**: `code-reviewer`

**Perspective**: Line-level correctness. Reviews the actual code for concrete issues — security vulnerabilities (secret leaks, SQL injection via `| sqlsafe` on user input, missing auth/RBAC), test coverage gaps (missing tests, stale assertions, untested error paths), architecture violations (dependency-flow breaks — `app/core/` importing from `routes`/`cli`/`utils`; DB queries in `app/models/`; I/O in Temporal workflow code), and integration hygiene (conflict markers, stray files, missing artifacts: `policy.csv` for new routes, `operationid.json`, worker registration in `app/core/cli_settings.py`).

### Agent 2 — Critiq

**Agent type**: `critiq`

**Perspective**: Design and approach. Challenges whether this is the right pattern, whether it scales across the 9 products, and what breaks in production. Questions the testing strategy — are we testing the right things, will these tests catch real regressions? Evaluates operational risks (Temporal determinism, provisioning idempotency, multi-tenant blast radius) and whether the change is sustainable long-term.

### Agent 3 — Database Reviewer *(only if triggered in step 1.5)*

**Agent type**: `database-reviewer`

**Perspective**: PostgreSQL change discipline — migration safety (both `-- migrate:up`/`-- migrate:down`, UUID v7 PKs, TIMESTAMPTZ, expand-contract for drops/renames), SQL template security (`{{ var }}` binding vs `| sqlsafe` on user input), query performance (missing FK indexes, `SELECT *`, OFFSET-on-large-table, N+1 loops), and money correctness for billing paths. Default-to-flag; verifies from the repo or marks `UNVERIFIED`. Its `BLOCK`/`UNVERIFIED` items are merge-blocking.

## 3. Consolidate

1. Merge all findings from every agent that ran
2. Deduplicate — same file:line → keep higher severity, combine context
3. Sort: CRITICAL → HIGH → MEDIUM
4. Tag source: `[CODE]` (code-reviewer), `[DESIGN]` (critiq), `[PG]` (database-reviewer)
5. Number each finding

## 4. Report

```
## Deep Review: <branch> against <base>

### Findings (deduplicated)

CRITICAL:
1. [TAG] file:line — issue → fix

HIGH:
2. [TAG] file:line — issue → fix

MEDIUM:
3. [TAG] file:line — suggestion

### Ticket Coverage (if Linear ticket found)
| Requirement | Status | Code |

### Completeness
- [x] / [ ] artifact checklist (policy.csv, operationid.json, cli_settings.py, tests)

### Reviewers run
- code-reviewer ✓ · critiq ✓ · database-reviewer <✓ | not triggered — no PG surface>

### Verdict: APPROVE | REQUEST_CHANGES | NEEDS_DISCUSSION
```

**Merge-gate rule:** the verdict is `REQUEST_CHANGES` if *any* agent requests changes — and specifically if `database-reviewer` returned any `BLOCK` or `UNVERIFIED` item (an unresolved `UNVERIFIED` blocks; it does not pass). `APPROVE` requires every triggered reviewer to pass.

## 5. Apply Fixes (if "fix" argument provided)

Show report → wait for confirmation → apply CRITICAL then HIGH → run `/verify` → report.

## Rules

- All agents review the full diff — don't restrict them to a subset of concerns
- Pair every issue with a concrete fix
- Don't flag ruff/formatting — pre-commit handles that
- Fundamental approach problem → recommend `/critiq` before continuing
