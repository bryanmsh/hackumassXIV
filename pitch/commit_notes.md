# Commit notes (Kevin, lane B)

One entry per commit, newest first: what changed, why, and what is still open.

## Demo script matches the app on main (16-page book, words band, cascade)

**What changed**
- Pulled `main` (fast-forward to 8a90127). `pitch/demo_script.md` rewritten against it and the team's notes:
  - 16-page *Animal Homes*: the hard page is now **page 3** (page 1 is the cover; 13 to 16 have no subject).
  - Words: always shown below at Tinted and Cut-out, in book line breaks, no page number, in the child's main colour when readable; the profile option is now "extra words below" for Faded page and Outlined.
  - Credits read from the book's own credits page on upload, and named in step 12.
  - Reader keys: B blanks the screen, Esc closes the bar. Hover spotlight on suggestions. Live URL miraai.study.
  - New "If a judge asks how the AI works": subject cascade (our model first, Gemini otherwise; 1 of 16 pages on Animal Homes), SAM 2.1 for cut-outs, our cut-out model ready but not live (0.897 vs 0.906 IoU), credits with no AI.
  - Open decisions: after a reset most pages arrive Needs subject, so step 6 leaves most out unless more are picked live.

**Why**
- The script still described the 5-page book (hard page 2), text as a profile toggle, and Gemini as the only subject finder.

**Still open**
- Decide step 6 with Andrew before the first judge. `pitch/checkpoint1_steps.md` still says 5 pages.

## README team row matches what Kevin built (plus merge main)

**What changed**
- Merged `origin/main` into `kevin` (clean; brings in Bryan's README, the model branch work and Thomas's Spotlight).
- `README.md` Team table, Kevin's row only: "Display, checks, pitch, and the cut-out model code (with Bryan)", folders `render/`, `checks/`, `pitch/`, `tests/`, `cutout_model/`. Dropped `eval/`, which holds only a `.gitkeep`.

**Why**
- The row came from the build plan's ownership, not from the work done: no evaluation exists yet, and the cut-out model code is not listed.

**Still open**
- Put `eval/` back in the row if the 20-page evaluation gets done.

## model: first set of labelled real-book pages

**What changed**
- `training_images_set_1/`: 11 picture-book pages (PNG, about 9 MB) from StoryWeaver-style books.
- `significant_subjects.json` (repo root): for each page file, the list of subjects that matter on it (e.g. `catch-that-cat-pg3.png`: boy, dog, cat).

**Why**
- Real picture-book pages with named subjects, to spot-check and later evaluate the cut-out model and subject choice beyond DUTS.

**Still open**
- No masks yet, only subject names. Check each book's licence before using pages in slides.

## render: text band reads like the page

**What changed**
- `render/core.py`: the band keeps the book's line breaks. Each non-empty source line is its own line, wrapped only when wider than the band. Lines that are only a page number (`^\s*\d+\s*(/\s*\d+)?\s*$`, e.g. "4/12", "12") are dropped; nothing else is removed, so "4/12 Spiders spin" stays whole. Text that is only a page number shows no band at all.
- Bigger type: `TEXT_SIZE` 0.06 to 0.075, `TEXT_BAND` 0.16 to 0.20; shrink-to-fit kept, floor 12 px (start size floor raised from 10 to 12 to match).
- Text is drawn in the child's main colour when it reaches 4.5:1 on the background, else white or black as before. `Rendered.text_color` is the drawn colour, so the `text_contrast` check measures what the child sees.
- `RENDER_VERSION` "b1" to "b2". New helpers `text_lines`, `band_text_color`, `layout_text` (no contract change).
- 4 new tests; existing band test reads `TEXT_BAND`. 65 pass across render, checks and tests.

**Why**
- PDF text arrives with page numbers and line breaks; collapsing it into one paragraph read unlike the book, and page numbers are noise for a CVI reader. Larger type and the child's own colour make the band easier to see.
- The band looks different, so old approvals must stop matching.

**Still open**
- Andrew: `RENDER_VERSION` is now "b2"; every existing approval with text on goes back to needing approval.

## render: overlay_palette, one colour per candidate on the review image

**What changed**
- `render/__init__.py`: new `overlay_palette(view_path, mask_paths, selected, fmt="webp")`, exported in `__all__`, next to an unchanged `overlay()`. New constants `SUBJECT_PALETTE` (the six web tokens, #1D4ED8 #C2410C #6D28D9 #BE185D #0F766E #EAB308; no green) and `OVERLAY_OTHER_TINT = 0.30`.
- Starts from the page dimmed by 0.55. Candidate i is tinted in `SUBJECT_PALETTE[i % 6]`: 0.30 when not selected, 0.45 plus a 3 px ring in its colour when selected. Painted largest mask first, selected last. Missing or unreadable masks are skipped silently.
- 6 new tests in `render/tests/test_render.py` (size, colours per candidate, dimmed page outside, selected ring exact and none when `selected=None`, empty list, index 6 = index 0, bad path skipped). 61 tests pass across render, checks and tests.

**Why**
- The Subject review chips are colour-coded but the picture was one cyan, so a teacher could not tell which chip was which object without number markers on the art.
- `RENDER_VERSION` stays "b1": a teacher-review image, not a child-facing render, so no approval is voided.

**Still open**
- Andrew: `page_overlay` takes optional `?palette=1` and calls `overlay_palette`; `api/modules.py` wires it like `overlay`. Then Thomas removes the number markers.
- On a page with a combined candidate, the combined one's colour is fully hidden by its parts (by design: parts stay visible). Its chip has no visible patch unless it is the selected one.

## Merge main (Bryan's pipeline, Andrew's API, Thomas's web) and demo script for the new subject rules

**What changed**
- Merged `origin/main` into `kevin`. Bryan's branch had nothing beyond `main`. Brought in: up to 5 subjects per page; combined cut-out offered but **not pre-selected** (9e09be4, Thomas with Bryan's OK); Andrew's credits autofill stand-in, re-approve tool, render-version approval tests; Thomas's custom colors and readability fixes. PR #20 (fidelity and email) is in `main`.
- `pitch/demo_script.md` steps 3 to 5 and `pitch/checkpoint1_steps.md`: page 2 arrives Needs subject with the combined option offered; the teacher picks the hornbill alone.

**Tested**
- 55 tests pass in `render`, `checks` and `tests` (the reader tests run against Andrew's latest API).

**Still open**
- Bryan's `pipeline/credits.py` has not landed; Andrew's upload keeps the teacher's credits until it does.
- The demo book is now the 16-page edition; page numbers in the script are still for the 5-page one.

## Fidelity check accepts combined cut-outs; demo script for pre-selected pages

**What changed**
- `checks/core.py`, `check_fidelity`: the "largest piece holds 90%" rule is gone. A cut-out may be in several pieces; it fails only when stray specks (pieces under 0.1% of the page) hold more than 10% of it. The detail says "in 3 pieces" plainly.
- Tests: five whole blobs now pass ("in 5 pieces"); a subject plus 40 specks fails ("stray specks").
- `pitch/demo_script.md` steps 3 to 7 and open decisions, `pitch/checkpoint1_steps.md` expected states.

**Why**
- Bryan's branch (commit b7bc13f, Andrew's decision) pre-selects one combined cut-out of all sure subjects on a page with several. Joining the three page 2 masks the same way failed fidelity at every look ("3 pieces; the largest holds only 48%"). It now passes: "covers 11.5% of the page, in 3 pieces." Display was already right.
- Re-checked all 24 real masks (GrabCut and SAM 2): the only fail is still the 0.08% woodpecker.
- Tradeoff: the check can no longer tell five scattered blobs from five real subjects. That is now the teacher's call on the contact sheet. Departs from the spec's "in one piece".
- The demo no longer has a page with nothing selected, so the hard page is now: page 2 arrives with all three together, and the teacher switches to the hornbill alone.

**Still open**
- Tell the team: fidelity no longer means "one piece".
- Agree with Bryan which Animal Homes edition is the demo book (his notes use a longer one).
- Display and check results change, not pixels, so `RENDER_VERSION` stays "b1".

## Teacher email: three questions, real book art (B4)

**What changed**
- `pitch/tvi_email.md`: cut to three questions (looks useful or missing; looks not tied to CVI phases; the 3 to 1 edge contrast rule). Says "teacher" and "not yet reviewed by a teacher". Adds the CC BY credit and a note of what we changed.
- `pitch/tvi_mockups/`: the made-up bird and rabbit images are replaced by *Animal Homes* page 2 (the hornbill), as printed plus all four looks. Tinted, Faded page and Outlined use Maya's settings (red on black); Cut-out uses Leo's (left, text below). Rendered with `render()` on Bryan's GrabCut mask.

**Why**
- A teacher judges real book art better than shapes we drew.
- The checks warn on contrast for the hornbill at Tinted, Cut-out and Faded page (black body on black). That became question 3, so the email asks about a real case, not a hypothetical one.

**Still open**
- Fill in the recipient, the judging date, and the author and illustrator from the StoryWeaver page, then send.

## Checkpoint 1 step list and word-for-word demo script (hours 7 and 10)

**What changed**
- `pitch/checkpoint1_steps.md`: 11 steps for checkpoint 1 on the live site, with who clicks, where, what to expect, and a column for what broke. Uses Thomas's real button names (Choose a PDF, Upload, Leave out, Suggestions, Tap the object, Draw an outline) and the real Animal Homes results.
- `pitch/demo_script.md`: rewritten word for word. About 4 minutes, Kevin speaks and Thomas drives. Adds the reset step before every judge (`python -m api.tools.reset_demo <book id>`), keyboard-only reader (the spec is now desktop and laptop only), wording rules from `PRODUCT.md`, and what to do if something breaks.
- Merged `origin/main` into `kevin` first (spec: desktop only; `PRODUCT.md`; the fixture PDF).

**Why some choices**
- Hard page: Animal Homes page 2 (hornbill, beehive, nest at equal confidence), proposed from the real run. The book has 5 pages, not the spec's 6.
- No page was pre-selected on the real run, so the script says so as the "honest" moment instead of hiding it.

**Still open**
- Confirm the demo book and hard page with Bryan (hour 10), and the picks for pages 3 to 5.
- Check that Thomas's Profiles has size, position and text controls; if not, Leo is Cut-out, centered, text off.
- Time it at the first rehearsal.

## Fidelity check: minimum cut-out size 1% -> 0.1% of the page

**What changed**
- `checks/core.py`: `COVERAGE_MIN` is now 0.001. The detail text shows two decimals ("0.08%").
- Tests: a 0.26% subject now passes fidelity and still gets the size warning for enlargement; a new 0.03% speck test still fails.

**Why**
- On Animal Homes, 8 of 13 real cut-outs failed at 1% although they were mostly right: the frogs, fish and tortoises are small in this artwork (0.2 to 0.7% of the page). The size check already warns when a small subject is enlarged more than 2.5 times, so a soft-looking result is still flagged. Kevin chose 0.1%; this departs from the spec's 1%, so tell the team.
- Check results only, no pixel changes, so `RENDER_VERSION` stays "b1" and no approvals are voided.

**Verified**
- 49 tests pass in `render` and `checks`.
- Animal Homes: fidelity failures went from 8 to 1. The one left is the woodpecker on the cover at 0.08%, a speck on a page the pipeline already marked No clear subject. A fair failure.

## render/try_book.py: real artwork from Animal Homes (hour 5)

**What changed**
- `render/try_book.py`: takes a book processed by Bryan's `pipeline.run_book` and, for every page and candidate, writes the overlay and all four looks, runs every check, and prints one line per look. No AI calls.

**What the real book showed** (5 pages, Bryan's pipeline with GrabCut, 51 s for the book)
- States: 4 pages Needs subject (several animals), the cover No clear subject. Nothing pre-selected, as the spec predicted for this book.
- 13 candidates, all rendered at all four looks: 52 images, median 184 ms per render on the laptop (the real masters are bigger than the samples).
- Good: hornbill (page 2), beehive, bird nest, spider, termite mound. All pass, except contrast warnings, which are real (dark subjects on black).
- Fidelity fails on all 8 candidates on pages 1, 4 and 5 for one reason: the cut-out covers under 1% of the page (0.1 to 0.7%). Looking at the overlays, the cut-outs are mostly right; the animals are just small in this artwork. The spec's 1% floor looks too strict for real books.
- Cut-out quality, for Bryan: the spider's cut-out includes a large patch of web and leaves, and the tortoise's has the shell but not the head. The checks cannot catch "wrong but in one piece"; that is the teacher's job.

**Still open**
- Decide whether to lower the fidelity floor (team call; the size check already warns about enlarging small subjects).
- Render speed on real pages: 184 ms on the laptop against a 150 ms server target; measure on the server.

## Reader tests over HTTP (hour 11)

**What changed**
- `tests/test_reader_http.py`: the plan's four reader tests, calling the API from outside over HTTP:
  1. an approved page is served (WebP, `Cache-Control: no-store`);
  2. a page that was never approved is refused with 403 and is listed as skipped;
  3. a page approved and then changed is refused, both its old link and its new version (run twice: a profile color change and a subject change);
  4. an approval sent for an old version gets 409 "look again", records nothing, and the page stays refused.
- Each test makes its own book (a generated two-page PDF) and draws the subject as an outline, which needs no AI, so the tests pass with the real pipeline or the stand-ins.
- `tests/conftest.py`: with no `MIRAI_URL`, it starts a local API by itself; with `MIRAI_URL` (plus `SITE_USER` / `SITE_PASSWORD`) it tests that server instead.
- `tests/local_server.py`: Andrew's API, unchanged, with an in-memory database (`mongomock`) because this laptop has no Docker or MongoDB. Pipeline stand-ins, real display code, the Gemini key removed.
- `tests/requirements.txt`: httpx, mongomock, pymupdf, pytest.

**Verified**
- 5 of 5 pass against the local API in about 13 s.
- With the approval check deliberately broken (every version counted as approved), all 5 fail. So the tests do catch an unapproved page reaching the reader.

**Still open**
- Run against the live site once Bryan has it up: `MIRAI_URL=... pytest tests`. There is no delete route, so they leave "zz-test" books and profiles behind there; the profiles would show in the reader's teacher bar.
- Hand the tests to Andrew (plan: hour 11).

## Second look: default model gemini-3.8-flash

**What changed**
- `checks/second_look.py`: the default model is now `gemini-3.8-flash`. The old placeholder `gemini-flash-latest` returns 404 for our key, and `gemini-2.5-flash` is closed to new users. `SECOND_LOOK_MODEL` or `GEMINI_MODEL` still override it.

**Verified**
- Real Gemini call with the team key: the bird page answered "red bird" and the rabbit page "rabbit", both pass, about 4 to 5 s each.
- With a wrong model name it returned a warning and did not crash, as intended.

**Still open**
- Bryan picks the team's `GEMINI_MODEL` for subject choosing; if it differs, the second look follows it.
- Open a pull request to get this onto `main`.

## Merge main into kevin; match Andrew's contract types

**What changed**
- Merged `origin/main` (Andrew's contracts and stub API, Thomas's web app, the spec and plan docs) into `kevin`.
- Resolved the one conflict, `render/requirements.txt`: kept Andrew's `pydantic>=2,<3` and added numpy, OpenCV, Pillow and pytest. Same pydantic pin in `checks/requirements.txt`.
- `run_checks` now returns `background = None` at Outlined and `text_contrast = None` when no text is shown, as `contracts/types.py` and Thomas's web app expect. It used to return a "pass" with an explanation.
- New tests: results are the real `contracts.types.CheckResult` and `SecondLook`, contract `Settings` are accepted, and `text_contrast` is absent when text is off.

**Verified**
- 70 tests pass across `render`, `checks` and `contracts`.
- Andrew's 34 API tests pass with both `RENDER=stub` and `RENDER=real`. With `real`, the API loads `render` and `checks` from this branch at startup.

**Still open**
- Open a pull request from `kevin` into `main` so Andrew can set `RENDER=real` on the server.
- Swap in Bryan's real pages when they land in `fixtures/`; nothing there yet.
- Reader tests in `tests/` (hour 11).

## Add commit notes

- Started this file. Every commit from here on gets an entry.
- No code changes.

## 0ceec2a: Owner B: render, overlay, run_checks, second_look with samples, tests and pitch drafts

**What changed**
- `render/`: `render()` for all four levels (Tinted, Cut-out, Faded page, Outlined), `overlay()` for subject review, `RENDER_VERSION = "b1"`. Size, position, extra outline and the text band (Atkinson Hyperlegible) are already in, though the plan lists them as Phase 2.
- `render/samples/`: two generated stand-in pages (bird, rabbit) with masks, plus two deliberately bad masks. These are stand-ins until Bryan's real pages land.
- `checks/`: `run_checks()` (fidelity, page edge, background, contrast, size, text contrast) and `second_look()` (Gemini, warning only). Also `swatch_contrast()` for the profile screen's 3 to 1 warning.
- `pitch/`: draft teacher email with mock-up images, first demo script.
- 45 tests in `render/tests` and `checks/tests`, including the source-fidelity proof at Cut-out.

**Why some choices**
- WebP encoder method 0: about 25 ms faster per page. Median render is now 116 ms on the laptop, against a 150 ms target.
- Edge softening only goes inward, so no pixel from outside the mask can ever show.
- Types mirror Contract 2 locally and switch to Andrew's `contracts/types.py` automatically when it exists.

**Still open**
- `second_look` not yet tried against real Gemini (no key on this machine).
- Swap in Bryan's real pages (hour 5).
- Reader tests in `tests/` (hour 11).
- Email: trim to three questions, say "teacher" instead of "TVI." Demo script: add when the reset script runs.
