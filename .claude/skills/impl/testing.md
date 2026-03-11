---
name: testing
description: Patterns for writing pytest tests in Launchpad.
---

## Essentials

- Test files in `test/` directory
- Use `uv run pytest` for all test execution
- `AsyncMock` for mocking async functions, never `Mock`
- All new routes should be covered by tests

## Running Tests

```bash
# Full suite with coverage
uv run pytest --cov=./app test/ -s -v \
  -W ignore::DeprecationWarning:opentelemetry.instrumentation.dependencies \
  --cov-report term-missing

# Single file
uv run pytest test/test_file.py -s -v

# Single test
uv run pytest test/test_file.py::TestClass::test_method -s -v
```

## Common Patterns

- Mock external services (Keycloak, Stripe, Lago, 1Password, CloudFlare)
- Use `@pytest.mark.asyncio` for async tests
- Descriptive test names: `test_<action>_<scenario>_<expected_outcome>`
