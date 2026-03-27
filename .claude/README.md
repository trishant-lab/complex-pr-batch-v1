# Claude Code Configuration — Launchpad

## Structure

```
.claude/
├── agents/              # code-reviewer, test-runner, builder, critiq, database-reviewer
├── commands/
│   ├── plan/            # /plan:plan, /plan:complete
│   ├── impl/            # /impl:implement
│   ├── feature/         # /feature:build, /feature:review
│   ├── sonar/           # /sonar:fix
│   ├── security/        # /security:audit
│   └── refactoring/     # /refactoring:renaming
│   └── verify.md        # /verify
├── rules/               # Always-loaded invariants (4 files)
├── skills/
│   ├── checklists/      # 6 review dimensions (loaded on-demand)
│   ├── impl/            # How-to guides for writing code
│   └── *.md             # Top-level skills (sonar-fix, function-naming, jinja2-sql, temporal)
├── templates/           # TRD template
├── common-operations.md
└── settings.json
```

## Commands

| Command | Description |
|---------|-------------|
| `/plan:plan` | Create a TRD for a feature or change |
| `/plan:complete` | Full pipeline: plan → implement → test → review |
| `/impl:implement` | Make a change following standards + checklists |
| `/feature:build` | Build a feature from a Linear ticket |
| `/feature:review` | Code review (loads checklists by file type) |
| `/verify` | Format, lint, pre-commit sync checks |
| `/sonar:fix` | Fix SonarQube issues |
| `/security:audit` | Security audit |
| `/refactoring:renaming` | Rename a symbol across the codebase |

## Rules (always loaded)

| Rule | Purpose |
|------|---------|
| `coding-patterns.md` | Dependency flow, forbidden patterns, error handling, OSV resolution |
| `git-workflow.md` | Branch strategy, merge rules, dual PRs |
| `sql-templating.md` | Jinja2 SQL conventions, sqlsafe restrictions |
| `temporal-workflows.md` | Determinism rules, worker architecture, per-product structure |

## Checklists (loaded on-demand)

| Checklist | Applies To |
|-----------|-----------|
| `security` | APIs, SQL |
| `api-contract` | APIs, models |
| `business-logic` | APIs, Activities |
| `data-integrity` | APIs, Activities |
| `schema` | Migrations, SQL |
| `temporal` | Workflows, Activities |

## Hooks

- **git commit**: pre-commit hooks run on staged files (uv-sort, ruff-format, ruff, bandit, osv-scanner, gitleaks, pre_commit_checks)
