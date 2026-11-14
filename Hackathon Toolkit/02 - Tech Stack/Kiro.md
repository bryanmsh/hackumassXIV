# Kiro

## Historical context
Hackachusetts 2026 was powered by Kiro; confirm current event tool requirements from its own rules. Official site: https://kiro.dev/

## Suggested agent workflow
1. Write a 1-page spec with acceptance criteria in [[MVP Scope]].
2. Ask for small independently testable tasks, not the whole app at once.
3. Require changes to include tests, clear file paths and run commands.
4. Inspect diffs and test output; do not trust unexecuted claims.
5. Keep generated code and dependencies under version control.

Prompt: 'Implement only the POST /analyze endpoint described in the spec. Include Pydantic validation, one happy-path test, one invalid-input test, and exact commands to run them. Do not change unrelated files.'
