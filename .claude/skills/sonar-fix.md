# SonarQube Issue Fix Patterns

Patterns for classifying and fixing SonarQube issues in Launchpad. Used by `/sonar:fix` command.

## Use This When

- Fixing SonarQube-reported bugs, code smells, and vulnerabilities
- Classifying Sonar issues for auto-fix vs. escalation

## Issue Classification

### Auto-Fixable Categories

#### SONAR_SMELL: Code Smells

| Rule | Description | Fix Strategy |
|------|-------------|-------------|
| python:S1192 | String literal duplication | Extract to module-level constant |
| python:S107 | Too many parameters | Extract parameter object (Pydantic model) |
| python:S3776 | Cognitive complexity too high | Extract helper functions, reduce nesting |
| python:S1066 | Collapsible if statements | Merge nested `if` into single `and` condition |
| python:S1135 | TODO/FIXME in code | Remove or convert to tracked issue |
| python:S125 | Commented-out code | Remove dead code entirely |
| python:S1481 | Unused local variable | Remove variable or prefix with `_` |
| python:S905 | Dead store | Remove the unused assignment |

#### SONAR_BUG: Bugs

| Rule | Description | Fix Strategy |
|------|-------------|-------------|
| python:S5727 | None comparison with `==` | Use `is None` / `is not None` |
| python:S5632 | Incorrect exception type raised | Fix to correct exception class |
| python:S930 | Wrong number of function arguments | Fix function call to match signature |
| python:S5747 | Bare `except` clause | Catch specific exception |

#### SONAR_VULN: Vulnerabilities

| Rule | Description | Fix Strategy |
|------|-------------|-------------|
| python:S4790 | Weak hash algorithm (MD5/SHA1) | Replace with `hashlib.sha256()` or stronger |
| python:S2245 | Insecure PRNG (`random`) | Use `secrets` module for security-sensitive values |
| python:S4721 | OS command injection risk | Use `subprocess` with list args, never `shell=True` |
| python:S2077 | SQL injection risk | Verify Jinja2 parameterized templates are used |
| python:S5443 | Insecure temp file creation | Use OpenDAL via `app/utils/file_operations.py` |

### Escalation Categories (User Decision Required)

#### SONAR_HOTSPOT: Security Hotspots

Present to user with file path, line number, rule description, and code context. User options: fix, accept risk, false positive, or skip.

#### SONAR_DUP: Duplications

Present duplicated blocks and locations. Suggest refactoring. User options: refactor, accept, skip.

## Fix Application Pattern

1. **Read** the affected file
2. **Get rule guidance** via `show_rule(key=rule_key)` MCP tool
3. **Understand context** — read 10-20 lines around the issue
4. **Apply minimal fix** — change only what is needed
5. **Maintain conventions** — follow `.claude/rules/coding-patterns.md`
6. **Run verification** — `ruff format . && ruff check --fix .`

## Conflict Resolution: Sonar vs Ruff

| Conflict | Resolution |
|----------|-----------|
| Sonar formatting vs `ruff format` | Run `ruff format .` after Sonar fix — ruff wins |
| Sonar naming convention vs project convention | Project convention wins (coding-patterns.md) |
| Sonar unused import vs ruff F401 | Ruff is authoritative for imports |

**Post-fix sweep**: Always run `ruff format . && ruff check --fix .` after applying Sonar fixes.

## Launchpad-Specific Patterns

### SQL Template Files
- Files in `app/sql/` may be excluded from Sonar analysis
- If Sonar flags SQL patterns in Python code, verify Jinja2 templates are used (not string concat)

### Subprocess Execution
- `app/utils/subprocess_execution.py` and various activities use `subprocess`
- Sonar may flag these — verify command injection safety before dismissing

### Async Code
- Always verify async fixes maintain `async/await` correctness (asyncpg, aiohttp)

### Error Handling
- Sonar may flag broad exception handling — fix using `ServerErrorModel` patterns
- Do NOT change error codes or error message templates while fixing Sonar issues

## Required References

| Reference | Purpose |
|-----------|---------|
| `.claude/rules/coding-patterns.md` | Conventions to maintain during fixes |
| `.claude/common-operations.md` | Verification commands |
| `sonar-project.properties` | Project key, org, exclusions |
