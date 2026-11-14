# Overnight API Build (hours 2 to 14, on stand-ins) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the example-answering API skeleton with the real MVP API (upload, subjects, profiles, approval, reader, second look, demo reset), running on the stand-in pipeline and display, with every rule proven by tests.

**Architecture:** FastAPI routers in `api/routes/`, one per area, over five MongoDB collections. Three small modules hold the rules every route shares: `coords.py` (the only fraction-to-pixel conversion), `views.py` (the only database-to-JSON conversion) and `versions.py` (the only place a version token or an approval is decided). Background work runs in-process through FastAPI `BackgroundTasks` and a thread pool.

**Tech Stack:** Python (the repo `.venv`), FastAPI, Pydantic v2, PyMongo, PyMuPDF (page count only), Pillow, pytest. Local MongoDB in Docker.

**Spec:** `Product and technical spec.md`, Part 2 (Contracts; "Implementation: API and data"). Schedule and scope: `Mirai 24-Hour Build Plan.md`, Andrew's MVP table, hours 2 to 14. Response shapes: `contracts/examples.json`.

## Global Constraints

- Edit only `api/` and `contracts/`. Never edit `web/`, `pipeline/`, `render/`, `checks/`, `tests/`, `fixtures/`, `infra/` or any root file. If one of them needs a change, write it in `api/docs/overnight-notes.md` and move on.
- Contracts are frozen. Do not change `contracts/types.py`, `contracts/hashing.py` or `contracts/examples.json`. A response may carry extra fields; it may never drop or rename one that an example shows.
- MVP only. No `refine_point`, no `tidy=True`, no `/eval/summary`, no `api/tools/reapprove.py`, no render-version or switch-back approval tests (those are hour 17).
- `PIPELINE` and `RENDER` stay `stub`. Call the modules only as `modules.pipeline.<fn>` and `modules.display.<fn>`, never `api.stubs` directly.
- Database: local MongoDB in Docker. Never connect to Atlas. The database name comes from the path of `MONGODB_URI`, default `mirai`. No new setting names.
- Positions crossing HTTP are fractions from 0 to 1 from the top-left corner. Everything stored and everything passed to the pipeline is in master pixels. `api/coords.py` is the only file that converts.
- Every image response is WebP with `Cache-Control: no-store`.
- `mask_path` and every other server path never appear in a response.
- Never call a page "verified". The reader serves approved versions only.
- Ids are MongoDB ObjectIds sent as strings. A malformed or unknown id is a 404, except on `GET /reader/page/...`, where every refusal is a 403.
- Run all commands from the repo root. Tests: `.venv/bin/python -m pytest api contracts -q`. All of them must pass before each commit.
- Commit after every task, on branch `andrew`, with only `api/` and `contracts/` paths staged. Do not push, merge or open a pull request.
- `main` must always start: after each task, `.venv/bin/python -c "import api.main"` exits 0.

## Decisions the spec leaves open

These were chosen for this plan. Each is listed in `api/docs/overnight-notes.md` by Task 12 so Andrew can overrule one in the morning.

1. **Upload limits answer 413** with a plain `detail`. A file that is not a readable PDF answers 400.
2. **A subject can be set on any page that is not Processing** (409 if it is). Setting one makes the page `ready` and clears `confirmed` when `subject_hash` changes.
3. **Retry is allowed only from `failed` and `unsupported`** (409 otherwise). `unsupported` needs `force: true`.
4. **`confirm-all` confirms pages that are `ready`, have a subject, and are not omitted or already confirmed**, and returns exactly the pages it confirmed.
5. **A page has a version only when it has a subject, is confirmed and is not omitted.** Otherwise its version is null on the sheet and the reader refuses it.
6. **`GET /render/...` answers 409 when `v` is sent and is not the current token**, so a sheet never shows a picture that differs from what it will approve.
7. **`GET /pages/{id}/overlay` with no subject selected returns the working copy unchanged**, so the review grid still shows the page.
8. **A version is "fully approved"** when the book has at least one approved page and every page is either omitted or has a decision (approve or reject) on its current version.
9. **Reader `versions` lists** each profile at its own level, plus every other (profile, level) pair that has an approval record on this book.
10. **Demo reset** restores each page to what the pipeline last returned, using `auto_state`, `auto_subject_hash` and `auto_reason` saved when a result lands.

## Review Focus

1. **A page changes between sheet load and approve.** The teacher expects "look again", never a silent approval of something they did not see. Pinned in Task 7, `test_stale_version_is_refused_and_not_recorded`.
2. **A page is omitted or unconfirmed after it was approved.** The child must not see it. Pinned in Task 8, `test_approved_then_changed_is_refused[omitted]` and `[subject]`.
3. **A second-look result lands after the teacher picked a different subject.** The old answer must not attach to the new subject. Pinned in Task 9, `test_late_result_for_an_old_subject_is_discarded`.
4. **An upload that is not a PDF, or a click or outline outside 0 to 1.** The teacher expects a refusal with a reason, not a 500 or a mask off the page. Pinned in Task 2, `test_not_a_pdf_is_refused`, and Task 4, `test_positions_outside_the_page_are_refused`.
5. **A pipeline or display function raises.** One page fails with a reason; the book and the server carry on. Pinned in Task 2, `test_a_raising_page_fails_alone`, and Task 4, `test_pipeline_error_on_click_leaves_the_page_unchanged`.

## File structure

| File | Responsibility |
| --- | --- |
| `api/db.py` | Mongo client, the five collections, `oid()`, indexes |
| `api/coords.py` | Fractions to master pixels and back. The only converter |
| `api/views.py` | Database documents to Contract 1 JSON. The only serializer |
| `api/jobs.py` | Ingest, page processing, second look, startup recovery |
| `api/versions.py` | Current version of a page for a child and look; approval state |
| `api/images.py` | Image response, render cache |
| `api/routes/books.py` `pages.py` `profiles.py` `approval.py` `reader.py` | One router per area |
| `api/main.py` | App, startup recovery, router includes |
| `api/tools/second_look.py` `reset_demo.py` | Commands |
| `api/joining/` | Thomas's typed client run against the live API |
| `api/tests/` | One test file per task, plus `helpers.py` |

Database documents (all ids are ObjectIds; `page.book_id` and `approval.profile_id` are stored as ObjectIds):

```text
books      title, credits{author,illustrator,publisher,source,license}, state, page_count, created_at
pages      book_id, number, image_path, view_path, width, height, text, flags, state, reason, page_kind,
           candidates[] (Candidate.model_dump(): master pixels, with mask_path), selected, subject_hash,
           confirmed, omitted, processing_started_at, auto_state, auto_subject_hash, auto_reason,
           second_look{subject_hash,status,answer,detail} | None
profiles   name, level, settings, settings_hash, contrast_override_note
checks     page_id, subject_hash, settings_hash, level, render_version, result
approvals  page_id, profile_id, subject_hash, settings_hash, level, render_version, decision, at
```

---

### Task 1: Database, test harness and the split into routers

**Files:**
- Create: `api/db.py`, `api/images.py`, `api/routes/__init__.py`, `api/routes/books.py`, `api/routes/pages.py`, `api/routes/profiles.py`, `api/routes/approval.py`, `api/routes/reader.py`, `api/tests/helpers.py`, `api/tests/test_db.py`, `api/docs/overnight-notes.md`
- Modify: `api/main.py`, `api/tests/conftest.py`, `api/requirements.txt`

**Interfaces:**
- Produces:
  - `api.db`: `books`, `pages`, `profiles`, `checks`, `approvals` (PyMongo collections); `oid(value: str) -> ObjectId` raising `HTTPException(404, "not found")` on a malformed id; `ensure_indexes() -> None`.
  - `api.images.image(data: bytes) -> Response` (moved from `main.py`, unchanged).
  - `api.routes.<area>.router`, each an `APIRouter(prefix="/api")`.
  - `api.tests.helpers`: `client` (a `TestClient`), `make_pdf(pages: int = 3) -> bytes`, `upload(pages: int = 3) -> dict` (posts a PDF and returns `GET /api/books/{id}` once ingest has run).
  - Fixture `clean_db` (autouse): empties all five collections before each test.

- [ ] **Step 1: Start MongoDB and install packages**

```bash
docker run -d --name mirai-mongo -p 127.0.0.1:27017:27017 mongo:7
```

Add `pymupdf` to `api/requirements.txt`, then `.venv/bin/python -m pip install -r api/requirements.txt`.
Expected: `docker ps` lists `mirai-mongo`; `.venv/bin/python -c "import fitz, pymongo"` exits 0. If the container name is taken, `docker start mirai-mongo`.

- [ ] **Step 2: Write the failing test** in `api/tests/test_db.py`

```python
import pytest
from bson import ObjectId
from fastapi import HTTPException

from api import db


def test_tests_use_a_throwaway_database():
    assert db.books.database.name.startswith("mirai_test_")


def test_oid_accepts_a_real_id_and_refuses_a_bad_one():
    real = ObjectId()
    assert db.oid(str(real)) == real
    with pytest.raises(HTTPException) as e:
        db.oid("b1")
    assert e.value.status_code == 404


def test_each_test_starts_empty():
    assert db.books.count_documents({}) == 0
    db.books.insert_one({"title": "x"})
```

- [ ] **Step 3: Run it.** `.venv/bin/python -m pytest api/tests/test_db.py -q`. Expected: FAIL, `cannot import name 'db'`.

- [ ] **Step 4: Implement**

- `api/db.py`: `MongoClient(settings.MONGODB_URI or "mongodb://localhost:27017/mirai", serverSelectionTimeoutMS=2000)`, database from `client.get_default_database(default="mirai")`. Indexes: `pages (book_id, number)`, `checks (page_id, subject_hash, settings_hash, level, render_version)`, `approvals (page_id, profile_id, at)`.
- `api/tests/conftest.py`: before any `api` import, also set `MONGODB_URI=mongodb://localhost:27017/mirai_test_<8 random hex>`. Add the autouse `clean_db` fixture, and a session-end fixture that drops the database. If the server cannot be reached, fail the session with: `MongoDB is not running. Start it: docker start mirai-mongo`.
- `api/tests/helpers.py`: `make_pdf` builds a PDF with PyMuPDF (`fitz.open()`, `new_page(width=800, height=600)`, one line of text per page).
- Move each route function from `api/main.py` into its router file, unchanged, still answering with examples. `main.py` keeps the app, `EXAMPLES`, `example()`, and includes the five routers. `stub_page` and `stub_render` move to `api/images.py`.
- Create `api/docs/overnight-notes.md` with headings `Decisions`, `Needed from other owners`, `Not done`.

- [ ] **Step 5: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass, including the existing 54.

- [ ] **Step 6: Commit**

```bash
git add api && git commit -m "api: local mongo, test harness, routes split into routers"
```

---

### Task 2: Take in a book (upload, background processing, book routes)

**Files:**
- Create: `api/coords.py`, `api/views.py`, `api/jobs.py`, `api/tests/test_coords.py`, `api/tests/test_books.py`
- Modify: `api/routes/books.py`, `api/settings.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `api.db`, `modules.pipeline.rasterize(pdf_path, out_dir) -> list[PageAsset]`, `modules.pipeline.process_page(asset, out_dir, force=False) -> PageResult`. `out_dir` is the book folder `settings.DATA_DIR / "books" / str(book_id)`.
- Produces:
  - `api.settings.MAX_UPLOAD_BYTES = 50 * 1024 * 1024`, `MAX_UPLOAD_PAGES = 30` (constants, not environment settings).
  - `api.coords.to_pixels(point: Sequence[float], width: int, height: int) -> tuple[float, float]`
  - `api.coords.box_to_fractions(box: Sequence[float], width: int, height: int) -> list[float]` (rounded to 4 places)
  - `api.views.page_json(page: dict) -> dict`, `api.views.book_json(book: dict, pages: list[dict]) -> dict`: exactly the keys of the `GET /api/books/{id}` example. Candidates lose `mask_path` and get a fraction `box`. `second_look` is `{status, answer, detail}` only when its `subject_hash` equals the page's; otherwise null. `created_at` is ISO 8601 UTC ending in `Z`.
  - `api.jobs.book_dir(book_id) -> Path`
  - `api.jobs.ingest_book(book_id: ObjectId) -> None`
  - `api.jobs.process_one(page_id: ObjectId, force: bool = False) -> None`
  - `api.jobs.apply_result(page: dict, result: PageResult) -> None`
  - Routes: `POST /api/books`, `GET /api/books`, `GET /api/books/{id}`, `PATCH /api/books/{id}`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_coords.py`:

```python
import pytest
from api import coords


def test_fraction_to_master_pixels():
    assert coords.to_pixels((0.5, 0.1), 3000, 2250) == (1500.0, 225.0)


def test_box_to_fractions():
    assert coords.box_to_fractions((900, 900, 1800, 1800), 3000, 2250) == [0.3, 0.4, 0.6, 0.8]


@pytest.mark.parametrize("point", [(-0.01, 0.5), (0.5, 1.01), (float("nan"), 0.5)])
def test_outside_the_page_is_refused(point):
    with pytest.raises(ValueError):
        coords.to_pixels(point, 3000, 2250)
```

`api/tests/test_books.py` (uses `client`, `make_pdf`, `upload` from `helpers`):

```python
def test_upload_answers_at_once_then_pages_reach_states():
    r = client.post("/api/books", files={"file": ("b.pdf", make_pdf(), "application/pdf")},
                    data={"title": "Animal Homes", "credits": '{"author": "A. Author"}'})
    assert r.status_code == 200 and r.json()["state"] == "ingesting"
    book = client.get(f"/api/books/{r.json()['book_id']}").json()
    assert (book["state"], book["page_count"], book["title"]) == ("ready", 3, "Animal Homes")
    assert book["credits"] == {"author": "A. Author", "illustrator": None, "publisher": None,
                               "source": None, "license": None}
    assert [p["state"] for p in book["pages"]] == ["ready", "needs_subject", "failed"]
    assert book["pages"][2]["reason"] == "stub failure"


def test_page_json_matches_the_example_shape_and_hides_paths():
    page = upload()["pages"][0]
    example = EX["GET /api/books/{id}"]["response"]["pages"][0]
    assert set(page) >= set(example)
    assert set(page["candidates"][0]) == set(example["candidates"][0])   # no mask_path
    assert page["candidates"][0]["box"] == [0.3, 0.4, 0.6, 0.8]
    assert page["subject_hash"] == page["candidates"][0]["mask_hash"]
    assert (page["selected"], page["confirmed"], page["omitted"]) == (0, False, False)
    assert "mask_path" not in json.dumps(page) and str(settings.DATA_DIR) not in json.dumps(page)


def test_title_defaults_to_the_file_name():
    r = client.post("/api/books", files={"file": ("animal homes.pdf", make_pdf(1), "application/pdf")})
    assert client.get(f"/api/books/{r.json()['book_id']}").json()["title"] == "animal homes"


def test_over_30_pages_is_refused():
    r = client.post("/api/books", files={"file": ("b.pdf", make_pdf(31), "application/pdf")})
    assert r.status_code == 413 and "30 pages" in r.json()["detail"]
    assert db.books.count_documents({}) == 0


def test_over_the_size_limit_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 100)
    r = client.post("/api/books", files={"file": ("b.pdf", make_pdf(), "application/pdf")})
    assert r.status_code == 413 and "50 MB" in r.json()["detail"]


def test_not_a_pdf_is_refused():
    r = client.post("/api/books", files={"file": ("b.pdf", b"hello", "application/pdf")})
    assert r.status_code == 400 and db.books.count_documents({}) == 0


def test_bad_credits_json_is_refused():
    r = client.post("/api/books", files={"file": ("b.pdf", make_pdf(1), "application/pdf")},
                    data={"credits": "{not json"})
    assert r.status_code == 422


def test_pages_are_processing_while_the_pipeline_runs(monkeypatch):
    seen = []
    real = modules.pipeline.process_page
    def spy(asset, out_dir, force=False):
        page = db.pages.find_one({"number": asset.page_number})
        seen.append((page["state"], page["processing_started_at"] is not None,
                     db.books.find_one()["state"]))
        return real(asset, out_dir, force)
    monkeypatch.setattr(modules.pipeline, "process_page", spy)
    upload()
    assert seen == [("processing", True, "ready")] * 3


def test_a_raising_page_fails_alone(monkeypatch):
    real = modules.pipeline.process_page
    def flaky(asset, out_dir, force=False):
        if asset.page_number == 1:
            raise RuntimeError("boom")
        return real(asset, out_dir, force)
    monkeypatch.setattr(modules.pipeline, "process_page", flaky)
    pages = upload()["pages"]
    assert (pages[0]["state"], pages[0]["reason"]) == ("failed", "boom")
    assert pages[1]["state"] == "needs_subject"


def test_rasterize_failure_fails_the_book(monkeypatch):
    monkeypatch.setattr(modules.pipeline, "rasterize", lambda *a: 1 / 0)
    book = upload()
    assert (book["state"], book["pages"]) == ("failed", [])


def test_list_patch_and_unknown_book():
    book = upload()
    assert [b["id"] for b in client.get("/api/books").json()] == [book["id"]]
    r = client.patch(f"/api/books/{book['id']}", json={"credits": {"license": "CC BY 4.0"}})
    assert r.json()["credits"]["license"] == "CC BY 4.0" and r.json()["title"] == book["title"]
    assert client.get("/api/books/nope").status_code == 404
    assert client.get("/api/books/65a000000000000000000001").status_code == 404
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_coords.py api/tests/test_books.py -q`. Expected: FAIL (`coords` missing; upload still answers with the example).

- [ ] **Step 3: Implement**

- `POST /api/books` (`file: UploadFile`, `title: str | None = Form(None)`, `credits: str | None = Form(None)`): read the upload in 1 MB chunks and stop past `MAX_UPLOAD_BYTES` (413, `"The file is over 50 MB."`). Open the bytes with `fitz.open(stream=..., filetype="pdf")`; failure is 400 `"This file is not a readable PDF."`; more than `MAX_UPLOAD_PAGES` is 413 `"The book is over 30 pages."`. Then save `source.pdf` in `book_dir`, insert the book as `ingesting`, add `jobs.ingest_book` as a background task, and return `{book_id, state}`. Credits always hold all five keys, missing ones null. `PATCH` merges credits key by key.
- `jobs.ingest_book`: `rasterize`; on any exception set the book `failed` and stop. Insert one page per asset as `processing` with `processing_started_at`, set the book `ready` with `page_count`, then run `process_one` for every page on a `ThreadPoolExecutor(max_workers=settings.PAGE_CONCURRENCY)` and wait.
- `jobs.process_one`: call `process_page` with a `PageAsset` rebuilt from the page document. An exception becomes `PageResult(state="failed", page_kind=None, candidates=[], selected=None, reason=str(error))`. Either way the result goes through `apply_result`, so every processed page has its `auto_*` fields.
- `jobs.apply_result` — the merge rule, because candidates are only ever added:

```python
def apply_result(page, result):
    candidates = list(page.get("candidates", []))
    known = {c["mask_hash"] for c in candidates}
    candidates += [c.model_dump() for c in result.candidates if c.mask_hash not in known]
    chosen = result.candidates[result.selected].mask_hash if result.selected is not None else None
    selected = next((i for i, c in enumerate(candidates) if c["mask_hash"] == chosen), None)
    changed = chosen != page.get("subject_hash")
    db.pages.update_one({"_id": page["_id"]}, {"$set": {
        "state": result.state, "reason": result.reason, "page_kind": result.page_kind,
        "candidates": candidates, "selected": selected, "subject_hash": chosen,
        "confirmed": page.get("confirmed", False) and not changed,
        "auto_state": result.state, "auto_subject_hash": chosen, "auto_reason": result.reason}})
```

- In `api/tests/test_routes.py`: delete `test_upload_answers_at_once` and the three `books` rows of `JSON_ROUTES`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: upload a book, process pages in the background, book routes"
```

---

### Task 3: Overlay image and a preview that stores nothing

**Files:**
- Create: `api/tests/test_images.py`
- Modify: `api/routes/pages.py`, `api/routes/profiles.py`, `api/images.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `modules.display.overlay(view_path, mask_path) -> bytes`, `modules.display.render(image_path, view_path, mask_path, settings, level, text, fmt="webp") -> bytes`.
- Produces:
  - `api.images.selected(page: dict) -> dict | None`: the selected candidate document, or None.
  - `api.images.render_page(page: dict, settings: Settings, level: int) -> bytes`: raises `HTTPException(409, "This page has no subject yet.")` when nothing is selected.
  - `api.images.view_bytes(page: dict) -> bytes`: the working copy as WebP at quality 90.
  - Routes: `GET /api/pages/{id}/overlay`, `POST /api/preview` with body `{page_id: str, settings: Settings, level: Level}`.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_images.py`

```python
def is_webp(r):
    return (r.status_code == 200 and r.headers["content-type"] == "image/webp"
            and r.headers["cache-control"] == "no-store" and r.content[8:12] == b"WEBP")


def test_overlay_calls_the_display_with_the_selected_mask(monkeypatch):
    calls = []
    real = modules.display.overlay
    monkeypatch.setattr(modules.display, "overlay", lambda v, m: calls.append(m) or real(v, m))
    page = upload()["pages"][0]
    assert is_webp(client.get(f"/api/pages/{page['id']}/overlay"))
    assert calls[0].endswith(f"1_{page['subject_hash']}.png")


def test_overlay_without_a_subject_is_the_plain_page():
    page = upload()["pages"][1]          # needs_subject, nothing selected
    assert is_webp(client.get(f"/api/pages/{page['id']}/overlay"))


def test_preview_passes_unsaved_settings_and_stores_nothing(monkeypatch):
    calls = []
    real = modules.display.render
    monkeypatch.setattr(modules.display, "render",
                        lambda *a, **k: calls.append(a) or real(*a, **k))
    page = upload()["pages"][0]
    before = {name: getattr(db, name).count_documents({})
              for name in ("books", "pages", "profiles", "checks", "approvals")}
    body = {"page_id": page["id"], "level": 2,
            "settings": {"colors": ["#fdd835"], "background": "#000000"}}
    assert is_webp(client.post("/api/preview", json=body))
    assert calls[0][3].colors == ["#FDD835"] and calls[0][4] == 2
    assert before == {name: getattr(db, name).count_documents({}) for name in before}


def test_preview_refusals():
    pages = upload()["pages"]
    ok = {"colors": ["#E53935"], "background": "#000000"}
    assert client.post("/api/preview", json={"page_id": pages[1]["id"], "settings": ok, "level": 2}).status_code == 409
    assert client.post("/api/preview", json={"page_id": pages[0]["id"], "settings": ok, "level": 5}).status_code == 422
    assert client.post("/api/preview", json={"page_id": "nope", "settings": ok, "level": 2}).status_code == 404
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_images.py -q`. Expected: FAIL (overlay ignores the page id; preview returns the stand-in page for a page with no subject).

- [ ] **Step 3: Implement** the two routes and the three `api.images` functions. Delete `stub_page` and `stub_render` once nothing uses them (the `/render` and `/reader/page` routes still do until Tasks 5 and 8; leave them until then). In `test_routes.py` remove the overlay and preview rows from `IMAGE_ROUTES`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: overlay image and stateless preview"
```

---

### Task 4: Fix subjects (pick, click, outline; confirm, leave out, retry; restart recovery)

**Files:**
- Create: `api/tests/test_subjects.py`
- Modify: `api/routes/pages.py`, `api/routes/books.py` (confirm-all), `api/jobs.py`, `api/main.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `coords.to_pixels`, `views.page_json`, `jobs.process_one`, `jobs.book_dir`, `modules.pipeline.segment_at_point(image_path, x, y, out_dir) -> Candidate`, `modules.pipeline.mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate`.
- Produces:
  - `api.jobs.recover_interrupted() -> None`, called once from the app's lifespan startup.
  - `api.routes.pages.select(page: dict, index: int) -> dict`: sets `selected`, `subject_hash`, `state="ready"`, `reason=None`, and `confirmed=False` when the hash changed. Returns the updated page.
  - Routes: `POST /api/pages/{id}/subject`, `/confirm`, `/omit`, `/retry`, `POST /api/books/{id}/confirm-all`. Each returns `page_json` (a list for confirm-all).

- [ ] **Step 1: Write the failing tests** in `api/tests/test_subjects.py`

```python
OUTLINE = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.4], [0.1, 0.4]]
subject = lambda page, body: client.post(f"/api/pages/{page['id']}/subject", json=body)


def test_pick_a_candidate():
    page = upload()["pages"][1]
    r = subject(page, {"candidate": 1}).json()
    assert (r["selected"], r["state"], r["confirmed"]) == (1, "ready", False)
    assert r["subject_hash"] == page["candidates"][1]["mask_hash"]


def test_click_sends_master_pixels_and_appends(monkeypatch):
    calls = []
    real = modules.pipeline.segment_at_point
    monkeypatch.setattr(modules.pipeline, "segment_at_point",
                        lambda path, x, y, out: calls.append((x, y, str(out))) or real(path, x, y, out))
    page = upload()["pages"][1]
    r = subject(page, {"point": [0.5, 0.1]}).json()
    assert calls[0][:2] == (1500.0, 225.0)
    assert calls[0][2].endswith(f"books/{page['book_id']}")
    assert len(r["candidates"]) == 3 and r["selected"] == 2 and r["candidates"][2]["source"] == "click"


def test_outline_lands_where_it_was_drawn():
    page = upload()["pages"][2]                      # failed page: the manual fallback
    r = subject(page, {"label": "frog", "outline": OUTLINE}).json()
    c = r["candidates"][r["selected"]]
    assert (r["state"], c["label"], c["source"], c["confidence"]) == ("ready", "frog", "manual", 1.0)
    assert c["box"] == [0.1, 0.1, 0.5, 0.4]
    stored = db.pages.find_one({"_id": ObjectId(page["id"])})["candidates"][0]
    mask = Image.open(stored["mask_path"])
    assert mask.size == (3000, 2250)
    assert mask.getpixel((900, 500)) == 255 and mask.getpixel((2000, 1500)) == 0


def test_reselecting_an_earlier_subject_restores_its_hash():
    page = upload()["pages"][0]
    first = page["subject_hash"]
    assert subject(page, {"candidate": 1}).json()["subject_hash"] != first
    assert subject(page, {"candidate": 0}).json()["subject_hash"] == first


def test_changing_the_subject_clears_the_confirmation():
    page = upload()["pages"][0]
    assert client.post(f"/api/pages/{page['id']}/confirm").json()["confirmed"] is True
    assert subject(page, {"candidate": 0}).json()["confirmed"] is True      # same subject
    assert subject(page, {"candidate": 1}).json()["confirmed"] is False


@pytest.mark.parametrize("body", [
    {}, {"candidate": 0, "point": [0.5, 0.5]}, {"candidate": 9}, {"candidate": -1},
    {"outline": OUTLINE}, {"label": " ", "outline": OUTLINE},
    {"label": "frog", "outline": OUTLINE[:2]}, {"refine_point": [0.5, 0.5]}])
def test_bad_subject_bodies_are_refused(body):
    assert subject(upload()["pages"][0], body).status_code == 422


@pytest.mark.parametrize("body", [
    {"point": [1.2, 0.5]}, {"point": [0.5, -0.1]},
    {"label": "frog", "outline": [[0.1, 0.1], [0.5, 0.1], [0.5, 1.4]]}])
def test_positions_outside_the_page_are_refused(body):
    assert subject(upload()["pages"][0], body).status_code == 422


def test_pipeline_error_on_click_leaves_the_page_unchanged(monkeypatch):
    page = upload()["pages"][0]
    monkeypatch.setattr(modules.pipeline, "segment_at_point", lambda *a: 1 / 0)
    assert subject(page, {"point": [0.5, 0.5]}).status_code == 502
    assert client.get(f"/api/books/{page['book_id']}").json()["pages"][0] == page


def test_confirm_needs_a_subject():
    page = upload()["pages"][1]
    assert client.post(f"/api/pages/{page['id']}/confirm").status_code == 409


def test_confirm_all_confirms_only_ready_pages_not_left_out():
    book = upload(6)                                 # states cycle ready, needs_subject, failed
    client.post(f"/api/pages/{book['pages'][3]['id']}/omit", json={"omitted": True})
    done = client.post(f"/api/books/{book['id']}/confirm-all").json()
    assert [p["number"] for p in done] == [1] and done[0]["confirmed"] is True
    assert client.post(f"/api/books/{book['id']}/confirm-all").json() == []


def test_omit_and_bring_back():
    page = upload()["pages"][0]
    assert client.post(f"/api/pages/{page['id']}/omit", json={"omitted": True}).json()["omitted"] is True
    assert client.post(f"/api/pages/{page['id']}/omit", json={"omitted": False}).json()["omitted"] is False


def test_retry_reruns_a_failed_page(monkeypatch):
    page = upload()["pages"][2]
    monkeypatch.setattr(modules.pipeline, "process_page", lambda asset, out, force=False:
                        stubs.process_page(asset.model_copy(update={"page_number": 1}), out))
    r = client.post(f"/api/pages/{page['id']}/retry", json={})
    assert r.status_code == 200 and r.json()["state"] == "processing"
    after = client.get(f"/api/books/{page['book_id']}").json()["pages"][2]
    assert (after["state"], after["reason"], after["selected"]) == ("ready", None, 0)


def test_retry_rules(monkeypatch):
    pages = upload()["pages"]
    assert client.post(f"/api/pages/{pages[0]['id']}/retry", json={}).status_code == 409   # ready
    db.pages.update_one({"_id": ObjectId(pages[2]["id"])}, {"$set": {"state": "unsupported"}})
    assert client.post(f"/api/pages/{pages[2]['id']}/retry", json={}).status_code == 409   # needs force
    forced = []
    monkeypatch.setattr(modules.pipeline, "process_page", lambda asset, out, force=False:
                        forced.append(force) or stubs.process_page(asset, out))
    assert client.post(f"/api/pages/{pages[2]['id']}/retry", json={"force": True}).status_code == 200
    assert forced == [True]


def test_processing_page_cannot_be_changed():
    page = upload()["pages"][0]
    db.pages.update_one({"_id": ObjectId(page["id"])}, {"$set": {"state": "processing"}})
    assert subject(page, {"candidate": 1}).status_code == 409
    assert client.post(f"/api/pages/{page['id']}/retry", json={}).status_code == 409


def test_restart_marks_stuck_work_failed():
    book = upload()
    stuck = db.books.insert_one({"title": "t", "state": "ingesting"}).inserted_id
    db.pages.update_one({"_id": ObjectId(book["pages"][0]["id"])}, {"$set": {"state": "processing"}})
    with TestClient(app):                            # runs the startup handler
        pass
    assert db.books.find_one({"_id": stuck})["state"] == "failed"
    pages = client.get(f"/api/books/{book['id']}").json()["pages"]
    assert (pages[0]["state"], pages[0]["reason"]) == ("failed", "interrupted, retry")
    assert pages[1]["state"] == "needs_subject"
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_subjects.py -q`. Expected: FAIL (routes still answer with examples).

- [ ] **Step 3: Implement**

- Subject body: one Pydantic model with optional `candidate: int`, `point: [x, y]`, `label: str`, `outline: list[[x, y]]`, and `model_config = {"extra": "forbid"}`. A validator accepts exactly one of three shapes: `candidate` alone, `point` alone, or `label` with `outline` (label non-blank, at least 3 points). Anything else is 422, including `refine_point`.
- `ValueError` from `coords.to_pixels` becomes 422. Any other exception from a pipeline function becomes 502 `"The cut-out could not be made. Try again or draw an outline."` with the page untouched.
- Click and outline: convert through `coords.to_pixels`, call the pipeline with `out_dir=jobs.book_dir(book_id)`, append the candidate unless its `mask_hash` is already present, then `select` it.
- Retry: 409 unless the state is `failed`, or `unsupported` with `force`. Set `processing`, clear `reason`, set `processing_started_at`, add `jobs.process_one(page_id, force)` as a background task, and return the page as it is then.
- `recover_interrupted`: books still `ingesting` become `failed`; pages still `processing` become `failed` with reason `"interrupted, retry"`. Wire it into a FastAPI lifespan in `main.py`, after `db.ensure_indexes()`.
- In `test_routes.py` remove the retry, subject, confirm, confirm-all and omit rows.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: subject routes, confirm, leave out, retry, restart recovery"
```

---

### Task 5: Child profiles, the settings hash, and renders for a saved profile

**Files:**
- Create: `api/versions.py`, `api/tests/test_profiles.py`
- Modify: `api/routes/profiles.py`, `api/images.py`, `api/views.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `contracts.hashing.settings_hash`, `contracts.hashing.version_token`, `modules.display.RENDER_VERSION`, `images.render_page`.
- Produces:
  - `api.views.profile_json(profile: dict) -> dict`: the keys of the `GET /api/profiles` example.
  - `api.versions.Version`: a `NamedTuple` of `subject_hash: str, settings_hash: str, level: int, render_version: str`, with property `token -> str` (`version_token` of the four).
  - `api.versions.current_version(page: dict, profile: dict, level: int) -> Version | None`: None unless the page has a `subject_hash`, is `confirmed` and is not `omitted`. Reads `modules.display.RENDER_VERSION` at call time, not at import.
  - `api.images.cached_render(page: dict, profile: dict, level: int) -> bytes`: an in-memory cache of at most 256 images keyed by `(page id, token)`. For a page with no version, the key uses the token of its selected subject so previews of unconfirmed pages still work.
  - Routes: `GET /api/profiles`, `POST /api/profiles`, `PATCH /api/profiles/{id}`, `GET /api/render/{page_id}?profile=&level=&v=`.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_profiles.py`

```python
MAYA = {"name": "Maya", "level": 1, "contrast_override_note": None,
        "settings": {"colors": ["#E53935"], "background": "#000000", "size": "medium",
                     "position": "center", "text_mode": "off", "outline": "off"}}
make = lambda **over: client.post("/api/profiles", json={**MAYA, **over}).json()
patch = lambda p, body: client.patch(f"/api/profiles/{p['id']}", json=body)


def test_create_matches_the_agreed_example():
    p = make()
    example = EX["POST /api/profiles"]["response"]
    assert {**p, "id": example["id"]} == example        # includes settings_hash 2804b24a29e2
    assert client.get("/api/profiles").json() == [p]


def test_changing_a_color_and_back_restores_the_hash():
    p = make()
    changed = patch(p, {"settings": {**MAYA["settings"], "colors": ["#FDD835"]}}).json()
    assert changed["settings_hash"] != p["settings_hash"]
    assert patch(p, {"settings": MAYA["settings"]}).json()["settings_hash"] == p["settings_hash"]


def test_name_level_and_note_do_not_change_the_hash():
    p = make()
    r = patch(p, {"name": "May", "level": 3, "contrast_override_note": "checked on her tablet"}).json()
    assert r["settings_hash"] == p["settings_hash"]
    assert (r["name"], r["level"], r["contrast_override_note"]) == ("May", 3, "checked on her tablet")


def test_lowercase_colors_hash_the_same():
    assert make(settings={**MAYA["settings"], "colors": ["#e53935"]})["settings_hash"] == "2804b24a29e2"


@pytest.mark.parametrize("over", [
    {"name": " "}, {"level": 5}, {"level": None},
    {"settings": {**MAYA["settings"], "colors": []}},
    {"settings": {**MAYA["settings"], "colors": ["#E53935"] * 4}},
    {"settings": {**MAYA["settings"], "background": "black"}}])
def test_bad_profiles_are_refused(over):
    assert client.post("/api/profiles", json={**MAYA, **over}).status_code == 422


def test_unknown_profile_is_404():
    assert client.patch("/api/profiles/65c000000000000000000009", json={"name": "x"}).status_code == 404


def test_render_uses_the_saved_settings_and_the_requested_level(monkeypatch):
    calls = []
    real = modules.display.render
    monkeypatch.setattr(modules.display, "render", lambda *a, **k: calls.append(a) or real(*a, **k))
    page, p = upload()["pages"][0], make()
    url = f"/api/render/{page['id']}?profile={p['id']}&level=3"
    r = client.get(url)
    assert r.headers["content-type"] == "image/webp" and r.headers["cache-control"] == "no-store"
    assert calls[0][3].colors == ["#E53935"] and calls[0][4] == 3
    client.get(url)
    assert len(calls) == 1                               # second one came from the cache


def test_render_refuses_a_stale_token_and_a_page_with_no_subject():
    pages, p = upload()["pages"], make()
    client.post(f"/api/pages/{pages[0]['id']}/confirm")
    assert client.get(f"/api/render/{pages[0]['id']}?profile={p['id']}&level=1&v=000000000000").status_code == 409
    assert client.get(f"/api/render/{pages[1]['id']}?profile={p['id']}&level=1").status_code == 409
    assert client.get(f"/api/render/{pages[0]['id']}?profile={p['id']}&level=9").status_code == 422
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_profiles.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement.** `POST` body: `name` (stripped, non-empty), `level: Level`, `settings: Settings`, `contrast_override_note: str | None = None`. `PATCH` takes any subset. Both recompute `settings_hash` from the saved settings on every save. `level` in every query string is validated as 1 to 4. Remove the three profile rows from `JSON_ROUTES` and the render row from `IMAGE_ROUTES`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: profiles, settings hash, saved-profile renders with a cache"
```

---

### Task 6: Contact sheet

**Files:**
- Create: `api/tests/test_sheet.py`
- Modify: `api/routes/approval.py`, `api/versions.py`, `api/tests/helpers.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `versions.current_version`, `images.selected`, `modules.display.run_checks(image_path, view_path, mask_path, settings, level, text) -> CheckResult`.
- Produces:
  - `api.versions.approval_state(page_id: ObjectId, profile_id: ObjectId, version: Version | None) -> Literal["approved", "rejected", "none"]`: from the newest `approvals` record (by `at`) matching the page, the profile and all four version values. `"none"` when `version` is None or nothing matches.
  - `api.versions.stored_checks(page: dict, version: Version, settings: Settings) -> dict`: returns the stored `checks.result` for this page and version, running `run_checks` and inserting it first when there is none.
  - `api.tests.helpers`: `make_profile(**over) -> dict` (the `MAYA` body from Task 5), `confirmed_book(pages: int = 3) -> dict` (uploads, then `confirm-all`, returns the fresh book).
  - Route: `GET /api/books/{id}/sheet?profile=&level=` returning `{book_id, profile_id, level, render_version, pages: [row]}`.

Row fields, as in the example: `page_id, number, version, state, confirmed, omitted, label, source, checks, second_look, approval, preview_url`. `label` and `source` come from the selected candidate, or null. For a row with no version: `version`, `checks`, `second_look` and `preview_url` are null and `approval` is `"none"`. For a row with a version: `second_look` is the page's stored result when its `subject_hash` matches, otherwise `{"status": "pending", "answer": null, "detail": null}`; `preview_url` is `/api/render/{page_id}?profile={profile_id}&level={level}&v={token}`.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_sheet.py`

```python
sheet = lambda book, p, level=1: client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}&level={level}")


def test_sheet_rows():
    book, p = confirmed_book(), make_profile()
    body = sheet(book, p).json()
    example = EX["GET /api/books/{id}/sheet"]["response"]
    assert set(body) == set(example) and (body["level"], body["render_version"]) == (1, "stub-1")
    row, unpicked, failed = body["pages"]
    assert set(row) == set(example["pages"][0])
    assert row["version"] == version_token(book["pages"][0]["subject_hash"], p["settings_hash"], 1, "stub-1")
    assert (row["label"], row["source"], row["approval"]) == ("rabbit", "auto", "none")
    assert row["checks"]["fidelity"]["status"] == "pass" and row["second_look"]["status"] == "pending"
    assert row["preview_url"] == f"/api/render/{row['page_id']}?profile={p['id']}&level=1&v={row['version']}"
    assert client.get(row["preview_url"]).status_code == 200
    for other in (unpicked, failed):
        assert (other["version"], other["checks"], other["preview_url"], other["approval"]) == (None, None, None, "none")


def test_checks_run_once_per_version(monkeypatch):
    calls = []
    real = modules.display.run_checks
    monkeypatch.setattr(modules.display, "run_checks", lambda *a: calls.append(a[4]) or real(*a))
    book, p = confirmed_book(), make_profile()
    sheet(book, p); sheet(book, p)
    assert calls == [1]
    sheet(book, p, level=2)
    assert calls == [1, 2] and db.checks.count_documents({}) == 2


def test_a_left_out_page_has_no_version():
    book, p = confirmed_book(), make_profile()
    client.post(f"/api/pages/{book['pages'][0]['id']}/omit", json={"omitted": True})
    row = sheet(book, p).json()["pages"][0]
    assert (row["version"], row["omitted"]) == (None, True)


def test_the_level_changes_the_version():
    book, p = confirmed_book(), make_profile()
    assert sheet(book, p, 1).json()["pages"][0]["version"] != sheet(book, p, 2).json()["pages"][0]["version"]


def test_sheet_refusals():
    book, p = confirmed_book(), make_profile()
    assert client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}").status_code == 422
    assert client.get(f"/api/books/{book['id']}/sheet?profile=65c000000000000000000009&level=1").status_code == 404
    assert client.get(f"/api/books/65a000000000000000000009/sheet?profile={p['id']}&level=1").status_code == 404
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_sheet.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement** the route and the two `versions` functions. If `run_checks` raises, the row's `checks` is null and nothing is stored (the spec says no check raises; this keeps one bad page from blanking the sheet). Remove the sheet row from `JSON_ROUTES`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: contact sheet with versions, stored checks and approval state"
```

---

### Task 7: Approval, with "look again"

**Files:**
- Create: `api/tests/test_approve.py`
- Modify: `api/routes/approval.py`, `api/tests/helpers.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `versions.current_version`, `versions.approval_state`.
- Produces:
  - Route `POST /api/books/{id}/approve`, body `{profile_id: str, level: Level, pages: [{page_id: str, version: str, decision: "approve" | "reject"}]}`.
    - 200 `{"approvals": [record]}` when every version sent is current.
    - 409 `{"detail": "look again", "changed": [{page_id, sent, current}], "recorded": [record]}` when any differs. Matching pages are still recorded; changed ones are not. `current` is null for a page with no version, or one that is not in this book.
    - `record` = `{page_id, profile_id, level, version, decision, at}`, `at` in ISO 8601 UTC ending in `Z`.
  - `api.tests.helpers.approve_all(book: dict, profile: dict, level: int = 1) -> Response`: loads the sheet and approves every row that has a version.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_approve.py`

```python
def send(book, p, rows, level=1, decision="approve"):
    return client.post(f"/api/books/{book['id']}/approve", json={
        "profile_id": p["id"], "level": level,
        "pages": [{"page_id": r["page_id"], "version": r["version"], "decision": decision} for r in rows]})

rows = lambda book, p, level=1: client.get(
    f"/api/books/{book['id']}/sheet?profile={p['id']}&level={level}").json()["pages"]


def test_approve_records_and_the_sheet_shows_it():
    book, p = confirmed_book(), make_profile()
    row = rows(book, p)[0]
    r = send(book, p, [row])
    assert r.status_code == 200
    record = r.json()["approvals"][0]
    assert set(record) == set(EX["POST /api/books/{id}/approve"]["response"]["approvals"][0])
    assert (record["version"], record["decision"], record["at"][-1]) == (row["version"], "approve", "Z")
    assert rows(book, p)[0]["approval"] == "approved"
    stored = db.approvals.find_one()
    assert stored["subject_hash"] == book["pages"][0]["subject_hash"]
    assert (stored["settings_hash"], stored["level"], stored["render_version"]) == (p["settings_hash"], 1, "stub-1")


def test_the_newest_decision_wins():
    book, p = confirmed_book(), make_profile()
    row = rows(book, p)[0]
    send(book, p, [row]); send(book, p, [row], decision="reject")
    assert rows(book, p)[0]["approval"] == "rejected"
    assert db.approvals.count_documents({}) == 2          # nothing is deleted


def test_stale_version_is_refused_and_not_recorded():
    book, p = confirmed_book(6), make_profile()           # pages 1 and 4 have versions
    first, fourth = [r for r in rows(book, p) if r["version"]]
    client.post(f"/api/pages/{first['page_id']}/subject", json={"candidate": 1})
    client.post(f"/api/pages/{first['page_id']}/confirm")
    r = send(book, p, [first, fourth])
    assert r.status_code == 409 and r.json()["detail"] == "look again"
    assert r.json()["changed"] == [{"page_id": first["page_id"], "sent": first["version"],
                                    "current": rows(book, p)[0]["version"]}]
    assert [a["page_id"] for a in r.json()["recorded"]] == [fourth["page_id"]]
    assert db.approvals.count_documents({}) == 1


def test_a_profile_edit_while_the_sheet_is_open_is_look_again():
    book, p = confirmed_book(), make_profile()
    row = rows(book, p)[0]
    client.patch(f"/api/profiles/{p['id']}", json={"settings": {"colors": ["#FDD835"], "background": "#000000"}})
    assert send(book, p, [row]).status_code == 409 and db.approvals.count_documents({}) == 0


def test_pages_without_a_version_cannot_be_approved():
    book, p = confirmed_book(), make_profile()
    other = upload()["pages"][0]
    fake = [{"page_id": book["pages"][1]["id"], "version": "000000000000"},     # needs_subject
            {"page_id": other["id"], "version": "000000000000"}]               # another book
    r = send(book, p, fake)
    assert r.status_code == 409 and [c["current"] for c in r.json()["changed"]] == [None, None]
    assert db.approvals.count_documents({}) == 0


def test_approval_is_per_child_and_per_look():
    book, maya, leo = confirmed_book(), make_profile(), make_profile(name="Leo", level=2)
    send(book, maya, [rows(book, maya)[0]])
    assert rows(book, leo, 1)[0]["approval"] == "none"
    assert rows(book, maya, 2)[0]["approval"] == "none"


def test_bad_approve_bodies_are_refused():
    book, p = confirmed_book(), make_profile()
    row = rows(book, p)[0]
    assert send(book, p, [row], decision="verified").status_code == 422
    assert send(book, p, [row], level=7).status_code == 422
    assert send(book, {"id": "65c000000000000000000009"}, [row]).status_code == 404
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_approve.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement.** For each page sent, compute `current_version(...)` and compare its token with `version`. Insert one `approvals` document per match with the four version values and `at = now (UTC)`. Remove the approve row from `JSON_ROUTES`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: approve versions, refuse stale ones with look again"
```

---

### Task 8: Reader that serves approved versions only

This task is on the never-cut list. Kevin's four outside tests do not exist yet; the tests below are written from the spec's three cases plus the stale approval (covered in Task 7), and Kevin's run tomorrow as the outside check.

**Files:**
- Create: `api/tests/test_reader.py`
- Modify: `api/routes/reader.py`, `api/versions.py`, `api/images.py`, `api/tests/test_routes.py`

**Interfaces:**
- Consumes: `versions.current_version`, `versions.approval_state`, `images.cached_render`.
- Produces:
  - `api.versions.fully_approved(pages: list[dict], profile: dict, level: int) -> bool`: at least one page is `"approved"`, and every page is omitted or its `approval_state` is `"approved"` or `"rejected"`.
  - `GET /api/reader/{book_id}?profile=&level=` with the keys of the example: `book_id, title, profile_id, level, pages[{page_id, number, v, image_url}], skipped[{page_id, number, reason}], credits, adaptation_note, versions[{profile_id, profile_name, level, fully_approved}]`.
    - `pages`: in page order, only pages whose current version is approved. `image_url` = `/api/reader/page/{page_id}?profile={profile_id}&level={level}&v={token}`.
    - `skipped.reason`: `"omitted"` if the page is omitted, else `"rejected"` if its current version's newest decision is reject, else `"not_approved"`.
    - `adaptation_note`: exactly `"These pages were adapted from the original book."`
    - `versions`: decision 9 in "Decisions the spec leaves open", sorted by profile name then level.
  - `GET /api/reader/page/{page_id}?profile=&level=&v=`: the image, or 403 `{"detail": "not approved"}`.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_reader.py`

```python
manifest = lambda book, p, level=1: client.get(f"/api/reader/{book['id']}?profile={p['id']}&level={level}").json()


def approved_page():
    book, p = confirmed_book(), make_profile()
    assert approve_all(book, p).status_code == 200
    return book, p, manifest(book, p)["pages"][0]


def test_an_approved_page_is_served():
    book, p, page = approved_page()
    r = client.get(page["image_url"])
    assert r.status_code == 200 and r.content[8:12] == b"WEBP"
    assert r.headers["cache-control"] == "no-store"


def test_a_never_approved_page_is_refused():
    book, p = confirmed_book(), make_profile()
    token = client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}&level=1").json()["pages"][0]["version"]
    r = client.get(f"/api/reader/page/{book['pages'][0]['id']}?profile={p['id']}&level=1&v={token}")
    assert r.status_code == 403 and r.json() == {"detail": "not approved"}
    assert manifest(book, p)["pages"] == []


CHANGES = {
    "profile": lambda page, p: client.patch(f"/api/profiles/{p['id']}",
                   json={"settings": {"colors": ["#FDD835"], "background": "#000000"}}),
    "subject": lambda page, p: [client.post(f"/api/pages/{page['page_id']}/subject", json={"candidate": 1}),
                                client.post(f"/api/pages/{page['page_id']}/confirm")],
    "omitted": lambda page, p: client.post(f"/api/pages/{page['page_id']}/omit", json={"omitted": True}),
    "rejected": lambda page, p: client.post(
        f"/api/books/{page['book_id']}/approve", json={"profile_id": p["id"], "level": 1,
        "pages": [{"page_id": page["page_id"], "version": page["v"], "decision": "reject"}]}),
}


@pytest.mark.parametrize("change", CHANGES)
def test_approved_then_changed_is_refused(change):
    book, p, page = approved_page()
    CHANGES[change]({**page, "book_id": book["id"]}, p)
    assert client.get(page["image_url"]).status_code == 403          # the old link is dead
    after = manifest(book, p)
    assert after["pages"] == []
    if change in ("profile", "subject"):                              # a fresh link is refused too
        token = client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}&level=1").json()["pages"][0]["version"]
        assert token != page["v"]
        assert client.get(f"/api/reader/page/{page['page_id']}?profile={p['id']}&level=1&v={token}").status_code == 403


@pytest.mark.parametrize("query", [
    "profile={p}&level=1&v=000000000000",      # wrong token
    "profile={p}&level=2&v={v}",               # another look
    "profile={p}&level=1",                     # no token
    "profile=65c000000000000000000009&level=1&v={v}",
    "profile=nope&level=1&v={v}",
    "profile={p}&level=9&v={v}"])
def test_every_other_request_is_refused(query):
    book, p, page = approved_page()
    r = client.get(f"/api/reader/page/{page['page_id']}?" + query.format(p=p["id"], v=page["v"]))
    assert r.status_code == 403
    assert client.get(f"/api/reader/page/nope?profile={p['id']}&level=1&v={page['v']}").status_code == 403


def test_another_child_cannot_use_the_link():
    book, p, page = approved_page()
    leo = make_profile(name="Leo")                                    # same settings, same hash
    r = client.get(f"/api/reader/page/{page['page_id']}?profile={leo['id']}&level=1&v={page['v']}")
    assert r.status_code == 403


def test_manifest_lists_pages_skips_and_credits():
    book, p, page = approved_page()
    client.post(f"/api/pages/{book['pages'][2]['id']}/omit", json={"omitted": True})
    m = manifest(book, p)
    assert set(m) == set(EX["GET /api/reader/{book_id}"]["response"])
    assert [(x["number"], x["v"]) for x in m["pages"]] == [(1, page["v"])]
    assert [(s["number"], s["reason"]) for s in m["skipped"]] == [(2, "not_approved"), (3, "omitted")]
    assert set(m["credits"]) == {"author", "illustrator", "publisher", "source", "license"}
    assert m["adaptation_note"] == "These pages were adapted from the original book."


def test_fully_approved_versions():
    book, maya, leo = confirmed_book(), make_profile(), make_profile(name="Leo", level=2)
    for page in book["pages"][1:]:
        client.post(f"/api/pages/{page['id']}/omit", json={"omitted": True})
    approve_all(book, maya)
    approve_all(book, maya, level=3)
    assert manifest(book, maya)["versions"] == [
        {"profile_id": leo["id"], "profile_name": "Leo", "level": 2, "fully_approved": False},
        {"profile_id": maya["id"], "profile_name": "Maya", "level": 1, "fully_approved": True},
        {"profile_id": maya["id"], "profile_name": "Maya", "level": 3, "fully_approved": True}]


def test_an_undecided_page_blocks_fully_approved():
    book, p = confirmed_book(), make_profile()                        # pages 2 and 3 undecided
    approve_all(book, p)
    assert manifest(book, p)["versions"][0]["fully_approved"] is False
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_reader.py -q`. Expected: FAIL (the skeleton serves an image for anything).

- [ ] **Step 3: Implement.** `reader_page` takes `profile`, `level` and `v` as optional raw strings and answers 403 through one path for every failure: bad id, unknown page or profile, level not 1 to 4, no current version, `v` missing or not equal to the current token, or `approval_state` not `"approved"`. Only then does it call `images.cached_render`. Delete `stub_page`, `stub_render` and `test_routes.py`'s remaining `JSON_ROUTES` and `IMAGE_ROUTES` tests; keep `test_unknown_route_is_404` and `test_every_example_route_is_served`. `main.py` no longer needs `EXAMPLES` or `example()`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass. Then confirm no route still answers with an example: `grep -rn "example(" api --include=*.py` prints nothing.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: reader manifest and page images for approved versions only"
```

---

### Task 9: Second look in the background

First thing to cut if Task 8 overran. If it is cut, write that under `Not done` in the notes and go to Task 10.

**Files:**
- Create: `api/tools/__init__.py`, `api/tools/second_look.py`, `api/tests/test_second_look.py`
- Modify: `api/jobs.py`, `api/routes/pages.py`, `api/routes/books.py`

**Interfaces:**
- Consumes: `modules.display.second_look(image_path, mask_path, label, synonyms) -> SecondLook`.
- Produces:
  - `api.jobs.start_second_look(page: dict) -> bool`: if the page's stored `second_look.subject_hash` already equals its `subject_hash`, returns False. Otherwise stores `{subject_hash, status: "pending", answer: None, detail: None}` and returns True.
  - `api.jobs.run_second_look(page_id: ObjectId, subject_hash: str) -> None`: runs the display function for the candidate with that hash and stores `{subject_hash, status, answer, detail}`, with the update filtered on `subject_hash` still being the page's. An exception stores `status="warn"`, `detail="The second look could not run."`.
  - `python -m api.tools.second_look [book_id]`: runs it for every confirmed page (of one book, or all) whose stored result is missing, pending, or for another subject. Prints one line per page: page id, number, status, answer.
  - `api.tools.second_look.main(argv: list[str]) -> int`.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_second_look.py`

```python
def test_confirm_shows_pending_then_the_result(monkeypatch):
    page = upload()["pages"][0]
    r = client.post(f"/api/pages/{page['id']}/confirm").json()
    assert r["second_look"] == {"status": "pending", "answer": None, "detail": None}
    after = client.get(f"/api/books/{page['book_id']}").json()["pages"][0]
    assert after["second_look"] == {"status": "pass", "answer": "rabbit", "detail": "stub"}


def test_it_runs_once_per_page_and_subject(monkeypatch):
    calls = []
    real = modules.display.second_look
    monkeypatch.setattr(modules.display, "second_look", lambda *a: calls.append(a[2]) or real(*a))
    page = upload()["pages"][0]
    confirm = lambda: client.post(f"/api/pages/{page['id']}/confirm")
    confirm(); confirm()
    assert calls == ["rabbit"]
    client.post(f"/api/pages/{page['id']}/subject", json={"candidate": 1}); confirm()
    assert calls == ["rabbit", "tree"]


def test_confirm_all_starts_it_for_each_page():
    book = upload(6)
    client.post(f"/api/books/{book['id']}/confirm-all")
    pages = client.get(f"/api/books/{book['id']}").json()["pages"]
    assert [p["second_look"]["status"] if p["second_look"] else None for p in pages] == \
           ["pass", None, None, "pass", None, None]


def test_late_result_for_an_old_subject_is_discarded():
    page = upload()["pages"][0]
    old = page["subject_hash"]
    client.post(f"/api/pages/{page['id']}/subject", json={"candidate": 1})
    jobs.run_second_look(ObjectId(page["id"]), old)
    assert db.pages.find_one({"_id": ObjectId(page["id"])}).get("second_look") is None


def test_a_failing_second_look_is_a_warning_and_blocks_nothing(monkeypatch):
    monkeypatch.setattr(modules.display, "second_look", lambda *a: 1 / 0)
    book, p = confirmed_book(), make_profile()
    look = client.get(f"/api/books/{book['id']}").json()["pages"][0]["second_look"]
    assert (look["status"], look["detail"]) == ("warn", "The second look could not run.")
    assert approve_all(book, p).status_code == 200


def test_the_sheet_carries_the_result():
    book, p = confirmed_book(), make_profile()
    row = client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}&level=1").json()["pages"][0]
    assert row["second_look"] == {"status": "pass", "answer": "rabbit", "detail": "stub"}


def test_command_fills_in_pages_confirmed_earlier(capsys):
    book = upload()
    db.pages.update_one({"_id": ObjectId(book["pages"][0]["id"])}, {"$set": {"confirmed": True}})
    assert second_look_tool.main([book["id"]]) == 0
    assert "rabbit" in capsys.readouterr().out
    assert client.get(f"/api/books/{book['id']}").json()["pages"][0]["second_look"]["status"] == "pass"
    assert second_look_tool.main([book["id"]]) == 0 and capsys.readouterr().out.strip() == ""
```

Also change Task 6's `test_sheet_rows`: `row["second_look"]["status"]` is now `"pass"`.

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_second_look.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement.** In confirm and confirm-all: after setting `confirmed`, call `start_second_look`; when it returns True add `run_second_look(page_id, subject_hash)` as a background task. Build the response from the page as stored before the task runs, so it shows pending.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: second look in the background, with a catch-up command"
```

---

### Task 10: Demo reset script

**Files:**
- Create: `api/tools/reset_demo.py`, `api/tests/test_reset_demo.py`

**Interfaces:**
- Produces: `python -m api.tools.reset_demo <book_id>` and `api.tools.reset_demo.main(argv: list[str]) -> int`.
  - For each page of the book: keep only candidates with `source == "auto"`; set `selected` to the index of `auto_subject_hash` among them (None if there is none); `subject_hash = auto_subject_hash`; `state = auto_state`; `reason = auto_reason`; `confirmed = False`; `omitted = False`; `second_look = None`.
  - A page whose `auto_state` is missing (still Processing, or interrupted) is left untouched and reported.
  - Delete every `approvals` document for the book's pages. Keep `checks`, profiles, page images and mask files.
  - Print one line per page (number, state, subject label or `none`) and the number of approvals removed. Exit 0.
  - Unknown or malformed book id: print `No book with id <id>.` and exit 1, changing nothing.

- [ ] **Step 1: Write the failing tests** in `api/tests/test_reset_demo.py`

```python
def test_reset_returns_the_book_to_just_processed(capsys):
    fresh = upload()
    book, p = fresh, make_profile()
    hard = book["pages"][1]                                           # needs_subject: the hard page
    client.post(f"/api/pages/{hard['id']}/subject", json={"point": [0.5, 0.5]})
    client.post(f"/api/pages/{book['pages'][2]['id']}/subject",
                json={"label": "frog", "outline": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.4]]})
    client.post(f"/api/pages/{book['pages'][0]['id']}/omit", json={"omitted": True})
    client.post(f"/api/books/{book['id']}/confirm-all")
    approve_all(book, p)
    other = confirmed_book(); approve_all(other, p)                   # a second book, untouched

    assert reset_demo.main([book["id"]]) == 0

    assert client.get(f"/api/books/{book['id']}").json() == fresh    # hard page is wrong again
    assert db.approvals.count_documents({}) == 1                      # only the other book's
    assert db.profiles.count_documents({}) == 1
    assert "needs_subject" in capsys.readouterr().out


def test_reset_keeps_the_mask_files():
    book = upload()
    client.post(f"/api/pages/{book['pages'][1]['id']}/subject", json={"point": [0.5, 0.5]})
    masks = lambda: sorted(p.name for p in (jobs.book_dir(ObjectId(book["id"])) / "masks").iterdir())
    before = masks()
    reset_demo.main([book["id"]])
    assert masks() == before


def test_reset_twice_is_the_same_as_once():
    book = upload()
    reset_demo.main([book["id"]]); reset_demo.main([book["id"]])
    assert client.get(f"/api/books/{book['id']}").json() == book


@pytest.mark.parametrize("book_id", ["nope", "65a000000000000000000009"])
def test_unknown_book_changes_nothing(book_id, capsys):
    upload()
    before = list(db.pages.find())
    assert reset_demo.main([book_id]) == 1
    assert "No book with id" in capsys.readouterr().out and list(db.pages.find()) == before
```

- [ ] **Step 2: Run them.** `.venv/bin/python -m pytest api/tests/test_reset_demo.py -q`. Expected: FAIL, module missing.

- [ ] **Step 3: Implement** `api/tools/reset_demo.py`.

- [ ] **Step 4: Run everything.** `.venv/bin/python -m pytest api contracts -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api && git commit -m "api: demo reset script"
```

---

### Task 11: The swap check (addition, not in the spec or build plan)

One command that tells Andrew, at the hour 4 and hour 7 swaps, exactly where a real module differs from what the API assumes. Overnight it runs against the stand-ins and must pass.

**Files:**
- Create: `api/tests/test_swap.py`

**Interfaces:**
- Consumes: `modules.pipeline`, `modules.display` (whatever `PIPELINE` and `RENDER` select), `helpers.make_pdf`.
- Produces: `PIPELINE=real RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q` as the swap command. Every assertion message names the assumption it checks.

- [ ] **Step 1: Write the tests.** A module-scoped fixture writes `make_pdf(2)` to `tmp/books/b1/source.pdf` and calls `modules.pipeline.rasterize(pdf, book_dir)`. Unlike `test_stubs.py`, nothing here may depend on stand-in values (three pages, gray, rectangles).

```python
def test_rasterize_follows_contract_3(assets, book_dir):
    for a in assets:
        assert a.image_path == str(book_dir / "pages" / f"{a.page_number}.png"), "out_dir must be the book folder"
        assert a.view_path == str(book_dir / "pages" / f"{a.page_number}_view.png")
        master, view = Image.open(a.image_path), Image.open(a.view_path)
        assert master.mode == "RGB" and master.size == (a.width, a.height)
        assert max(master.size) <= 3000 and max(view.size) == 1600
    assert [a.page_number for a in assets] == list(range(1, len(assets) + 1)), "pages are numbered from 1"


def test_process_page_never_raises_and_masks_follow_contract_3(assets, book_dir):
    for a in assets:
        result = modules.pipeline.process_page(a, book_dir)
        assert isinstance(result, PageResult)
        assert result.selected is None or 0 <= result.selected < len(result.candidates)
        for c in result.candidates:
            check_mask(c, a, book_dir)


def test_outline_is_used_exactly_as_drawn(assets, book_dir):
    a = assets[0]
    w, h = a.width, a.height
    points = [(0.2 * w, 0.2 * h), (0.6 * w, 0.2 * h), (0.6 * w, 0.6 * h), (0.2 * w, 0.6 * h)]
    c = modules.pipeline.mask_from_outline(a.image_path, "duck", points, book_dir)
    check_mask(c, a, book_dir)
    mask = Image.open(c.mask_path)
    assert mask.getpixel((int(0.4 * w), int(0.4 * h))) == 255 and mask.getpixel((int(0.9 * w), int(0.9 * h))) == 0
    assert (c.label, c.source, c.confidence) == ("duck", "manual", 1.0)


def test_click_returns_a_candidate(assets, book_dir):
    a = assets[0]
    c = modules.pipeline.segment_at_point(a.image_path, a.width / 2, a.height / 2, book_dir)
    check_mask(c, a, book_dir)
    assert c.source == "click"


@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_display_functions_return_contract_types(assets, book_dir, level):
    a = assets[0]
    c = modules.pipeline.mask_from_outline(a.image_path, "duck", SQUARE(a), book_dir)
    out = modules.display.render(a.image_path, a.view_path, c.mask_path, Settings(), level, a.text)
    image = Image.open(io.BytesIO(out))
    assert image.format == "WEBP" and max(image.size) == 1600
    png = modules.display.render(a.image_path, a.view_path, c.mask_path, Settings(), level, a.text, fmt="png")
    assert Image.open(io.BytesIO(png)).format == "PNG"
    assert isinstance(modules.display.run_checks(a.image_path, a.view_path, c.mask_path, Settings(), level, a.text), CheckResult)
    assert Image.open(io.BytesIO(modules.display.overlay(a.view_path, c.mask_path))).format == "WEBP"
    assert isinstance(modules.display.RENDER_VERSION, str) and modules.display.RENDER_VERSION
```

`check_mask(c, a, book_dir)` asserts: the file is at `book_dir/masks/{page_number}_{mask_hash}.png`; mode `L`; size equals the master's; `c.mask_hash == hash_bytes(file bytes)` (message: `"mask_hash must be contracts.hashing.hash_bytes of the file, or approvals will not match"`); and `0 <= x0 < x1 <= width`, `0 <= y0 < y1 <= height` for the box (message: `"boxes are master pixels"`).

`second_look` is not called here: with real code it spends the Gemini key.

- [ ] **Step 2: Run on the stand-ins.** `.venv/bin/python -m pytest api/tests/test_swap.py -q`. Expected: PASS. If the stand-in fails a check (for example the 1,600 px canvas), fix `api/stubs.py`, not the check.

- [ ] **Step 3: Run on the real modules, to record where things stand.**

Run: `PIPELINE=real RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q 2>&1 | tail -30`
Expected overnight: an import error or failures, because the real modules are not written. Do not fix anything. Paste the last 30 lines into `api/docs/overnight-notes.md` under `Needed from other owners`.

- [ ] **Step 4: Commit**

```bash
git add api && git commit -m "api: swap check that runs the contract tests against real or stand-in modules"
```

---

### Task 12: The joining check and the handoff notes (addition, not in the spec or build plan)

Thomas's own tests cannot be pointed at the real API: they run against Mock Service Worker with seeded data and fail on any unmocked request. So the joining check has two parts that live in `api/`: a shape test in Python, and Thomas's real typed client (`web/src/api.ts`, imported, never edited) driven through the whole demo against a running server.

**Files:**
- Create: `api/tests/test_shapes.py`, `api/joining/joining.test.ts`, `api/joining/vitest.config.ts`, `api/joining/run.sh`
- Modify: `api/docs/overnight-notes.md`

**Interfaces:**
- Consumes: every route; `web/src/api.ts` `createApiClient(base: string)`.
- Produces: `bash api/joining/run.sh`, which exits 0 only when the whole flow passed.

- [ ] **Step 1: Write the shape test** in `api/tests/test_shapes.py`

```python
def same_shape(example, actual, path="$"):
    """Every key the example shows is present, with the same JSON type unless either side is null."""
    if example is None or actual is None:
        return
    assert type(example) is type(actual) or {type(example), type(actual)} <= {int, float}, path
    if isinstance(example, dict):
        for key, value in example.items():
            assert key in actual, f"{path}.{key} is missing"
            same_shape(value, actual[key], f"{path}.{key}")
    elif isinstance(example, list) and example and actual:
        for i, item in enumerate(actual):
            same_shape(example[0], item, f"{path}[{i}]")


def test_every_json_route_has_the_agreed_shape():
    book, p = confirmed_book(), make_profile()
    approve = approve_all(book, p)
    page = book["pages"][0]["id"]
    q = f"?profile={p['id']}&level=1"
    seen = {
        "GET /api/books": client.get("/api/books"),
        "GET /api/books/{id}": client.get(f"/api/books/{book['id']}"),
        "PATCH /api/books/{id}": client.patch(f"/api/books/{book['id']}", json={"title": "T"}),
        "POST /api/pages/{id}/subject": client.post(f"/api/pages/{page}/subject", json={"candidate": 1}),
        "POST /api/pages/{id}/confirm": client.post(f"/api/pages/{page}/confirm"),
        "POST /api/pages/{id}/omit": client.post(f"/api/pages/{page}/omit", json={"omitted": False}),
        "POST /api/pages/{id}/retry": client.post(f"/api/pages/{book['pages'][2]['id']}/retry", json={}),
        "POST /api/books/{id}/confirm-all": client.post(f"/api/books/{book['id']}/confirm-all"),
        "GET /api/profiles": client.get("/api/profiles"),
        "PATCH /api/profiles/{id}": client.patch(f"/api/profiles/{p['id']}", json={"name": "May"}),
        "GET /api/books/{id}/sheet": client.get(f"/api/books/{book['id']}/sheet{q}"),
        "POST /api/books/{id}/approve": approve,
        "GET /api/reader/{book_id}": client.get(f"/api/reader/{book['id']}{q}"),
    }
    for key, response in seen.items():
        assert response.status_code == 200, key
        same_shape(EX[key]["response"], response.json(), key)


def test_error_bodies_have_the_agreed_shape():
    book, p = confirmed_book(), make_profile()
    stale = client.post(f"/api/books/{book['id']}/approve", json={"profile_id": p["id"], "level": 1,
        "pages": [{"page_id": book["pages"][0]["id"], "version": "000000000000", "decision": "approve"}]})
    same_shape(EX["POST /api/books/{id}/approve"]["errors"]["409"], stale.json())
    refused = client.get(f"/api/reader/page/{book['pages'][0]['id']}?profile={p['id']}&level=1&v=x")
    assert refused.json() == EX["GET /api/reader/page/{page_id}"]["errors"]["403"]
```

- [ ] **Step 2: Run it.** `.venv/bin/python -m pytest api/tests/test_shapes.py -q`. Expected: PASS. A failure here is a real mismatch with what Thomas's types expect: fix the route, not the example.

- [ ] **Step 3: Write the joining run**

`api/joining/run.sh`:
1. `npm --prefix web ci` if `web/node_modules` is missing (it is git-ignored; this edits no tracked file. Afterwards `git status --short web` must print nothing).
2. Write a 3-page PDF to a temp folder with `make_pdf`.
3. Start `uvicorn api.main:app --port 8765` with `MONGODB_URI=mongodb://localhost:27017/mirai_joining`, a temp `DATA_DIR`, `PIPELINE=stub`, `RENDER=stub`; wait until `GET /api/books` answers.
4. Run `JOINING_API=http://127.0.0.1:8765 JOINING_PDF=<path> npx --prefix web vitest run --root web --config ../api/joining/vitest.config.ts`.
5. Always stop the server and drop the `mirai_joining` database; exit with vitest's status.

`api/joining/vitest.config.ts`: `environment: 'node'`, `globals: true`, `include: ['../api/joining/*.test.ts']`, no setup files (so Thomas's mock server never starts).

`api/joining/joining.test.ts`: imports only `createApiClient` and `ApiError` from `../../web/src/api`, and uses `describe`, `it`, `expect` as globals (a bare `vitest` import cannot resolve from outside `web/`). One test, in demo order, each step through the client:

1. `uploadBook` with the PDF as a `File` → `state === 'ingesting'`.
2. Poll `getBook` every 200 ms, at most 50 times, until no page is `processing` → states are `ready, needs_subject, failed`.
3. Page 2: set the subject with `{ point: [0.5, 0.5] }` → `state === 'ready'`, the new candidate's `source === 'click'`.
4. Page 3: set the subject with `{ label: 'frog', outline: [[0.1,0.1],[0.5,0.1],[0.5,0.4],[0.1,0.4]] }` → selected candidate `box` equals `[0.1, 0.1, 0.5, 0.4]`.
5. Overlay for page 1 → a `Blob` whose type starts with `image/`.
6. Confirm all → 3 pages.
7. Create Maya (level 1, `#E53935`) and Leo (level 2, `#FDD835`, `#1E88E5`); preview page 1 with Leo's unsaved settings → an image.
8. Sheet for Maya at level 1 → 3 rows with a `version`; fetch one row's render → an image.
9. Edit Maya's color, then approve with the old versions → the client's conflict outcome (`ok === false`), `changed.length === 3`.
10. Reload the sheet, approve → `ok === true`, 3 approvals.
11. Reader manifest for Maya → 3 pages, `versions` has Maya `fully_approved === true` and Leo `false`; fetch page 1's image → an image.
12. Reader page for Leo at level 2 with Maya's token → rejects with an `ApiError` whose `status === 403`.

Use the client's own method names, read from `web/src/api.ts` lines 200 to 305; do not guess them.

- [ ] **Step 4: Run it.** `bash api/joining/run.sh`. Expected: `1 passed`, exit 0, and `git status --short web` prints nothing.

Give this at most 30 minutes of fixing on the tooling side (module resolution, `File` and `FormData` under Node). If the harness itself cannot be made to run, keep the files, write exactly what failed under `Not done`, and rely on Step 1. If it runs and a step fails because the API and the client disagree, and the fix is in `api/` without changing an agreed example, fix it with a test in the matching task's test file. If the fix would be in `web/` or the examples, write it under `Needed from other owners` and mark that step `it.skip` with the reason.

- [ ] **Step 5: Run one real server by hand, with a restart in the middle**

```bash
MONGODB_URI=mongodb://localhost:27017/mirai DATA_DIR=./data .venv/bin/python -m uvicorn api.main:app --port 8000
```

Upload a PDF with `curl -F file=@<pdf> localhost:8000/api/books`, set one page to `processing` in the database with `mongosh`, stop the server, start it again, and confirm `GET /api/books/{id}` shows that page `failed` with reason `interrupted, retry`. Expected: build plan hours 5 to 6 "Done when": a killed server restarts with nothing stuck.

- [ ] **Step 6: Finish the notes.** Fill `api/docs/overnight-notes.md`:
- `Decisions`: the ten decisions from the top of this plan, each in one line, with the test that pins it.
- `Needed from other owners`: the Task 11 Step 3 output; anything found in Step 4; for Bryan, that `compose.yaml` needs a MongoDB service or an Atlas URI and that `api/requirements.txt` now includes `pymupdf`; for Kevin, that his four reader tests still need to run as the outside check.
- `Not done`: anything cut, plus what was deliberately left for people: Atlas, the live deploy, the hour 4 and hour 7 swaps, the alignment check on the tablet, the second-look run over the backup books.
- The final test count and the output of `git log --oneline main..andrew`.

- [ ] **Step 7: Run everything one last time, then commit**

Run: `.venv/bin/python -m pytest api contracts -q && .venv/bin/python -c "import api.main" && git status --short`
Expected: all pass; the only changes are under `api/`.

```bash
git add api && git commit -m "api: joining check against the web client, shape tests, overnight notes"
```
