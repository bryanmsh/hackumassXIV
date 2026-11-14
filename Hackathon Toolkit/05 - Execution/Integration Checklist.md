# Integration Checklist

- [ ] Frontend/backend agree on JSON field names
- [ ] API has `/health` endpoint
- [ ] Error states visible to user
- [ ] CORS exact origins configured
- [ ] Mock data replaced or labeled
- [ ] All contributors pull latest `main`
- [ ] Environment variable names documented without values
- [ ] One clean install tested
- [ ] Demo path works without developer-only state
- [ ] Backup demo ready

API contract example: `POST /analyze` request `{ "text": "..." }`, response `{ "length": 3, "text": "..." }`.
