# Mirai — HackUMass XIV

Product and technical requirements: `Product and technical spec.md`. Build schedule: `Mirai 24-Hour Build Plan.md`.

## Git workflow
- Each teammate works on their own branch (`bryan`, `andrew`, `kevin`, `Thomas`). Commit and push only to the current user's branch.
- Never commit, push, or merge to `main` without explicit permission. Permission for one action does not carry over to the next.
- Keep `main` demoable. Merge `main` into your branch often to catch conflicts early.
- Never use `git add .` blindly. Stage specific files, and never commit secrets (`*.env`).

## Dev log: `CLAUDE_NOTES.md`
After every change or commit, append an entry to `CLAUDE_NOTES.md` at the repo root before reporting the work as done. The file is gitignored (local only) and will feed the final writeup/Devpost, so each entry must explain what the feature does and how it's implemented, not just which files changed.

```
## YYYY-MM-DD HH:MM — <short title>  (commit <hash>, branch <name>)
**What:** what it does for the user and why it matters
**How:** files touched, libraries/APIs, architecture, key design decisions and tradeoffs
**Notes:** known issues, shortcuts taken, follow-ups (optional)
```

Keep entries brief but complete enough to reconstruct the work. Record real numbers (latency, accuracy, dataset size) when you have them, because they make the writeup stronger.

## Hackathon Toolkit
`Hackathon Toolkit/` is an Obsidian vault of reusable hackathon playbooks. Read the relevant note before starting matching work, and follow it unless the spec says otherwise:

| When you're doing... | Read |
|---|---|
| Backend / API endpoints | `02 - Tech Stack/FastAPI.md`, `07 - Reusable Templates/API Endpoint Template.md` |
| Frontend | `02 - Tech Stack/React + TypeScript.md` |
| Data storage | `02 - Tech Stack/Databases.md` |
| Auth | `02 - Tech Stack/Authentication.md` |
| Deploying | `02 - Tech Stack/Deployment.md` |
| Git problems / merges | `02 - Tech Stack/Git & GitHub.md` |
| LLM calls, prompts, agents | `03 - AI & ML/LLM APIs.md`, `03 - AI & ML/Tool Calling & MCP.md` |
| Retrieval / search | `03 - AI & ML/RAG.md`, `03 - AI & ML/Embeddings.md` |
| Vision / classic ML | `03 - AI & ML/Computer Vision.md`, `03 - AI & ML/ML Models.md` |
| Measuring quality | `03 - AI & ML/Evaluation.md` |
| Scoping / cutting features | `01 - Ideation/MVP Scope.md` |
| Architecture docs | `07 - Reusable Templates/Architecture Template.md` |
| Wiring pieces together | `05 - Execution/Integration Checklist.md` |
| Something's broken | `05 - Execution/Debugging Playbook.md` |
| README / writeup | `07 - Reusable Templates/Project README.md`, `06 - Demo & Pitch/Judging Criteria.md` |
| Demo prep | `06 - Demo & Pitch/Demo Script.md`, `06 - Demo & Pitch/Backup Demo.md`, `00 - Dashboard/Submission Checklist.md` |

Notes under `04 - Hackachusetts Tracks/` and the Hackachusetts-specific dashboard notes describe a past event. Don't treat their rules, tracks, or dates as applying to HackUMass.

Guiding principle (from the toolkit): one complete, credible, measurable workflow beats five unfinished features. Integrate before polishing.
