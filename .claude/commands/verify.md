Run backend verification before committing or creating PRs.

## Modes

- `/verify` — Quick: ruff format, ruff check, pre_commit_checks
- `/verify full` — Full: same as quick + osv-scanner + bandit

## Commands

```bash
# Quick (default)
ruff format --check . && ruff check . && uv run python app/pre_commit_checks.py

# Full
ruff format --check . && ruff check . && uv run python app/pre_commit_checks.py && osv-scanner --lockfile=uv.lock --config=osv-scanner.config.toml && bandit -r app/ -ll
```

## Failure Recovery

- **Format failures**: `ruff format .` to auto-fix.
- **Lint failures**: `ruff check --fix .` for auto-fixable, manual fix for the rest.
- **Pre-commit sync**: Run `uv run python app/pre_commit_checks.py` and fix reported files (OpenAPI spec, worker config).
- **OSV vulnerabilities**: Update the package in `pyproject.toml`, run `uv lock --upgrade-package <pkg>`. See `.claude/rules/coding-patterns.md` for the full process.
- **Bandit findings**: Review and fix security issues. Skip false positives with `# nosec` only when justified.

## Verdict Template

```
| Check           | Status        |
|-----------------|---------------|
| Format (ruff)   | PASS / FAIL   |
| Lint (ruff)     | PASS / FAIL   |
| Pre-commit sync | PASS / FAIL   |
| OSV scanner     | PASS / FAIL   |  (full mode only)
| Bandit          | PASS / FAIL   |  (full mode only)

Ready for PR: YES / NO
```
