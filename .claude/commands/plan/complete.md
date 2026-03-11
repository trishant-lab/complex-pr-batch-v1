# Complete Feature

Full automated pipeline for greenfield features. Composes `/plan:plan` → `/impl:implement` → verify → review.

**Usage**: `/plan:complete <PRD-text-or-file>`

For small changes, use `/impl:implement` directly.

## Flow

| Phase | What | Gate |
|-------|------|------|
| 1 | `/plan:plan` — TRD | User approval |
| 2 | `critiq` — question the approach | OK / RETHINK / STOP |
| 3 | `/impl:implement` — build in dependency order | Layer dependencies |
| 4 | Test tiers (format → lint → pre-commit → pytest → security) | Stop on first failure |
| 5 | `/feature:review` — checklist-based code review | APPROVE verdict |
| 6 | Summary | — |

### Phase 2 Loop

- **critiq → OK**: proceed to impl
- **critiq → OK with caveats**: proceed, document caveats as known trade-offs
- **critiq → RETHINK**: revise TRD (back to Phase 1), re-run critiq
- **critiq → STOP**: escalate to user

This loop MUST close before Phase 3. No code gets written on a flawed approach.

## Agent Ownership

| Agent | Can | Cannot |
|-------|-----|--------|
| `critiq` | Read, search, question approach | Write/edit code |
| `builder` | Read, search, write, edit code | Run tests, produce reviews |
| `test-runner` | Read, search, run commands | Write/edit code |
| `code-reviewer` | Read, search | Write/edit code, run verification |

## Stop Conditions

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Max iterations | 10 across fix cycles | Stop, summarize, escalate |
| Repeated failure | Same error 3x | Escalate with alternatives |
| TRD revisions | 3 revisions | Require explicit approval |
