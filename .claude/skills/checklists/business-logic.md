---
name: checklist-business-logic
description: Business logic standards for APIs and activities. Loaded during review and implementation.
---

- All async functions properly `await`ed
- Error paths return correct HTTP status + error code
- Edge cases handled: not-found, duplicate, validation failure
- DB access via `DBManager`, queries via Jinja2 SQL templates
- Work that can exceed request latency budget belongs in a Temporal activity, not the request handler
- Per-product branching uses `ProductEnum`, not string comparisons
