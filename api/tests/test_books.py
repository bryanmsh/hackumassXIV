import json

from api import db, jobs, modules, settings
from api.tests.helpers import EX, client, make_pdf, upload
from contracts.types import PageResult


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


def test_failure_reason_hides_server_paths(monkeypatch):
    def lost(asset, out_dir, force=False):
        raise FileNotFoundError(f"{settings.DATA_DIR}/books/x/pages/1.png")
    monkeypatch.setattr(modules.pipeline, "process_page", lost)
    page = upload()["pages"][0]
    assert page["state"] == "failed" and str(settings.DATA_DIR) not in page["reason"]


def test_failure_with_no_message_names_the_exception(monkeypatch):
    def silent(asset, out_dir, force=False):
        raise RuntimeError()
    monkeypatch.setattr(modules.pipeline, "process_page", silent)
    assert upload()["pages"][0]["reason"] == "RuntimeError"


def test_a_bad_result_fails_the_page_not_the_book(monkeypatch):
    real = modules.pipeline.process_page
    def bad(asset, out_dir, force=False):
        if asset.page_number == 1:
            return PageResult.model_construct(state="ready", page_kind="single", candidates=[],
                                              selected=5, reason=None)
        return real(asset, out_dir, force)
    monkeypatch.setattr(modules.pipeline, "process_page", bad)
    pages = upload()["pages"]
    assert pages[0]["state"] == "failed" and pages[0]["reason"] == "list index out of range"
    assert [p["state"] for p in pages[1:]] == ["needs_subject", "failed"]


def test_rasterize_failure_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(modules.pipeline, "rasterize", lambda *a: 1 / 0)
    upload()
    assert "rasterize failed for book" in caplog.text


def test_second_look_is_hidden_without_a_subject():
    from api import views
    upload()
    doc = db.pages.find_one({"number": 2})
    doc["second_look"] = {"subject_hash": None, "status": "pass", "answer": "x", "detail": None}
    assert doc["subject_hash"] is None and views.page_json(doc)["second_look"] is None


def test_failure_reason_keeps_words_that_contain_a_relative_data_dir(monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(settings, "DATA_DIR", Path("data"))
    assert jobs.failure_reason(RuntimeError("database is down")) == "database is down"
