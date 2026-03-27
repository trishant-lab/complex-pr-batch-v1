---
name: checklist-security
description: Security standards for APIs and SQL. Loaded during review and implementation.
---

- SQL binding: `{{ var }}` always. `| sqlsafe` only for trusted computed values (LIMIT, OFFSET, column names)
- Auth: every route has a `policy.csv` entry
- No PII in log statements
- No hardcoded secrets, API keys, or tokens
- No `eval()`, `exec()`, `subprocess(shell=True)` without justification
- File operations via OpenDAL (`app/utils/file_operations.py`), not `open()`/`pathlib`/`tempfile`
- No bare `except` — catch specific exceptions
- Subprocess execution in activities: verify command injection safety
