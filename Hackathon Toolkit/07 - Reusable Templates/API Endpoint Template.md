# API Endpoint Template

## Endpoint: [METHOD] /[path]
**Purpose:**
**Request JSON:**
```json
{"example": "value"}
```
**Success JSON:**
```json
{"result": "value"}
```
**Errors:** 400 invalid request, 429 rate limit, 500 internal error (adjust per endpoint).
**Owner:**
**Test cases:** happy path, missing field, empty input, upstream outage.
