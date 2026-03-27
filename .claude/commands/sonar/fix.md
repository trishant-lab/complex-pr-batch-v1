# Sonar Fix: Draft PR → Analyze → Fix Issues → Clean Up

**Usage**: `/sonar:fix` (no arguments — operates on the current branch)

## Prerequisites

- Current branch is NOT `sprint` or `production`
- All local changes are committed (no uncommitted work)
- `gh` CLI is authenticated (`gh auth status`)
- SonarQube MCP server is configured (see Setup section)

## Setup (One-Time)

Add the SonarQube MCP server to Claude Code:

```bash
claude mcp add sonarqube \
  --env SONARQUBE_TOKEN=$SONAR_TOKEN \
  --env SONARQUBE_ORG=softwareartistry \
  --env SONARQUBE_TOOLSETS=analysis,issues,quality-gates,rules,measures,security-hotspots,duplications \
  -- docker run --init --pull=always -i --rm \
     -e SONARQUBE_TOKEN -e SONARQUBE_ORG -e SONARQUBE_TOOLSETS mcp/sonarqube
```

## Flow

```
Current Branch
  │
  ▼
Phase 1: Pre-flight checks
  │
  ▼
Phase 2: Create draft PR → production
  │
  ▼
Phase 3: Wait for Sonar Check GitHub Action
  │
  ▼
Phase 4: Pull issues + Quality Gate via MCP
  │
  ▼
Phase 5: Fix loop (max 3 iterations)
  │   ├── Classify issues
  │   ├── Escalate (security hotspots, duplications)
  │   ├── Auto-fix (bugs, code smells, vulnerabilities)
  │   ├── Run /verify (ruff + pre-commit)
  │   ├── Checkpoint commit
  │   ├── Push → wait for re-analysis
  │   └── Re-check Quality Gate
  │
  ▼
Phase 6: Cleanup
  ├── Quality Gate PASSED → delete draft PR
  └── Quality Gate FAILED → keep draft PR for inspection
```

## Phase 1: Pre-flight Checks

1. Verify current branch is not `sprint` or `production`
2. Verify no uncommitted changes: `git status --porcelain` (must be empty)
3. Verify `gh auth status` succeeds
4. Verify SonarQube MCP tools are available
5. Record `WORKING_BRANCH` (current branch name)

**On failure**: Report what is missing and stop.

## Phase 2: Create Draft PR

```bash
git push -u origin $WORKING_BRANCH

gh pr create --draft --base production \
  --title "sonar-fix: analysis for $WORKING_BRANCH" \
  --body "Temporary draft PR for SonarQube PR analysis. Will be deleted after Quality Gate passes."

PR_NUMBER=$(gh pr view --json number -q .number)
```

**On failure**: If a PR already exists, use `gh pr list --head=$WORKING_BRANCH --json number -q '.[0].number'`.

## Phase 3: Wait for Sonar Check

```bash
gh run list --workflow="Sonar Check" --branch=$WORKING_BRANCH --limit=1 --json databaseId,status
gh run watch $RUN_ID --exit-status
```

After the Action completes, poll the Quality Gate (30-120 seconds processing delay).

## Phase 4: Pull Issues and Quality Gate

1. **Quality Gate check** — if `OK`, skip to Phase 6.
2. **Retrieve issues** via MCP tools.
3. **Get rule details** for each unique rule.
4. **Get metrics snapshot**.

## Phase 5: Fix Loop (max 3 iterations)

### Issue Classification

| SonarQube Type | Auto-Fix? | Action |
|----------------|-----------|--------|
| CODE_SMELL | Yes | Auto-fix |
| BUG | Yes | Auto-fix |
| VULNERABILITY (LOW-HIGH) | Yes | Auto-fix |
| VULNERABILITY (BLOCKER) | Yes (with caution) | Auto-fix |
| SECURITY_HOTSPOT | **No** | Escalate to user |
| DUPLICATION | **No** | Escalate to user |

### Per-Iteration Flow

1. **CLASSIFY** — Group issues by type and severity.
2. **ESCALATE** — For hotspots/duplications, present to user and ask: fix, accept risk, false positive, or skip.
3. **AUTO-FIX** — Priority: CODE_SMELL → BUG → VULNERABILITY. Follow `.claude/rules/coding-patterns.md`.
4. **LOCAL VERIFY** — Run `/verify` (ruff + pre-commit checks).
5. **CHECKPOINT** — `git add <files> && git commit -m "fix(sonar): iter-N fix <count> issues"`.
6. **PUSH + RE-ANALYZE** — Push and wait for Sonar re-analysis.
7. **RE-CHECK** — If Quality Gate OK → Phase 6. If N < 3 → next iteration.

### Conflict Avoidance: Sonar vs Ruff

1. Apply Sonar fix first
2. Run `ruff format . && ruff check --fix .` immediately after
3. If ruff undoes a Sonar fix, ruff takes precedence

## Phase 6: Cleanup and Report

**Success**: `gh pr close $PR_NUMBER --delete-branch=false`
**Failure**: Keep draft PR open for manual inspection.

### Report Template

```markdown
## Sonar Fix Report

| Metric | Value |
|--------|-------|
| Branch | $WORKING_BRANCH |
| Draft PR | #$PR_NUMBER |
| Quality Gate | PASSED / FAILED |
| Iterations | N / 3 |
| Issues found | X |
| Issues auto-fixed | Y |
| Issues escalated | Z |
| Issues remaining | R |

### Fixed Issues
- [file:line] rule_key — description (iteration N)

### Escalated Issues
- [file:line] rule_key — description → user decision

### Remaining Issues (if any)
- [file:line] rule_key — description
```

## Stop Conditions

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Quality Gate passes | Any iteration | Delete draft PR, report success |
| Max iterations | 3 | Keep draft PR, report remaining issues |
| Same issue unfixable 2x | Per issue | Skip that issue, note in report |
| Security hotspot | Any | Pause for user input |
| Duplication detected | Any | Pause for user input |
| GH Action failure | Non-Sonar failure | Stop, keep PR, report failure |

## Rules

- **Always commit before creating draft PR** — no uncommitted changes
- **Never force-push** — use normal `git push`
- **Run `/verify`** after every fix iteration
- **Checkpoint per iteration** — commit after each fix batch
- **Ruff wins conflicts** — when Sonar and ruff disagree, follow ruff
- **Escalate, don't guess** — security hotspots and duplications require user judgment
- **Clean up draft PRs** — delete on success, keep on failure
