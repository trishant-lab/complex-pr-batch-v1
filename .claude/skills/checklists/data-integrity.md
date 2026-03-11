---
name: checklist-data-integrity
description: Data integrity standards for mutations. Loaded during review and implementation.
---

- All mutations within a single request in one transaction (`execute_many`)
- PUT/DELETE are idempotent
- FK constraints respected — parent must exist before child insert
- `updatedAt` timestamp refreshed on mutations
- Read-then-write sequences must account for concurrent modification
- Provisioning workflows are idempotent — re-running should not create duplicates
