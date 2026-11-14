# Authentication

Avoid authentication unless essential to the product demonstration. A fake login should be labeled as a demo mode. For real auth use a trusted provider and server-side session/token verification; never store secrets in frontend code. Protect private data, limit OAuth scopes, and do not collect real patient data. Official reference: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
