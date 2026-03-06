# Build Feature from Linear Ticket

**Usage**: `/feature:build <TICKET-ID>` or `/feature:build <TICKET-ID> <additional-context>`

Examples:
- `/feature:build VER-622`
- `/feature:build VER-670 only the provisioning workflow, skip billing`

## Steps

### 1. Fetch Linear Ticket

Use the Linear MCP tools to fetch the ticket:
- `get_issue` with the ticket ID (e.g. `VER-622`)
- Extract: title, description, acceptance criteria, priority, assignee, labels
- If the ticket has sub-issues, fetch those too

Present a summary:
```
Ticket: VER-622 — <title>
Priority: <priority>
Labels: <labels>

Acceptance Criteria:
1. <criterion>
2. <criterion>
...
```

### 2. Codebase Analysis

Scan the codebase to understand the scope of changes needed:
- Which products are affected? (check `app/cli/temporal/<product>/`)
- Are new routes needed? (check `app/routes/`)
- Are new Temporal activities needed? (check `app/cli/temporal/activities/`)
- Are new SQL templates needed? (check `app/sql/`)
- Are config/template changes needed? (check product template directories)
- Are new models needed? (check `app/models/`)

### 3. Implementation Plan

Write a plan to a file: `docs/plans/<TICKET-ID>-plan.md`

The plan must include:
- **Summary**: What this ticket requires
- **Affected products**: Which products are impacted
- **Files to create/modify**: Grouped by layer
- **Implementation order**: Following the dependency flow from `.claude/rules/coding-patterns.md`
- **Acceptance criteria mapping**: Each criterion → specific code change
- **Risks/questions**: Anything unclear from the ticket

**HARD GATE**: Do not write any code until the user explicitly approves the plan.

### 4. Implementation

Follow the dependency flow:
```
1. Models           → app/models/
2. SQL templates    → app/sql/
3. Error codes      → app/exceptions/
4. Activities       → app/cli/temporal/activities/
5. Workflows        → app/cli/temporal/<product>/workflows/
6. Worker config    → app/core/cli_settings.py (if new queues/workflows)
7. Routes           → app/routes/
8. Policy/auth      → app/core/pycasbin/policy.csv (if new routes)
9. Templates/config → app/cli/temporal/<product>/templates/
```

After each layer, checkpoint:
```bash
git add <specific-files>
git commit -m "<type>: <TICKET-ID> <summary>"
```

### 5. Verification

Run pre-commit checks:
```bash
uv run python app/pre_commit_checks.py
ruff format .
ruff check .
```

### 6. Summary

```
Ticket: <TICKET-ID> — <title>
Files created: <count>
Files modified: <count>
Acceptance criteria met: <N>/<total>

Remaining:
- <any criteria not yet addressed>

Next: create branch, push, and create two PRs (production + sprint)
```

## Rules

- **Always fetch the ticket first** — never guess requirements
- **Never skip the plan** — even small features get a brief plan
- **Never skip the approval gate** — no code before user approves
- **Follow git workflow** — branch from production, dual PRs
- **Reference ticket in commits** — `feat: VER-622 <summary>`
- **Ask when unclear** — if acceptance criteria are ambiguous, ask before implementing
