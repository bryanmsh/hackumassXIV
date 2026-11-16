# Plan: drop Gemini, use only our own models

2026-11-15. The Gemini key has been deleted and removed from the Vultr server. From now on every AI
step runs on our own models: the subject finder and namer (`subject_model/`), and the cut-out cascade
(our cut-out model, then SAM 2.1 small) that is already live.

## Where Gemini is used today

| Step | Code | Owner | With no key today |
| --- | --- | --- | --- |
| Choosing the subject of each page | `pipeline/gemini.py` `choose_subjects`, called by `pipeline/process.py` | Bryan | **Broken.** The server runs `SUBJECT_FINDER=cascade`. Every page our model is not sure of goes to Gemini, which raises "GEMINI_API_KEY is not set", and the page ends Failed. On *Animal Homes* that is 15 of 16 pages |
| Naming a teacher's click | `pipeline/gemini.py` `label_crop`, called by `pipeline/click.py` | Bryan | Works but weaker: when our namer is unsure, the Gemini call fails, `_label` catches it and returns "", and the teacher types the name |
| Second look | `checks/second_look.py` | Kevin | Returns a warning, "Second look skipped: no GEMINI_API_KEY is set", on every page |
| Upload screen wording | `web/src/components/books/UploadForm.tsx`, `web/src/pages/SubjectReviewPage.tsx` | Thomas | Says pages go to "an outside AI service". That is no longer true |
| Settings and docs | `.env.example`, `infra/DEPLOY.md`, `Caddyfile`, `compose.yaml` comments, `README.md`, `pipeline/README.md`, `CLAUDE.md`, the spec | Bryan, plus whole team for the spec | Out of date |

The contracts do not change. `process_page`, `segment_at_point`, `refine_mask`, `second_look` and
every HTTP route keep their signatures and outputs. `subject_model/local.py` already returns the
same answer shape Gemini did, so the rest of the app cannot tell the difference.

## What we give up (say this to the team before starting)

From `subject_model/README.md`, scored on 38 team-labelled pages with 121 subjects:

| | Gemini | Our model alone |
| --- | --- | --- |
| Subjects found | 73 of 114 | 17 of 121 |
| First choice is a main subject | 31 of 37 pages | 13 of 38 pages |
| Ready and right | 8 | 4 |
| Ready and wrong | 0 | 0 |
| Teacher asked | 28 | 33 |

On *Animal Homes* in local mode, 7 pages came back Ready and **4 of those 7 were wrong**. So the
teacher will pick or outline the subject on most pages, and we need a guard so a wrong guess is
never pre-selected (step 1.2). The demo should lean on the click-to-pick and outline flows.

We also lose the Gemini sponsor prize track. We gain: no page leaves our server, no API cost, no rate
limits, and a page takes about 1 to 5 s instead of 8 to 20 s.

## Phase 0: get the live site working again (Bryan, about 5 minutes, no code)

1. On the Vultr server, in `.env`: set `SUBJECT_FINDER=local`. Delete the `GEMINI_API_KEY` and
   `GEMINI_MODEL` lines if any are left.
2. Restart the api container (`docker compose up -d api`).
3. Re-run the pages that failed with "GEMINI_API_KEY is not set" (the Subject review page's
   re-run button, or `python -m pipeline.run_book` for the demo book).
4. Check the api log shows `subjects by local (setting)` and no page is Failed.
5. Locally: delete the `GEMINI_API_KEY` line from the repo-root `.env` too (the key is revoked, but
   it should not sit on disk).

After Phase 0 the site works with no code change, but local mode can pre-select wrong subjects
(4 of 7 on *Animal Homes*). Phase 1 fixes that.

## Phase 1: pipeline (Bryan, about 1 to 1.5 hours)

Keep the file name `pipeline/gemini.py` for now. `subject_model/local.py` and
`subject_model/evaluate.py` (Andrew's) import from it, and renaming would mean editing his folder.
A rename to `pipeline/subjects.py` with `gemini.py` left as a one-line re-export can come after the
hackathon.

1.1 **Make local the only subject finder.** In `pipeline/gemini.py`:
- `choose_subjects` and `label_crop` always use `subject_model.local`.
- `SUBJECT_FINDER` set to `gemini` or `cascade` (an old `.env`) logs one warning and uses local,
  so a stale setting cannot break the server.
- Delete the Gemini call code: `_generate`, `gemini_subjects`, `gemini_label_crop`, the prompts,
  the token and time limits.
- Keep everything `subject_model/local.py` imports: `SubjectAnswer`, `_drop_non_subjects`,
  `DUPLICATE_IOU`, `GROUP_HOLDS`, `INSIDE_FRACTION`, `MAX_CANDIDATES`. Keep `GeminiError` and
  `RateLimited` as names, because `process.py`, `click.py` and Andrew's code catch them. Fix the
  module docstring.
- If `subject_model` or its weights are missing, raise the same plain error as today
  ("The local subject finder is not set up on this server"), so the page is Failed with a
  readable reason.

1.2 **Never pre-select a guess the page text does not back up.** `local_is_enough` already
encodes Andrew's trust rule (exactly one subject would be pre-selected, the page text names it,
and the text is not about anything else). Today only the cascade uses it. Use it in every case:
- Add an internal field `trusted: bool = True` to `SubjectAnswer` (pipeline-internal, not a contract).
- `choose_subjects` sets `trusted = local_is_enough(answer, text)[0]` and records the reason in
  `last_subject_route()`.
- In `process_page`, when `decide_state` says Ready but the answer is not trusted, the page becomes
  Needs subject with reason "Our model is not sure this is the subject. Please check it." The
  candidates stay, so the teacher's best guess is one click away.
- Expected on *Animal Homes*: the wrong Ready pages turn into Needs subject; the bear, crocodile and
  tiger stay Ready only if their page text passes the rule.

1.3 **Tidy the rest of `pipeline/`.**
- `process.py`: drop the key-scrubbing in `_reason`; fix docstrings and the "Gemini" comments.
  Keep the 0 to 1000 box scale; our model uses it too (rename `GEMINI_SCALE` to `BOX_SCALE`).
- `click.py`: fix the `_label` docstring.
- `run_book.py`: fix the docstring that mentions `GEMINI_API_KEY`.
- `requirements.txt`: remove `google-genai`. (`checks/requirements.txt` still has it until Kevin's
  step, and the Docker image installs both, so the image shrinks only after Phase 2.)

1.4 **Tests** (`pipeline/tests/`).
- `test_gemini.py`: delete the tests of the Gemini call; keep the guard tests
  (`_drop_non_subjects`) and the `local_is_enough` tests.
- `test_live.py`: delete (it only calls the real Gemini API).
- `test_subjects.py`, `test_process.py`, `test_click.py`: replace Gemini mocks with a fake local
  answer; add one test each for: untrusted Ready becomes Needs subject, trusted Ready stays Ready,
  a stale `SUBJECT_FINDER=gemini` still uses local, missing weights gives a Failed page with the
  plain reason.

1.5 **Check it.**
- `python -m pytest pipeline/tests -q` passes.
- `python -m subject_model.try_book` (or `run_book`) on *Animal Homes* with no key set: no Failed
  page; write down how many are Ready, Needs subject and No clear subject, and the time per page.
- `git grep -n -i gemini -- pipeline/` shows only the kept names and history notes.

## Phase 2: other owners (tell them; do not edit their folders)

**Kevin, `checks/second_look.py`.** Two options; Kevin picks.
- (a) Recommended: name the Cut-out-on-black image with our namer
  (`subject_model.local.label_crop`) and pass when its answer shares a word with the label, using
  the existing `matches`. It is the same namer that suggested the label, so the wording should say
  it is a weak signal, as it does now. No key, no network, under a second.
- (b) Turn the second look off: always return a warning that says it is not available. Simplest,
  but every page shows a warning, which looks bad in the demo.
- Either way: remove `google-genai` from `checks/requirements.txt`, and update the
  `GEMINI_API_KEY` test in `checks/tests/test_checks.py`.

**Thomas, `web/`.** Change the upload notice from "each page is sent to an outside AI service" to
something like "Pages are processed on our own server and never leave it." Same for the re-run
dialog in `SubjectReviewPage.tsx`, and the two tests that look for the old words. This is now a
privacy point worth showing in the pitch.

**Andrew, `subject_model/` and `api/`.** No code has to change. Optional: fix docstrings that say
"Gemini-shaped" and the comments in `api/tests` and `api/docs` that mention spending the Gemini key.
`subject_model/evaluate.py --modes gemini` will stop working; the saved Gemini answers in
`data/subject_testset/gemini/` still let it score against them.

**Kevin, `pitch/`.** Drop the Gemini sponsor track; use "nothing leaves our server" and "three
models we trained ourselves" instead.

## Phase 3: settings and docs (Bryan, about 30 minutes)

- `.env.example`: remove `GEMINI_API_KEY` and `GEMINI_MODEL`; add `SUBJECT_FINDER=local`.
- `infra/DEPLOY.md`: remove the Gemini row; `SUBJECT_FINDER` is `local`.
- `Caddyfile` and `compose.yaml`: fix comments that say the password protects the Gemini key (it
  still keeps strangers from uploading PDFs and using our CPU).
- `pipeline/README.md`: replace the Gemini sections with how our subject model is used and the trust
  rule; keep the old Gemini measurements under a short "Before 2026-11-15" note, since they explain
  the numbers in the writeup.
- `README.md` (Bryan or whoever owns it): tech stack, model cascade section, mermaid diagram,
  numbers, and the privacy line "Book pages are sent to an outside AI service".
- `CLAUDE.md` tech stack line and the spec's Part 2 tech stack: these change the team's stated
  stack, so agree it with all four people first. The frozen contracts themselves are unchanged.

## Order and timing

| When | What | Who |
| --- | --- | --- |
| Now | Phase 0 on the server | Bryan |
| Next hour | Phase 1, then merge to `main` with the team's OK so the server picks it up | Bryan |
| In parallel | Phase 2 messages sent; each owner changes their folder | Kevin, Thomas, Andrew |
| After Phase 1 | Phase 3 docs | Bryan |
| Before the demo | Run *Animal Homes* end to end on the live site; practise picking subjects by click and outline | Everyone |

## Risks

- **Many more pages need the teacher.** Expected and safe: the teacher approves every page anyway.
  The demo script should show it as a feature ("the app asks when it is not sure").
- **Click names are often empty.** The namer names a click only at 0.5 or more; otherwise the
  teacher types. Do not lower the bar: a wrong name is worse than an empty box.
- **Weights missing on the server.** They are in the image at `/app/subject_model/weights/`. If
  they go missing, pages are Failed with a plain reason, and the hand outline still works because it
  calls no model.
