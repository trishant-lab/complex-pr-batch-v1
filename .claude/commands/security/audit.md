Perform a security audit of the Launchpad codebase covering common vulnerability categories.

## Steps

### 1. Dependency Vulnerabilities
- Run `osv-scanner --lockfile=uv.lock --config=osv-scanner.config.toml` to check for known vulnerabilities.
- List critical and high severity vulnerabilities.
- For each, determine if the vulnerable code path is actually reachable in this project.
- Recommend specific version upgrades or patches.

### 2. Secrets Scan
- Run `gitleaks detect --source .` to scan for hardcoded secrets.
- Search for hardcoded secrets, API keys, tokens, and passwords:
  - Patterns: `password\s*=`, `api[_-]?key`, `secret`, `token`, `Bearer `, base64-encoded strings.
  - Files: `.env` files committed to git, config files, source code.
- Check `.gitignore` for proper exclusion of sensitive files (`.env`, `*.pem`, `*.key`, `*-config.json`).
- Verify environment variables and `APP_CONFIG_DIR` config files are used for all secrets.

### 3. Static Analysis (bandit)
- Run `bandit -r app/ -ll` to scan for Python security issues.
- Review findings for:
  - Hardcoded passwords or secrets
  - Use of `eval()`, `exec()`, `subprocess` with shell=True
  - Insecure hash functions (MD5, SHA1 for security)
  - SQL injection risks (string formatting in queries)
  - Insecure temp file usage

### 4. OWASP Top 10 Check
- **Injection**: Check Jinja2 SQL templates in `app/sql/` for unsafe `| sqlsafe` usage on user input. Verify all user inputs use parameterized binding (`{{ var }}`).
- **Broken Auth**: Review Keycloak integration in `app/core/oauth2.py`, session handling in `app/route_utils/user_session.py`.
- **Sensitive Data Exposure**: Check for PII in logs (loguru config in `app/core/log.py`), unmasked data in error responses (`ServerErrorModel`).
- **Broken Access Control**: Verify all routes have entries in `app/core/pycasbin/policy.csv`. Run `uv run python app/pre_commit_checks.py` to validate.
- **Security Misconfiguration**: Check CORS settings in `app/main.py`, default credentials, unnecessary features.

### 5. Input Validation
- Verify all API endpoints use Pydantic V2 models (in `app/models/`) for request validation.
- Check form schema validation in `app/models/form_schema/`.
- Ensure file operations via OpenDAL (`app/utils/file_operations.py`) have type and size validation.
- Verify URL and redirect validation in self-signup routes.

### 6. Authorization Review
- Verify Keycloak OAuth2 flow in `app/core/oauth2.py`.
- Check PyCasbin policy enforcement — every route's `operationId` must appear in `policy.csv`.
- Review middleware stack order in `app/main.py` (AuthorizationMiddleware must come before AuthenticationMiddleware in add_middleware order, which means it runs after).
- Verify OTP validation in `app/route_utils/user_otp.py` for rate limiting and expiry.

### 7. Temporal Workflow Security
- Verify 1Password credential management in `app/one_password_util.py` — no secrets logged or stored in plain text.
- Check Kubernetes operations in activities — verify RBAC, no privilege escalation.
- Review subprocess execution in `app/utils/subprocess_execution.py` for command injection.
- Check CloudFlare/DNS operations for proper credential handling.

### 8. Report
Produce a findings report organized by severity (Critical, High, Medium, Low, Info) with:
- Finding description.
- Affected file and line.
- Recommended fix.
- Reference (CWE number or OWASP category).

## Rules

- Prioritize findings by exploitability and impact, not just theoretical risk.
- Include proof-of-concept for critical findings when safe to do so.
- Do not just list tools to run. Actually analyze the output and provide actionable recommendations.
- Check both the application code and infrastructure configuration (Dockerfiles, rootfs/).
- Note: This repo uses `| sqlsafe` in Jinja2 SQL for trusted/computed values. Only flag `| sqlsafe` usage on user-provided input as a vulnerability.
