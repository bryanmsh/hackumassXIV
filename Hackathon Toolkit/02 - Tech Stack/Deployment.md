# Deployment

## Minimum deployment test
- Backend exposes `/health` and listens on host `0.0.0.0` and platform-provided `PORT`.
- Frontend uses configurable API base URL (e.g. `VITE_API_BASE_URL` for public URL only).
- Secrets configured server-side.
- CORS allows exact deployed frontend origin.
- Verify app in incognito and mobile.

```bash
# Example backend command; platform may inject PORT
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```
Keep a screen recording if hosted services fail. See [[Backup Demo]].
