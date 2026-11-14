# Tool Calling & MCP

## Tool calling
LLM requests a structured tool action -> your application validates arguments -> executes authorized tool -> returns result to LLM. Never treat the model's tool call as permission to do sensitive actions.

## MCP
Model Context Protocol standardizes tools and resources exposed to AI clients. Docs: https://modelcontextprotocol.io/

## Simple tool contract
```json
{"name":"lookup_clinic","description":"Return clinic hours from an approved local dataset","parameters":{"type":"object","properties":{"clinic_id":{"type":"string"}},"required":["clinic_id"]}}
```
Keep operations read-only for demos; log calls; impose timeouts; allowlist destinations. Tool descriptions are not security boundaries. See [[Evaluation]].
