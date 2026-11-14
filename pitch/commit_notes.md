# Commit notes (Kevin, lane B)

One entry per commit, newest first: what changed, why, and what is still open.

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
