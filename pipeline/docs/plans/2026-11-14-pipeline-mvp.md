# Pipeline and Server MVP (Owner A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Bryan's MVP lane: a `pipeline` package that turns a PDF into page images, Gemini subject candidates and cleaned masks behind the five Contract 2 functions, plus the Docker, Compose and Caddy files that serve the API behind a password.

**Architecture:** `pipeline/` is a plain Python package with no database and no web code. It reads and writes files under a book folder (`out_dir/pages`, `out_dir/masks`) and returns the types in `contracts/types.py`. Gemini sits behind `pipeline/gemini.py` and the segmenter behind `pipeline/segment.py`; nothing else imports the Gemini SDK or knows which segmenter is in use. The API loads it with `import pipeline` and reads `pipeline.rasterize`, `pipeline.process_page`, `pipeline.segment_at_point`, `pipeline.mask_from_outline` (see `api/modules.py`).

**Tech Stack:** Python 3.11 in Docker (3.14 in the local `.venv`), PyMuPDF, google-genai, opencv-python-headless, NumPy, Pillow, Pydantic v2, pytest. Docker Compose, Caddy 2.

**Spec:** `Product and technical spec.md` (Part 2: "Contracts", "Implementation: pipeline (Owner A)", "Setup, deploy and early decisions") and `Mirai 24-Hour Build Plan.md` ("Bryan: pipeline and server").

## Global Constraints

- Branch `bryan` only. Run `git branch --show-current` before every commit. Never commit, push or merge to `main`.
- Edit only `pipeline/`, `fixtures/`, `infra/`, root `Dockerfile`, `compose.yaml`, `Caddyfile`, `.env.example`.
- Import contract types from `contracts.types` and hashes from `contracts.hashing` (`hash_bytes`). Both exist; no fallback copy is needed.
- No PyTorch. Never add torch, torchvision, EdgeSAM or SAM 2 to any requirements file.
- `out_dir` is the book folder. Masters are `out_dir/pages/{n}.png` (RGB, longer side at most 3000 px), working copies `out_dir/pages/{n}_view.png` (longer side 1600 px), masks `out_dir/masks/{n}_{hash}.png` (8-bit, one channel, master size, 255 = subject). `{n}` for a mask is `Path(image_path).stem`.
- A mask file is never overwritten: if the path exists, leave it.
- Every coordinate passed in or out of the five contract functions is in master pixels from the top-left corner.
- The Gemini key is read only from the environment (`GEMINI_API_KEY`, `GEMINI_MODEL`). Never print, log or commit it. Stage named files, never `git add .`.
- **No Gemini call is made until Andrew says so.** Steps marked LIVE wait for that. Unit tests mock `pipeline.gemini`.
- Tests live in `pipeline/tests/` and run from the repo root with `.venv/bin/python -m pytest pipeline/tests -q`.
- After every commit, append a What/How/Notes entry to `CLAUDE_NOTES.md` (git-ignored) in the format in `CLAUDE.md`, with measured numbers where they exist.
- Deploying to the server (`140.82.15.107`) and pushing to `origin/bryan` each need Andrew's go-ahead at the time.

## Review Focus

1. A PDF page with a `/Rotate` of 90 or 270: the master must be upright and its `width`/`height` must be the rotated ones. Tested in Task 1.
2. Gemini returns a box that is reversed, off the page, or zero-area: the converter must clamp and order it, and a candidate whose mask comes out empty is dropped, not returned. Tested in Tasks 5 and 6.
3. Two candidates on one page that produce byte-identical masks: both get the same `mask_path` and the second save must not fail or rewrite the file. Tested in Task 2.
4. An outline with points outside the page, or fewer than 3 points: clip to the page; fewer than 3 raises `ValueError` (same as `api/stubs.py`). Tested in Task 3.
5. A click on flat background where the segmenter finds nothing: `segment_at_point` falls back to the stub rectangle around the click so the teacher still gets a mask to see. Tested in Task 7.

---

### Task 1: Setup and `rasterize` (A1)

**Files:**
- Modify: `pipeline/requirements.txt`
- Create: `pipeline/__init__.py`, `pipeline/rasterize.py`, `pipeline/README.md`, `pipeline/tests/__init__.py`, `pipeline/tests/conftest.py`, `pipeline/tests/test_rasterize.py`

**Interfaces:**
- Produces: `rasterize(pdf_path, out_dir) -> list[PageAsset]`, re-exported from `pipeline/__init__.py`. Constants `MASTER_MAX = 3000`, `VIEW_MAX = 1600`, `DPI = 300`.
- Produces (test helpers in `conftest.py`): fixture `make_pdf(tmp_path)` returning a function `make_pdf(pages: list[dict]) -> Path`, where each dict has `size=(w_pt, h_pt)`, optional `text`, `rotate`, `image_px` (draws one embedded image of that pixel size covering the page). Fixture `page_image(tmp_path)` that writes a 1200×900 white master with a filled red ellipse at centre (600, 450), radii (200, 150), under `tmp_path/pages/1.png`, and returns its path. A `live` marker, skipped unless `RUN_LIVE=1`.

- [ ] **Step 1:** Set `pipeline/requirements.txt` to `pymupdf`, `google-genai`, `opencv-python-headless`, `numpy`, `pillow`, `pydantic>=2,<3`, `pytest`. Install into `.venv`. Verify: `.venv/bin/python -c "import fitz, cv2, google.genai"` exits 0.
- [ ] **Step 2: Write failing tests** in `test_rasterize.py`, each on a PDF built by `make_pdf`:
  - `test_paths_and_sizes`: a 612×792 pt page gives `pages/1.png` with longer side exactly 3000 (300 DPI gives 3300, capped), mode RGB, and `pages/1_view.png` with longer side 1600; `asset.width, asset.height` equal the master's size; `page_number == 1`.
  - `test_small_page_is_not_upscaled`: a 360×360 pt page gives a 1500×1500 master.
  - `test_text_layer`: a page with text "The rabbit sat." gives `text_source == "layer"` and that text (stripped); a page with none gives `text == ""` and `"none"`.
  - `test_rotation_applied`: a 612×792 page with `rotate=90` gives `width > height`.
  - `test_spread_flag`: 1600×800 pt gives `"spread"` in flags; 1500×800 does not (ratio 1.875).
  - `test_low_quality_flag`: one embedded 800×600 image gives `"low_quality"`; one 1200×900 image does not; a text-only page does not.
- [ ] **Step 3:** Run the tests; expect import errors.
- [ ] **Step 4: Implement `rasterize`.** Render with `page.get_pixmap(dpi=300, alpha=False)` (PyMuPDF applies `/Rotate`); if the longer side exceeds 3000, resize with Pillow LANCZOS. The view is a LANCZOS resize of the master, never larger than the master. Text is `page.get_text().strip()`. `low_quality` is set when `page.get_images(full=True)` has exactly one entry and the longer of its own width and height is under 1000.
- [ ] **Step 5:** Run the tests; expect all pass.
- [ ] **Step 6:** Write `pipeline/README.md`: install, run tests, and a "Gemini findings" section with three empty rows (model name, box format, four-at-once result) to be filled in Task 5.
- [ ] **Step 7:** Commit `pipeline/` files: `Add rasterize with page flags and text layer`. Log.
- [ ] **Step 8 (needs the PDFs):** Rasterize the demo PDF to the scratchpad, pick six varied pages (one subject, two named animals, a scene, a text-heavy page, a spread or cover if there is one), and copy them to `fixtures/pages/{n}.png`, `{n}_view.png`, plus `fixtures/pages.json` (the six `PageAsset`s with repo-relative paths) and `fixtures/CREDITS.md` (title, author, illustrator, licence, source URL). If the six masters total more than 40 MB, stop and ask before committing. Commit: `Add six fixture pages from the demo book`. Log with page sizes and rasterize seconds per page.

### Task 2: Mask helpers

**Files:**
- Create: `pipeline/masks.py`, `pipeline/tests/test_masks.py`

**Interfaces:**
- Produces, all on `np.ndarray` of dtype `uint8` with values 0 or 255:
  - `clean_mask(mask) -> np.ndarray`
  - `save_mask(mask, image_path, out_dir) -> tuple[str, str]` returning `(mask_path, mask_hash)`
  - `polygon_mask(points, width, height) -> np.ndarray`
  - `mask_box(mask) -> tuple[float, float, float, float] | None` as `(x0, y0, x1, y1)`; `None` for an empty mask
  - `iou(a, b) -> float`; 0.0 when both are empty

- [ ] **Step 1: Write failing tests:**
  - `test_clean_keeps_largest_and_big_regions`: on 1000×1000, blobs of area 10000, 600 and 400 leave the first two (600 is at least 5% of 10000; 400 is not).
  - `test_clean_fills_small_holes_only`: in a 400×400 blob on 1000×1000, a 20×20 hole (400 px, under 0.1% of 1,000,000 = 1000) is filled and a 50×50 hole (2500 px) stays.
  - `test_clean_empty_mask_stays_empty`.
  - `test_save_mask_format_and_name`: the file is at `out_dir/masks/1_{hash}.png` for `image_path` `.../pages/1.png`, opens as mode `L` at the same size, `hash == hash_bytes(file bytes)` and is 12 hex characters.
  - `test_save_mask_never_overwrites`: saving the same mask twice returns the same path and leaves the file's mtime unchanged.
  - `test_polygon_mask_clips_to_page` and `test_iou` (identical 1.0, disjoint 0.0, both empty 0.0).
- [ ] **Step 2:** Run; expect failures.
- [ ] **Step 3: Implement.** `clean_mask` uses `cv2.connectedComponentsWithStats` (8-connectivity) on the mask for regions and on its inverse for holes; a hole is a background component that does not touch the image border. `save_mask` encodes with `cv2.imencode(".png", mask)`, hashes those bytes with `contracts.hashing.hash_bytes`, and writes only if the path does not exist. `polygon_mask` uses `cv2.fillPoly` on rounded integer points.
- [ ] **Step 4:** Run; expect pass. Commit: `Add mask cleanup, hashing save and polygon fill`. Log.

### Task 3: `mask_from_outline`, raw path (A6a, demo safety net)

**Files:**
- Create: `pipeline/outline.py`, `pipeline/tests/test_outline.py`
- Modify: `pipeline/__init__.py`

**Interfaces:**
- Consumes: `polygon_mask`, `save_mask` from Task 2.
- Produces: `mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate`. `points` is a list of `(x, y)` in master pixels.

- [ ] **Step 1: Write failing tests** using `page_image`:
  - `test_polygon_used_exactly`: a triangle gives a mask equal to `polygon_mask(points, 1200, 900)`, `source == "manual"`, `confidence == 1.0`, `label` as passed, `synonyms == []`, `box` equal to the points' min and max clipped to the page.
  - `test_fewer_than_three_points_raises_value_error`.
  - `test_works_with_gemini_and_segmenter_off`: with `GEMINI_API_KEY` removed from the environment, `SEGMENTER=edgesam`, and `pipeline.segment.segment` monkeypatched to raise `AssertionError`, `tidy=False` still returns the polygon mask. Also assert that importing `pipeline.outline` does not import `google.genai` (`"google.genai" not in sys.modules` in a fresh subprocess).
- [ ] **Step 2:** Run; expect failures.
- [ ] **Step 3: Implement** the `tidy=False` path. Read the image size with Pillow without decoding pixels. Leave `tidy=True` falling through to the raw polygon for now with a comment naming Task 4. `pipeline/__init__.py` must import `outline` without importing `gemini` at module load: `gemini.py` (Task 5) imports the SDK inside its functions.
- [ ] **Step 4:** Run; expect pass. Commit: `Add mask_from_outline with no model call`. Log.

### Task 4: Segmenter and tidy outlines

**Files:**
- Create: `pipeline/segment.py`, `pipeline/tests/test_segment.py`
- Modify: `pipeline/outline.py`, `pipeline/tests/test_outline.py`, `.env.example`

**Interfaces:**
- Produces: `segment(image, box=None, points=None) -> np.ndarray`. `image` is an RGB `uint8` array at master size; `box` is `(x0, y0, x1, y1)` in master pixels; `points` is a list of `(x, y)` positive points. Returns a raw (uncleaned) `uint8` mask at the image's size, 0 or 255. Raises `ValueError` if both `box` and `points` are `None`.
- Produces: `point_box(x, y, width, height) -> tuple` — the box used when only a point is given: half-size 20% of the longer side, clipped to the page.
- `SEGMENTER` is read on every call (so tests can switch it): `stub`, `grabcut` (default when unset or empty), `edgesam`, `sam2`. Any other value raises `ValueError`.

- [ ] **Step 1: Write failing tests** on the `page_image` ellipse (read as an array):
  - `test_stub_fills_box`: `SEGMENTER=stub` with box (100, 100, 300, 200) gives exactly that rectangle.
  - `test_stub_point_uses_point_box`.
  - `test_grabcut_finds_ellipse_from_box`: box (350, 250, 850, 650) gives IoU of at least 0.9 with the true ellipse mask.
  - `test_grabcut_from_point`: point (600, 450) gives IoU of at least 0.8 and the mask is 255 at the point.
  - `test_default_is_grabcut` (env var unset), `test_unknown_segmenter_raises`.
  - `test_edgesam_and_sam2_raise_not_implemented`: message is exactly `Bryan: PyTorch segmenter goes here`.
  - `test_output_shape_and_values`: shape equals `image.shape[:2]`, dtype `uint8`, values within {0, 255}.
- [ ] **Step 2:** Run; expect failures.
- [ ] **Step 3: Implement.** GrabCut runs on a copy scaled so the longer side is 1024 (5 iterations), and the result is scaled back with nearest-neighbour; this keeps a 3000 px page to about a second. Box prompt: `cv2.GC_INIT_WITH_RECT`. Any points: build a mask that is `GC_PR_FGD` inside the box (the given box, or `point_box`), `GC_BGD` outside, with a `GC_FGD` disc of radius 1% of the longer side at each point, and use `cv2.GC_INIT_WITH_MASK`. If GrabCut raises (it does on a degenerate box), return an empty mask. The `_edgesam` and `_sam2` functions carry a docstring stating the exact input and output above, that the model must be loaded once and cached at module level, and that the function must return the raw mask without cleanup.
- [ ] **Step 4:** Run; expect pass. Commit: `Add segment() with stub and GrabCut behind SEGMENTER`. Log with GrabCut seconds on a 3000 px image.
- [ ] **Step 5: Write failing tidy tests** in `test_outline.py`, monkeypatching `pipeline.segment.segment`:
  - `test_tidy_uses_segmenter_when_iou_high`: the segmenter returns the polygon shifted by 5 px (IoU above 0.6); the result equals `clean_mask(segmenter mask AND polygon dilated by 12 px)`.
  - `test_tidy_keeps_polygon_when_iou_low`: the segmenter returns a far-away square; the result is the raw polygon.
  - `test_tidy_keeps_polygon_when_segmenter_raises`.
  - `test_tidy_box_is_polygon_bounding_box`: the patched segmenter records its `box` argument.
- [ ] **Step 6: Implement `tidy=True`.** Dilate with a 25×25 elliptical kernel (12 px each way). IoU threshold constant `TIDY_MIN_IOU = 0.6`. `source` stays `manual`, confidence 1.0, and `box` becomes `mask_box` of the final mask.
- [ ] **Step 7:** Run; expect pass. In `.env.example`, change the line to `SEGMENTER=grabcut` and add a comment line above it: `# stub, grabcut, edgesam or sam2`. Commit: `Add tidy outlines through the segmenter`. Log.

### Task 5: Gemini subject choosing (A2)

**Files:**
- Create: `pipeline/gemini.py`, `pipeline/tests/test_gemini.py`, `pipeline/tests/test_live.py`

**Interfaces:**
- Produces:
  - Pydantic models `GeminiCandidate(label: str, synonyms: list[str], box_2d: list[int], confidence: float, reason: str)` and `SubjectAnswer(page_kind: Literal["single", "several", "scene"], candidates: list[GeminiCandidate])`. `box_2d` is `[ymin, xmin, ymax, xmax]` on 0 to 1000.
  - `choose_subjects(view_path, text) -> SubjectAnswer`
  - `label_crop(png_bytes: bytes) -> str` (used in Task 7; returns a lowercase one-to-three-word name)
  - `class GeminiError(Exception)` and `class RateLimited(GeminiError)`. Every SDK or parsing error leaves this module as one of these two.
  - Constants `TIMEOUT_S = 20`, `DEFAULT_MODEL = "gemini-flash-latest"` (used when `GEMINI_MODEL` is empty; replaced by the confirmed name in Step 6), `PROMPT` (below).
- Internal seam for tests: `_generate(parts: list, schema) -> str` is the only function that touches the SDK. Unit tests monkeypatch it.

- [ ] **Step 1: Write failing tests** with `_generate` monkeypatched:
  - `test_parses_answer`: a JSON string with two candidates returns a `SubjectAnswer` with those values.
  - `test_trims_to_three_candidates_and_five_synonyms`: four candidates and seven synonyms come back as three and five; candidates are sorted by confidence, highest first.
  - `test_confidence_clamped_to_0_1`.
  - `test_bad_json_raises_gemini_error`, `test_wrong_box_length_raises_gemini_error`.
  - `test_missing_key_raises_gemini_error`: with `GEMINI_API_KEY` unset and `_generate` not patched, `choose_subjects` raises `GeminiError` whose message does not contain any key text.
  - `test_sdk_429_becomes_rate_limited`: patch the SDK client call inside `_generate` to raise `google.genai.errors.APIError` with code 429; expect `RateLimited`. Code 500 gives `GeminiError`.
- [ ] **Step 2:** Run; expect failures.
- [ ] **Step 3: Implement.** Import `google.genai` inside `_generate`. Call `client.models.generate_content` with the view PNG as `types.Part.from_bytes(data=..., mime_type="image/png")` followed by the prompt text, and `types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=0, http_options=types.HttpOptions(timeout=20_000))`. Check these names against the installed SDK before relying on them. The fixed prompt:

```text
You are helping adapt a picture-book page for a child with cortical visual impairment.
Find the subject of this page: the one object the story is about on this page, not the
largest thing in the picture. Use the page text to decide. If the text says "The rabbit
was hiding under the tree", the subject is the rabbit.

page_kind: "single" if the page is about one object, "several" if it is about two or
more objects of equal importance, "scene" if it is a landscape, a crowd, or has no
object the story is about.

candidates: up to 3, most likely first. For each:
- label: one or two lowercase words, using the word from the page text when there is one.
- synonyms: up to 5 other names, always including the general kind of thing
  (hornbill: bird).
- box_2d: [ymin, xmin, ymax, xmax], integers from 0 to 1000, tight around the whole object.
- confidence: 0 to 1, how sure you are this is the subject.
- reason: one short sentence.

Page text: <<<{text}>>>
```

  An empty page text is sent as `(none)`.
- [ ] **Step 4:** Run; expect pass. Commit: `Add Gemini subject choosing with a JSON schema`. Log.
- [ ] **Step 5: Write the live tests** in `test_live.py`, all marked `live`: `test_one_page_returns_valid_answer` (on `fixtures/pages/1_view.png`) and `test_four_calls_at_once` (a 4-thread pool; records each call's seconds and whether any raised `RateLimited`). They must be collected and skipped without `RUN_LIVE=1`. Commit.
- [ ] **Step 6 (LIVE, needs the go-ahead and the fixture pages):** List the available models and pick the current Flash model; set `DEFAULT_MODEL`. Run one call and draw the returned box on the view image to confirm the `[ymin, xmin, ymax, xmax]` 0-to-1000 reading by eye. Run the four-at-once test. Save answers for three pages to `fixtures/gemini/{n}.json`. Fill the "Gemini findings" rows in `pipeline/README.md` with the model name, box format, per-call seconds and the rate-limit result. Commit: `Record Gemini model, box format and rate-limit findings`. Log.

### Task 6: `process_page` (A5, with A8 failure handling)

**Files:**
- Create: `pipeline/process.py`, `pipeline/tests/test_process.py`
- Modify: `pipeline/__init__.py`

**Interfaces:**
- Consumes: `choose_subjects`, `GeminiError`, `RateLimited` (Task 5); `segment` (Task 4); `clean_mask`, `save_mask`, `mask_box` (Task 2).
- Produces:
  - `process_page(asset, out_dir, force=False) -> PageResult`. Never raises.
  - `gemini_box_to_pixels(box_2d, width, height) -> tuple[float, float, float, float]` — the only place the 0-to-1000 scale is converted. Returns `(x0, y0, x1, y1)`, ordered and clamped to the page.
  - `decide_state(page_kind, candidates, text) -> tuple[str, int | None, str | None]` returning `(state, selected, reason)`. `candidates` are contract `Candidate`s, highest confidence first.
  - `call_with_retry(fn)` — calls `fn()`; on `RateLimited` sleeps `RATE_LIMIT_WAIT_S = 10` and tries once more; on any other `GeminiError` tries once more at once; the second failure propagates. Reused in Task 7.
  - Constants `READY_MIN_CONFIDENCE = 0.7`, `READY_MIN_LEAD = 0.2`.

- [ ] **Step 1: Write failing tests** for the pure functions:
  - `test_box_conversion`: `[100, 200, 500, 600]` on 3000×2000 gives `(600, 200, 1800, 1000)`.
  - `test_box_reversed_and_out_of_range_is_fixed`: `[500, 600, 100, 1200]` on 1000×1000 gives `(600, 100, 1000, 500)`.
  - `decide_state`, one test per rule, in the spec's order:
    - scene gives `no_clear_subject`; no candidates gives `no_clear_subject`.
    - several gives `needs_subject`, even with confidence 0.95 and a text match.
    - single, text "The rabbit sat.", top label "fox" with synonyms ["animal"] gives `needs_subject`.
    - a synonym match counts: text "A bird flew.", label "hornbill", synonyms ["bird"], confidences 0.9 and 0.3 gives `ready`, `selected == 0`.
    - plural and case: text "Rabbits hide." matches label "rabbit".
    - no text at all skips the text rule: confidences 0.9 and 0.3 give `ready`.
    - confidence 0.69 gives `needs_subject`; 0.8 against 0.65 gives `needs_subject`; a single candidate at 0.7 gives `ready`.
    - `selected` is `None` for every state but `ready`; `reason` is `None` for `ready` and a short sentence otherwise.
- [ ] **Step 2: Write failing tests** for `process_page`, with `pipeline.process.choose_subjects` monkeypatched, `SEGMENTER=stub`, and `time.sleep` patched out, on the `page_image` asset:
  - `test_spread_is_unsupported_without_force`: flags `["spread"]` gives `unsupported`, no candidates, and `choose_subjects` is not called. With `force=True` it is called.
  - `test_ready_page_has_masks_on_disk`: each candidate's `mask_path` exists, is master size, `source == "auto"`, `mask_hash` matches the file, `box` is in master pixels.
  - `test_empty_mask_candidate_is_dropped`: a zero-area box (with the stub) drops that candidate; if none remain the state is `no_clear_subject`.
  - `test_rate_limit_retries_once_then_succeeds`: first call raises `RateLimited`, second returns; state is not `failed`; sleep was called once with 10.
  - `test_second_failure_is_failed_with_reason`: two `GeminiError("timed out")` give `failed`, `candidates == []`, a non-empty `reason`.
  - `test_any_exception_is_failed_not_raised`: `segment` raising `RuntimeError` gives `failed`; a missing `image_path` gives `failed`.
  - `test_reason_never_contains_the_key`: with `GEMINI_API_KEY=secret123` and an error whose text includes `secret123`, the reason does not.
- [ ] **Step 3:** Run; expect failures.
- [ ] **Step 4: Implement.** Text match: lowercase, and for the label and each synonym test `\b{term}(s|es)?\b` against the page text. Load the master once with `cv2.imread` and convert to RGB. The whole body sits in one `try`; the `except Exception` branch builds the `failed` result with `reason` set to the exception class name plus its message, truncated to 200 characters and with the key value removed.
- [ ] **Step 5:** Run; expect pass. Commit: `Add process_page with state rules and failure handling`. Log.
- [ ] **Step 6 (LIVE, needs the go-ahead and the fixture pages):** Add `test_six_fixture_pages_each_get_a_state` to `test_live.py`: every page returns one of the five states, at least one is `needs_subject`, none raises. Run it. If no page is `needs_subject`, look at the answers before touching thresholds, and tune only on these six pages. Commit. Log the count of pages in each state and seconds per page.

### Task 7: `segment_at_point` (A6b) and `refine_mask` (P1)

**Files:**
- Create: `pipeline/click.py`, `pipeline/tests/test_click.py`
- Modify: `pipeline/__init__.py`

**Interfaces:**
- Consumes: `segment`, `point_box`; `clean_mask`, `save_mask`, `mask_box`; `label_crop`; `call_with_retry`.
- Produces: `segment_at_point(image_path, x, y, out_dir) -> Candidate` and `refine_mask(image_path, mask_path, x, y, out_dir) -> Candidate`.

- [ ] **Step 1: Write failing tests** with `pipeline.click.label_crop` monkeypatched:
  - `test_click_returns_mask_and_label`: click (600, 450) on the ellipse with `SEGMENTER=grabcut` gives `source == "click"`, `label == "ball"` (from the patch), a mask covering the click, `confidence == 1.0`, `synonyms == []`.
  - `test_click_label_empty_when_gemini_fails`: `label_crop` raising `GeminiError` twice gives `label == ""` and still a mask.
  - `test_click_on_background_falls_back_to_rectangle`: `segment` patched to return an empty mask gives the `point_box` rectangle as the mask.
  - `test_crop_sent_to_gemini_is_the_mask_box`: the PNG passed to `label_crop` decodes to the size of the mask's box plus 8% padding, clipped to the page.
  - `test_refine_adds_region_and_keeps_old_file`: start from a mask of the left half of the ellipse and refine at a point in the right half; the new mask contains the point, the returned `mask_path` differs from the old one, and the old file's bytes are unchanged.
  - `test_refine_prompt_is_old_box_grown_to_the_point`: the patched `segment` receives the old mask's box grown to include `point_box` at 5% half-size, and `points == [(x, y)]`.
- [ ] **Step 2:** Run; expect failures.
- [ ] **Step 3: Implement.** `refine_mask` has no access to the original Gemini box, so the old mask's bounding box stands in for "the original prompt". Its result is the cleaned union of the old mask and the new segmentation, so a refine click can only add. `refine_mask` returns `label == ""`, `source == "click"`, confidence 1.0; the API keeps the page's existing label.
- [ ] **Step 4:** Run; expect pass. Commit: `Add click-to-pick and click-to-refine`. Log.

### Task 8: Book runner

**Files:**
- Create: `pipeline/run_book.py`, `pipeline/tests/test_run_book.py`
- Modify: `pipeline/README.md`

**Interfaces:**
- Produces: `run_book(pdf_path, out_dir, concurrency=4) -> dict` and the CLI `python -m pipeline.run_book <pdf> <out_dir>`. It copies the PDF to `out_dir/source.pdf`, and writes `out_dir/summary.json`: `{"pdf", "pages": [{"page_number", "state", "page_kind", "reason", "seconds", "flags", "candidates": [...], "selected"}], "counts": {state: n}, "total_seconds"}`.

- [ ] **Step 1: Write failing tests** with `pipeline.run_book.process_page` patched: a 3-page `make_pdf` book gives a summary with three pages in order, correct `counts`, `source.pdf` present; one page whose patched `process_page` returns `failed` does not stop the others; the CLI exits 0 and prints one line per page with state, reason and seconds.
- [ ] **Step 2:** Run; expect failures. Implement with `concurrent.futures.ThreadPoolExecutor(max_workers=concurrency)`; load `.env` from the repo root if present, without printing it (parse `KEY=VALUE` lines by hand; no new dependency).
- [ ] **Step 3:** Run; expect pass. Add a "Run a whole book" section to the README. Commit: `Add run_book to process a PDF from the command line`. Log.
- [ ] **Step 4 (LIVE, needs the go-ahead and the PDF):** Run the demo book. Log pages per state, seconds per page and whether four at once hit a rate limit.

### Task 9: Dockerfile, Compose and Caddy (A4, A7)

**Files:**
- Create: `Dockerfile`, `compose.yaml`, `Caddyfile`, `infra/caddy.Dockerfile`, `infra/DEPLOY.md`, `.dockerignore` is **not** created (not in the allowed list; say so in the report if build context size is a problem)
- Modify: `.env.example`

**Interfaces:**
- `Dockerfile`: `python:3.11-slim`. Copies every `*/requirements.txt` first, installs them in one `pip install` with one `-r` per file found by a shell glob, then copies the repo. `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- `compose.yaml`: service `api` (build `.`, `env_file: .env`, `./data:/app/data`, `DATA_DIR=/app/data`, `restart: unless-stopped`, no published port) and service `caddy` (build `infra/caddy.Dockerfile` with the repo as context, ports 80 and 443, `env_file: .env`, volumes for the `Caddyfile` and named volumes `caddy_data`, `caddy_config`).
- `infra/caddy.Dockerfile`: a `node:20` stage runs `npm ci && npm run build` in `web/` with `VITE_API_URL` as a build argument; the final `caddy:2` stage copies `web/dist` to `/srv`. It starts Caddy through a shell line that sets `SITE_PASSWORD_HASH` from `caddy hash-password --plaintext "$SITE_PASSWORD"` and then runs `caddy run`, so the plain password lives only in `.env`.
- `Caddyfile`: site address `{$SITE_ADDRESS:localhost}`; `basic_auth` on every path with `{$SITE_USER} {$SITE_PASSWORD_HASH}`; `request_body max_size 55MB`; `/api/*` to `api:8000`; everything else served from `/srv` with `try_files {path} /index.html`.
- `.env.example` gains `SITE_ADDRESS=` with the comment `# e.g. 140-82-15-107.sslip.io; empty means localhost`.

- [ ] **Step 1:** Write the five files. `infra/DEPLOY.md` lists: the server `.env` names to fill, the deploy command (`cd /opt/mirai && git pull && docker compose up -d --build`), how to check it, and how to roll back (`git checkout <previous commit> && docker compose up -d --build`).
- [ ] **Step 2: Verify locally.** `docker compose config` exits 0. `docker compose build` succeeds; any pip conflict between the requirements files is reported to the owner of that folder, not fixed in their file. With `SITE_USER=test`, `SITE_PASSWORD=test` and a reachable `MONGODB_URI` in a throwaway env file: `curl -k -s -o /dev/null -w "%{http_code}" https://localhost/api/books` prints `401`, and with `-u test:test` prints `200`. `docker compose down` afterwards.
- [ ] **Step 3:** Commit: `Add Dockerfile, Compose and Caddy with a site password`. Log with image size and build time.
- [ ] **Step 4 (needs Andrew):** Andrew creates `/opt/mirai/.env` on the server. With his go-ahead: push `bryan`, then run the deploy command over SSH, then check that `https://140-82-15-107.sslip.io` answers 401 without the password and 200 with it.

### Task 10: Final check and report

- [ ] **Step 1:** Run the whole suite: `.venv/bin/python -m pytest pipeline/tests -q`; expect all pass and the live tests skipped. Run `api/` and `contracts/` tests too, to confirm nothing outside `pipeline/` broke.
- [ ] **Step 2:** `PIPELINE=real .venv/bin/python -c "import api.modules"` exits 0, which proves the four names the API expects exist on the package.
- [ ] **Step 3:** `git diff --stat origin/main...bryan` shows changes only in the allowed folders and files (plus the `CLAUDE.md` and `.gitignore` merge resolution).
- [ ] **Step 4:** Report: what is done, every LIVE step still waiting, what Bryan must do for `edgesam`/`sam2`, and what is needed from teammates.
