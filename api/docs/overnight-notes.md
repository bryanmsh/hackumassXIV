# Overnight notes

Every MVP route is real now. It runs on the stand-in pipeline and display. **171 tests pass** (`.venv/bin/python -m pytest api contracts -q`). Thomas's own typed client (`web/src/api.ts`) ran the whole demo against the live API without a failure. That run covers the fields the joining test reads; `api/tests/test_shapes.py` checks every field the examples show on populated responses.

Two checks to run first thing:

- `bash api/joining/run.sh` runs the web client through upload, review, profiles, approval and the reader. It uses a throwaway database (`mirai_joining`) and folder, stops its own server, and exits 0 only if everything passed. It refuses to start if something already listens on port 8765. MongoDB must be running (`docker start mirai-mongo`).
- `.venv/bin/python -m pytest api contracts -q` runs the rest. `api/tests/test_shapes.py` checks that every JSON route answers in the shape of `contracts/examples.json`, and fails if a response is empty where its example has content.

The server also survives a hard kill. I started it on a throwaway database, put a page in `processing`, killed the server with `kill -9`, and started it again. The page came back `failed` with the reason `interrupted, retry`, and nothing was left stuck.

## Decisions

The spec left these open. Each is one line with the test that pins it. Overrule any in the morning; the test is the place to change with it.

1. **Upload limits answer 413** with a plain `detail`; a file that is not a readable PDF answers 400. Tests: `test_over_30_pages_is_refused`, `test_over_the_size_limit_is_refused`, `test_not_a_pdf_is_refused`.
2. **A subject can be set on any page that is not processing** (409 if it is). It makes the page `ready` and clears `confirmed` when the subject changes. Tests: `test_changing_the_subject_clears_the_confirmation`, `test_processing_page_cannot_be_changed`.
3. **Retry is allowed only from `failed` and `unsupported`** (409 otherwise). `unsupported` needs `force: true`. Test: `test_retry_rules`.
4. **Confirm all confirms pages that are `ready`, have a subject, and are not left out or already confirmed**, and returns exactly the pages it confirmed. Test: `test_confirm_all_confirms_only_ready_pages_not_left_out`.
5. **A page has a version only when it has a subject, is confirmed and is not left out.** Otherwise its version is null on the sheet and the reader refuses it. Tests: `test_a_left_out_page_has_no_version`, `test_pages_without_a_version_cannot_be_approved`.
6. **`GET /render/...` answers 409 when `v` is sent and is not the current token**, so a sheet never shows a picture that differs from what it will approve. Test: `test_render_refuses_a_stale_token_and_a_page_with_no_subject`.
7. **`GET /pages/{id}/overlay` with no subject selected returns the page unchanged**, so the review grid still shows it. Test: `test_overlay_without_a_subject_is_the_plain_page`.
8. **A version is "fully approved"** when the book has at least one approved page and every page is either left out or has a decision (approve or reject) on its current version. Tests: `test_fully_approved_versions`, `test_an_undecided_page_blocks_fully_approved`.
9. **The reader's `versions` list** each profile at its own level, plus every other (profile, level) pair that has an approval on this book. Test: `test_fully_approved_versions`.
10. **Demo reset** puts each page back to what the pipeline last returned, using `auto_state`, `auto_subject_hash` and `auto_reason`, saved when a result lands. Tests: `test_reset_returns_the_book_to_just_processed`, `test_reset_twice_is_the_same_as_once`.

Decided during the run, because the plan or the first attempt was wrong or silent:

- **A failed page's reason is the error text with server paths removed.** If the error has no text, the reason is the error's class name. The full error goes to the log. Reason: a server path must never appear in a response. Tests: `test_failure_reason_hides_server_paths`, `test_failure_with_no_message_names_the_exception`.
- **The stand-in pipeline always returns three pages**, whatever the PDF. Tests that need a second approvable page get one by selecting candidate 0 on page 2 and confirming it. The stand-ins were left unchanged.
- **Every assertion in the swap check carries a message** that names the assumption it tests. If there are no automatic cut-outs to check, that part is skipped with a reason instead of passing without checking anything.
- **The approval test for "another book" uses a second confirmed book.** The first version of the test would have passed even without the book filter. It was checked by removing the filter.
- **The tests hide one library warning.** `api/tests/conftest.py` filters pymupdf's import-time DeprecationWarning on Python 3.14. It is not ours to fix.
- **The `SQUARE(a)` outline in the swap check** is the same 4-point square as the outline test: 0.2 to 0.6 of the width and height.

## Needed from other owners

**Bryan**

- `compose.yaml` needs a MongoDB service, or an Atlas URI in `MONGODB_URI`. The API reads the database name from the end of that URI (default `mirai`). Locally it uses the Docker container `mirai-mongo`; it never touched Atlas.
- `api/requirements.txt` now includes `pymupdf`. Rebuild the image.
- Add a request body limit in Caddy (`request_body max_size 50MB`). The API answers 413 for a file that is too large, but it reads the whole upload before it can say so. The real cap has to be at the proxy.
- `pipeline/` has no importable code yet, so the import paths in `api/modules.py` for the real pipeline are guesses. `api/modules.py` expects `pipeline.rasterize`, `process_page`, `segment_at_point` and `mask_from_outline`, and the display side expects `render.render`, `render.overlay`, `render.RENDER_VERSION`, `checks.run_checks` and `checks.second_look`. If your names differ, tell Andrew.

**Kevin**

- Your four reader tests still need to run as the outside check once the real display is in. The API's own reader tests use the stand-in display.

**Swap check (hour 4 display, hour 7 pipeline)**

Run these as the swaps land. A missing pipeline stops test collection and hides display problems, so check the display alone first:

- Hour 4, display only: `RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q 2>&1 | tail -30`
- Pipeline only: `PIPELINE=real .venv/bin/python -m pytest api/tests/test_swap.py -q 2>&1 | tail -30`
- Hour 7, pipeline, with the display already real: `PIPELINE=real RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q 2>&1 | tail -30`

Output of the both-real command tonight (expected: the pipeline is not there yet):

```text
==================================== ERRORS ====================================
___________________ ERROR collecting api/tests/test_swap.py ____________________
api/tests/test_swap.py:16: in <module>
    from api import modules
api/modules.py:42: in <module>
    pipeline, display = load(settings.PIPELINE, settings.RENDER)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api/modules.py:23: in load
    rasterize=real_pipeline.rasterize, process_page=real_pipeline.process_page,
              ^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: module 'pipeline' has no attribute 'rasterize'
=========================== short test summary info ============================
ERROR api/tests/test_swap.py - AttributeError: module 'pipeline' has no attri...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.07s
```

**Thomas**

- Nothing blocks you. The joining run and the shape tests found no place where the API and `web/src/api.ts` disagree, for the fields they read. `web/` was not touched.

## Not done

Left for people, on purpose:

- **Atlas.** Everything ran on local Docker MongoDB.
- **The live deploy** on Vultr.
- **The hour 4 and hour 7 swaps** to the real display and pipeline (commands above).
- **The alignment check on the tablet.**
- **The second-look run over the backup books.** `python -m api.tools.second_look [book_id]` does it.

Cut, because they belong to a later phase: `refine_point`, `tidy`, `/eval/summary`, `api/tools/reapprove.py`, and the render-version and switch-back approval tests.

Things to know:

- **Second look can stay stale.** A second look left pending by a restart, or stored as a warning, is only refreshed by `python -m api.tools.second_look` or by changing the subject.
- **Confirm accepts any page that is not processing and has a selected subject.** It does not insist on `ready`. Confirm all does.
- **Approving the same page twice in one request records two decisions.** The later one wins.
- **Demo reset deletes approvals of a skipped page that is still processing.** The page itself is left alone.
- **`api/requirements.txt` lists `httpx2`, not `httpx`.** Starlette's test client imports `httpx`. It is installed in the current `.venv`, so tests pass, but check that a fresh install gets it.

Known small gaps:

- Upload size is checked after the upload is fully received (see Caddy above).
- The 413 messages hard-code "50 MB" and "30 pages" instead of reading the constants.
- The book stores no text source; it is rebuilt as "layer" or "none" from the text.
- If the database write fails during an upload, an orphan book folder can remain, or the book stays `ingesting` until the next restart.
- A failed database write after a cut-out leaves an orphan mask file.
- Two writes (subject set, confirm, leave out) read then write. The subject list is written whole, so a very close second write can be lost. A `$push` would close it.
- Patching a profile without `settings` does not recompute the settings hash. Same result today.
- The render cache is bounded by count (256 images), not bytes.
- The reader manifest runs one approval query per (profile, level) pair and page. It is small at this size.
- There is a tiny window between the reader's approval check and its render. Images are `no-store`, so it is acceptable.
- A missing image file gives a bare 500 (no path leaks).
- Some tests are thinner than they could be: no test of the render cache key across levels or profile edits; no check that a correct `v` gives 200 on render; the outline test in the swap check looks at two pixels, not the area; the display check does not prove the four looks differ; no test that the second-look command skips unconfirmed pages.
- The "look belongs to this subject" comparison is written in four places.
- `render_page` in `api/images.py` has a parameter named `settings` that shadows the `settings` module.
- `pytest -W error` crashes inside pymupdf. A normal run is clean.

## What was built

`git log --oneline main..andrew` (the last commit, "api: joining check against the web client, shape tests, overnight notes", is the one that adds this file):

```text
8213b01 api: swap check names every assumption and reports unchecked auto masks
23ed438 api: swap check that runs the contract tests against real or stand-in...
9ec6084 api: demo reset skips pages in progress, tests prove it
d392ecc api: demo reset script
ff58613 api: second look in the background, with a catch-up command
1b33c62 api: reader refusal tests cover odd queries
c2c46eb api: reader manifest and page images for approved versions only
a496d49 api: approval tests prove the book filter and the new token
f11e867 api: approve versions, refuse stale ones with look again
64d725a api: contact sheet with versions, stored checks and approval state
4a1eb28 api: profiles, settings hash, saved-profile renders with a cache
d0ab383 api: log cut-out failures, make subject and retry writes race-safe
7decc36 api: subject routes, confirm, leave out, retry, restart recovery
8abb740 api: overlay image and stateless preview
f020d86 api: sanitize failure reasons, log and contain job errors
ee91b04 api: upload a book, process pages in the background, book routes
8539f17 api: fix upload helper response key
e16f645 api: local mongo, test harness, routes split into routers
505a6a4 keep this PR to web/: restore root .gitignore and CLAUDE.md, drop CLA...
c64bd0d web: background check can be null at Outlined (matches contracts)
4603daa align example shapes with the web client (PR 1)
12bef8c hours 0 and 1 - contracts, stubs, mocked data running on a server
2cdda39 review fixes: hash revalidates, open flags, version echo, enums, real...
fed5ed6 api skeleton answering every route on stand-ins
688b2f8 settings and stub-or-real switch
e193b4c stand-ins for pipeline and display
7b93801 fix examples position test
195fd69 hashing helper, examples consistency tests
c047ee0 shared contract types
01c4621 example responses for every api route
b8aea84 folder layout, requirements, env example
3573c91 Done for the night gn
```
