# Miraai: decisions and progress notes

Compiled 2026-11-14 from claude-mem's decision log, its work-state lists, and `CLAUDE_NOTES.md`. In the logs "Andrew" is the repo owner (the `andrew` branch and the `api/` and `contracts/` lane).

## Decisions made

### Project direction (Nov 13, late)
- The idea was chosen through a three-round agent debate. The pick was "FocusPage" (now Miraai): Gemini finds the subject, a cut-out isolates it, and the page is re-tinted for CVI. Crosscheck was the fallback.
- The go/no-go gate was cutting out the right subject on 7 of 10 real pages.
- The records do not say outright that FocusPage became Mirai. That link is inferred from the pipeline matching.

### Subject finding (Gemini pipeline)
- Show up to 5 candidate subjects instead of 3, so every main subject on a page surfaces. Three code guards back the prompt: drop setting words, drop group boxes, and merge duplicate boxes. A fixed seed makes answers repeatable.
- Pages arrive with a subject pre-selected, departing from the spec. A one-subject page selects its top candidate, and the teacher is asked only when the AI finds nothing or is not sure. A later follow-up (9e09be4) stopped pre-selecting the combined multi-subject cut-out; it is now offered but not selected.
- Chips on the page card are multi-select with no extra button. A first version that needed a "Choose several" button was rejected.
- Conservative caps on a single Gemini call, after asking how to stop a runaway call.

### Approval and spec
- Approval is scoped to one page, one cut-out, one profile and one look. Any change voids it. Re-approval after a render-version bump is handled by a tool that copies old decisions forward and deletes nothing.
- The API uses 0 to 1 fractions for positions. The Python functions use master pixels, and the API converts in one place.
- A teacher-picked subject sets the page state to `ready`. Sheet rows gain `confirmed`, `omitted` and `subject_source` fields (additive only).
- An overnight run settled ten spec gaps, each pinned by a named test. They cover upload refusals, when subjects and retries are allowed, and what counts as fully approved.

### Infrastructure
- The database went back and forth. It started as Atlas in the spec. At 11:31 it moved to a Compose container to keep the live database off laptops. At about 8 PM the live server switched back to Atlas M0, hot-patched without merging, driven by the sponsor prize and the project's stated database. Rollback is to empty `MONGODB_URI` in `/opt/mirai/.env` and run `docker compose up -d`.
- Explicit go-ahead is required before merging to main or redeploying. This is recorded as a standing rule on the `andrew-lane-finish` list.
- PRs on the owner's branches do not require reviewers.

### Local subject model (`model` branch)
- Build a Gemini-free subject finder (namer, finder and chooser) trained from random weights. The expectation was that it would be clearly worse than Gemini, with both measured on the same pages.
- It ran in the main checkout instead of a separate worktree.
- Test labels cover every main subject on realistic multi-subject pages, not single easy ones. That gave 38 pages and 121 subjects, built from Thomas's and Kevin's labels.
- The namer keeps whitened crops, because plain rectangles produced 2 wrong Ready pages.
- The Gemini agreement run was dropped.
- The trained weights were committed to `model` so Bryan can build the cascade from the repo.

## Where the project stands

| Area | Status |
|---|---|
| Pipeline, API and reader | Merged to main through PRs #19, #20 and #22. Spec and README updated. |
| Atlas | Live via hot-patch. PR #36 (Atlas support) merged into main, and the server was fast-forwarded to a852cf0. |
| Credits autofill | PR #23 is open and mergeable, not merged. It sits behind a stand-in until Bryan's `pipeline/credits.py` lands. |
| Subject model | All code done, 74 tests pass, weights pushed at 4b488f2. |

### Subject-model numbers (the 37 pages both modes answered)

| | Gemini | Local |
|---|---|---|
| Subjects found | 73 of 114 | 17 of 114 |
| Subjects named | 72 | 6 |
| First choice a main subject (pages) | 31 of 37 | 13 of 37 |
| Ready and right | 8 | 4 |
| Ready and wrong | 0 | 0 |

- Local runs at 0.07 s a page and about 740 MB, against Gemini's median of 10.9 s a page.
- The local model's weak points are the finder, which mostly marks one big blob per page, and the namer, which was trained on clip-art. Given the right rectangle, the namer's top guess is right for only 21 of 121 subjects.
- On Animal Homes, 4 of the 7 local Ready pages were wrong in both name and cut-out. All 3 correct ones were confirmed by the page text.
- Cascade rule: use the local answer only when exactly one subject is selected and the page text confirmed the name, otherwise ask Gemini. On the test set that avoids Gemini on about 1 page in 10 (range 4 to 25%), and the local answer was right on all 4.
- For the pitch, say "about 1 in 10 pages with no API call". Do not say "N times cheaper": there are no token counts yet and the current Gemini price is unknown.

### Remaining after the open questions are settled
- Final whole-branch review, a fix pass, and finishing the branch.
