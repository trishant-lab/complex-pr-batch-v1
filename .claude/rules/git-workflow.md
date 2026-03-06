# Git Workflow

## Branches

### Main branches (persistent, protected)

| Branch | Purpose |
|--------|---------|
| `sprint` | Current sprint work, deployed to test environments |
| `production` | Live production |

Both branches must be kept **in sync**. There is no staging branch.

### Work branches (ephemeral)

All work branches are created **from `production`**, not from `sprint`.

### Branch naming

| Prefix | Use |
|--------|-----|
| `feat/` | New feature |
| `impr/` | Improvement -- refactor, tests, docs, perf |
| `fix/` | Bug fix |
| `hotfix/` | Urgent fix against production |
| `chore/` | CI, deps, tooling, housekeeping |
| `task/` | Non-code tasks, ops work |

When a Linear ticket exists, include the ticket ID: `<prefix>/<TICKET-ID>` or `<prefix>/<TICKET-ID>-<short-desc>`.
When no ticket exists, use a short description: `<prefix>/<short-desc>`.

Examples: `feat/VER-622`, `fix/VER-630-supavisor-deletion`, `chore/update-deps`, `impr/dicom-server`

## Flow

### Standard change
```
production -> work-branch -> PR to production (merge commit)
                          -> PR to sprint (merge commit)
```

Every work branch gets **two PRs**:
1. One targeting `production`
2. One targeting `sprint`

Both PRs use **merge commit** (no squash). This keeps SHAs identical across both branches.

### Hotfix (direct to production)
```
production -> hotfix/* -> PR to production (merge commit)
                       -> PR to sprint (merge commit)
```

Same as standard -- hotfixes also go to both branches.

## Merge Strategy

| Scenario | Strategy |
|----------|----------|
| Work branch -> production | **Merge commit** (no squash) |
| Work branch -> sprint | **Merge commit** (no squash) |

**Never squash merge.** Squash creates new SHAs, causing sprint and production to diverge.

## Linear Integration

Launchpad serves multiple products, so tickets may come from different Linear teams (VER, JEV, DEX, etc.).

### Branch → Ticket inference
- Extract ticket ID from branch name: `feat/VER-622` → `VER-622`.
- Use the Linear MCP tools (`get_issue`) to fetch ticket details when available.

### Commit messages
- Reference the Linear ticket ID in commit messages when applicable: `feat: VER-622 add volcano scheduler`.
- For chores/deps without a ticket, a descriptive message is sufficient.

### PR descriptions
- Include the Linear ticket ID and link in the PR description when a ticket exists.
- Map acceptance criteria from the Linear ticket to the changes in the PR.

### Review
- When reviewing code (`/feature:review`), infer the Linear ticket from the branch name or PR description.
- Check acceptance criteria from the ticket against the diff to assess completeness.

## Rules for Claude

- **Never commit directly** to `sprint` or `production`.
- **Always create work branches from `production`** -- never from `sprint`.
- When creating a PR, always create **two PRs** (one to production, one to sprint) unless explicitly told otherwise.
- When resolving merge conflicts between main branches, check `git log` on both branches to identify **intentional removals** -- never re-add code that was deliberately deleted.
- Verify the current branch with `git branch --show-current` before any commit.
- Never use `git add -A` or `git add .` -- stage specific files by name.
