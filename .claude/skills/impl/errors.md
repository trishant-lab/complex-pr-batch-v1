---
name: errors
description: Patterns for adding error codes and constants.
---

## Adding an Error Code

1. Add code dict to `app/exceptions/error_codes.py` with unique code
2. Create constant: `MY_ERROR = ServerErrorModel.initialize("R1001")`
3. Raise: `raise MY_ERROR.exc()` or with params: `raise MY_ERROR.exc(name=name)`

## Error Code Ranges

| Prefix | Category | Range |
|--------|----------|-------|
| C | Common | C1000=App, C2000=Internal, C3000=External, C4000=Config, C5000=Auth |
| R | Route | R1xxx per domain |
| T | Task | T1xxx per workflow type |

## Error Model

- `ServerErrorModel` in `app/exceptions/error_code_mapper.py`
- `LaunchpadHTTPException` for HTTP errors
- `displayMessage` supports `str.format()` placeholders
