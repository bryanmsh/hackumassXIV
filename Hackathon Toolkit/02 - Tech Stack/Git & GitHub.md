# Git & GitHub

```bash
git init
git add .
git commit -m "Initial MVP"
git branch -M main
# after creating remote: git remote add origin <URL>
git push -u origin main
```
## Team convention
- `main` always demoable.
- Feature branches `feature/frontend`, `feature/api`, etc.
- Pull frequently; small PRs; integrate every 60–90 minutes.
- `.gitignore`: `.env`, `.venv/`, `node_modules/`, local DBs and generated secrets.
- `git status` and `git diff` before commit. Never commit API keys.

See [[Integration Checklist]].
