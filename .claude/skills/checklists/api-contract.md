---
name: checklist-api-contract
description: API contract standards for routes, models, and error codes. Loaded during review and implementation.
---

- Request/response models use Pydantic V2 syntax (`@field_validator`, `model_config`)
- `X | None` not `Optional[X]`
- `list[X]`, `dict[K, V]` not `List`, `Dict`
- Error responses via `ServerErrorModel.initialize()` codes, unique per domain range
- Status codes: POST=201, GET=200, PUT=200, DELETE=204
- Route registered with proper `operation_id`
- Policy.csv entry for new routes
