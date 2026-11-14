# Debugging Playbook

1. Reproduce with minimal input; copy exact traceback/status code.
2. Identify layer: UI, network, backend, data, provider, deployment.
3. Test each boundary independently (`curl`, browser network tab, server logs).
4. Compare request and response schemas.
5. Check environment variables, CORS, ports and URL base.
6. Change one thing; rerun the smallest test; record the fix.

```bash
curl -i http://localhost:8000/health
curl -i -X POST http://localhost:8000/analyze -H 'Content-Type: application/json' -d '{"text":"hello"}'
```
Never paste secrets into screenshots, public issues or LLM prompts.
