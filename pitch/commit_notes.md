# Commit notes (Kevin, lane B)

One entry per commit, newest first: what changed, why, and what is still open.

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
