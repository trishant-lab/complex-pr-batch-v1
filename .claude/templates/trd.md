# TRD: {{FEATURE_NAME}}

**Date**: {{DATE}}
**Author**: Agent (workflow command)
**Status**: Draft | Approved | Implemented

## 1. Overview

### Problem Statement
<!-- What problem does this solve? Who is affected? -->

### Proposed Solution
<!-- 1-2 sentence summary of the approach -->

### Affected Layers
- [ ] API Routes (`app/routes/`)
- [ ] Pydantic Models (`app/models/`)
- [ ] SQL Templates (`app/sql/`)
- [ ] Database Migration (`db/migrations/`)
- [ ] Error Codes (`app/exceptions/`)
- [ ] Temporal Activities (`app/cli/temporal/activities/`)
- [ ] Temporal Workflows (`app/cli/temporal/<product>/workflows/`)
- [ ] Worker Config (`app/core/cli_settings.py`)
- [ ] Product Templates (`app/cli/temporal/<product>/templates/`)
- [ ] Product Settings (`app/core/product_settings/`)

## 2. API Design (if applicable)

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/{{path}}` | {{description}} |

### Request/Response Models

```python
class {{Domain}}Request(BaseModel):
    # field: type = Field(constraints)
```

## 3. Data Model (if applicable)

### New Tables / Migrations

```sql
-- migrate:up
CREATE TABLE IF NOT EXISTS {{table}} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- migrate:down
DROP TABLE IF EXISTS {{table}};
```

## 4. Temporal Workflows (if applicable)

### Workflow

| Name | Queue | Worker | Trigger |
|------|-------|--------|---------|
| `{{Product}}OnboardingWorkflow` | `{{product}}_onboarding` | WORKER_1 | API / CLI |

### Activities

| Name | Timeout | Max Attempts | Description |
|------|---------|-------------|-------------|
| `{{Activity}}` | 5 min | 5 | {{description}} |

## 5. Error Handling

| Code | Message | Status | Condition |
|------|---------|--------|-----------|
| R{{NNNN}} | {{message}} | 400 | {{condition}} |

## 6. Security & Authorization

- [ ] Policy.csv entries for new routes
- [ ] No PII in logs
- [ ] No hardcoded secrets

## 7. Testing Strategy

- [ ] Happy path tests
- [ ] Error case tests
- [ ] Edge cases

## 8. Implementation Plan

| Step | What | Where | Complexity |
|------|------|-------|-----------|
| 1 | Models | `app/models/` | S |
| 2 | SQL templates | `app/sql/` | S |
| 3 | Error codes | `app/exceptions/` | S |
| 4 | Activities | `app/cli/temporal/activities/` | M |
| 5 | Workflows | `app/cli/temporal/<product>/workflows/` | M |
| 6 | Worker config | `app/core/cli_settings.py` | S |
| 7 | Routes | `app/routes/` | M |
| 8 | Tests | `test/` | M |
