---
name: python
description: Patterns for Pydantic V2 models, custom types, and enums.
---

## Models

- Place in `app/models/<module>.py`
- Pydantic V2 only: `@field_validator`, `@model_validator(mode="before"|"after")`, `model_config`
- `X | None` not `Optional[X]`, `list[X]` not `List[X]`
- No DB queries or side effects in model files
- Models must not import from `app/core/db`, `app/routes/`, or `app/cli/`

## Products

- `ProductEnum` in `app/models/product.py` — all product-specific logic branches on this enum
- Product settings in `app/core/product_settings/<product>.py`
