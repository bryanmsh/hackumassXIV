# LLM APIs

## Pattern
Browser -> your backend -> model provider -> validated structured result -> browser.

## Pseudocode (provider-neutral)
```python
# provider SDK details vary; consult current docs
# result = client.generate(model=..., messages=[...], response_schema=...)
# parsed = ResultSchema.model_validate(result)
```
Keep provider key in server environment. Bound token cost, set timeouts, handle rate limits, and include fallback error UI. Never assume generated text is factually correct. Add sources or deterministic validation. See [[Evaluation]] and [[Tool Calling & MCP]].
