import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

from api import db, modules, stubs
from api.main import app
from api.tests.helpers import client, upload

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


def test_pipeline_error_on_click_leaves_the_page_unchanged(monkeypatch, caplog):
    page = upload()["pages"][0]
    monkeypatch.setattr(modules.pipeline, "segment_at_point", lambda *a: 1 / 0)
    assert subject(page, {"point": [0.5, 0.5]}).status_code == 502
    assert any("cut-out failed for page" in r.getMessage() and r.exc_info for r in caplog.records)
    assert client.get(f"/api/books/{page['book_id']}").json()["pages"][0] == page


def test_a_click_never_erases_a_candidate_added_meanwhile(monkeypatch):
    page = upload()["pages"][1]
    real = modules.pipeline.segment_at_point

    def slow_click(path, x, y, out):
        found = real(path, x, y, out)
        stored = db.pages.find_one({"_id": ObjectId(page["id"])})
        other = {**stored["candidates"][0], "mask_hash": "added-meanwhile", "source": "click"}
        db.pages.update_one({"_id": stored["_id"]}, {"$push": {"candidates": other}})
        return found

    monkeypatch.setattr(modules.pipeline, "segment_at_point", slow_click)
    r = subject(page, {"point": [0.5, 0.1]}).json()
    hashes = [c["mask_hash"] for c in r["candidates"]]
    assert len(hashes) == 4 and "added-meanwhile" in hashes
    assert r["selected"] == 3 and r["subject_hash"] == hashes[3]
    assert db.pages.find_one({"_id": ObjectId(page["id"])})["selected"] == 3


def test_a_click_overlapping_a_retry_changes_nothing(monkeypatch):
    page = upload()["pages"][1]
    real = modules.pipeline.segment_at_point

    def click_during_retry(path, x, y, out):
        found = real(path, x, y, out)
        db.pages.update_one({"_id": ObjectId(page["id"])}, {"$set": {"state": "processing"}})
        return found

    monkeypatch.setattr(modules.pipeline, "segment_at_point", click_during_retry)
    assert subject(page, {"point": [0.5, 0.1]}).status_code == 409
    stored = db.pages.find_one({"_id": ObjectId(page["id"])})
    assert stored["state"] == "processing" and len(stored["candidates"]) == 2


def test_confirm_needs_a_subject():
    page = upload()["pages"][1]
    assert client.post(f"/api/pages/{page['id']}/confirm").status_code == 409


def test_confirm_all_confirms_only_ready_pages_not_left_out():
    book = upload()                                  # ready, needs_subject, failed
    extra = db.pages.find_one({"_id": ObjectId(book["pages"][0]["id"])})   # a fourth ready page
    extra.update(_id=ObjectId(), number=4)
    db.pages.insert_one(extra)
    client.post(f"/api/pages/{extra['_id']}/omit", json={"omitted": True})
    done = client.post(f"/api/books/{book['id']}/confirm-all").json()
    assert [p["number"] for p in done] == [1] and done[0]["confirmed"] is True
    assert client.post(f"/api/books/{book['id']}/confirm-all").json() == []


def test_omit_and_bring_back():
    page = upload()["pages"][0]
    assert client.post(f"/api/pages/{page['id']}/omit", json={"omitted": True}).json()["omitted"] is True
    assert client.post(f"/api/pages/{page['id']}/omit", json={"omitted": False}).json()["omitted"] is False


def test_retry_reruns_a_failed_page(monkeypatch):
    page = upload()["pages"][2]
    real = stubs.process_page
    monkeypatch.setattr(modules.pipeline, "process_page", lambda asset, out, force=False:
                        real(asset.model_copy(update={"page_number": 1}), out))
    r = client.post(f"/api/pages/{page['id']}/retry", json={})
    assert r.status_code == 200 and r.json()["state"] == "processing"
    after = client.get(f"/api/books/{page['book_id']}").json()["pages"][2]
    assert (after["state"], after["reason"], after["selected"]) == ("ready", None, 0)


def test_retry_rules(monkeypatch):
    pages = upload()["pages"]
    assert client.post(f"/api/pages/{pages[0]['id']}/retry", json={}).status_code == 409   # ready
    db.pages.update_one({"_id": ObjectId(pages[2]["id"])}, {"$set": {"state": "unsupported"}})
    assert client.post(f"/api/pages/{pages[2]['id']}/retry", json={}).status_code == 409   # needs force
    forced, real = [], stubs.process_page
    monkeypatch.setattr(modules.pipeline, "process_page", lambda asset, out, force=False:
                        forced.append(force) or real(asset, out))
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


def _change_subject_in_database(page_id, candidate):
    """What a slow click's write does: another subject, selected and not confirmed."""
    stored = db.pages.find_one({"_id": ObjectId(page_id)})
    db.pages.update_one({"_id": stored["_id"]}, {"$set": {
        "selected": candidate, "subject_hash": stored["candidates"][candidate]["mask_hash"],
        "confirmed": False}})


def test_confirm_never_lands_on_a_subject_the_teacher_did_not_see(monkeypatch):
    from api.routes import pages as pages_routes
    page = upload()["pages"][0]
    real = pages_routes._find_page

    def read_then_change(page_id):
        found = real(page_id)
        _change_subject_in_database(page["id"], 1)       # lands between the read and the write
        return found

    monkeypatch.setattr(pages_routes, "_find_page", read_then_change)
    assert client.post(f"/api/pages/{page['id']}/confirm").status_code == 409
    stored = db.pages.find_one({"_id": ObjectId(page["id"])})
    assert stored["confirmed"] is False and stored["selected"] == 1
    assert stored["second_look"] is None


def test_confirm_all_skips_a_page_whose_subject_changed_after_it_was_read(monkeypatch):
    book = upload()
    real_find = db.pages.find

    def find_then_change(*args, **kwargs):
        waiting = list(real_find(*args, **kwargs).sort("number", 1))
        monkeypatch.undo()                               # the change below reads through find too
        _change_subject_in_database(book["pages"][0]["id"], 1)
        return type("Waiting", (), {"sort": lambda self, *a: waiting})()

    monkeypatch.setattr(db.pages, "find", find_then_change)
    assert client.post(f"/api/books/{book['id']}/confirm-all").json() == []
    stored = db.pages.find_one({"_id": ObjectId(book["pages"][0]["id"])})
    assert stored["confirmed"] is False and stored["second_look"] is None


def test_relabelling_the_same_outline_corrects_the_label():
    page = upload()["pages"][2]
    subject(page, {"label": "dgo", "outline": OUTLINE})
    r = subject(page, {"label": "dog", "outline": OUTLINE}).json()
    assert len(r["candidates"]) == 1 and r["candidates"][r["selected"]]["label"] == "dog"
    assert db.pages.find_one({"_id": ObjectId(page["id"])})["candidates"][0]["label"] == "dog"


def test_an_outline_never_renames_an_automatic_candidate(monkeypatch):
    page = upload()["pages"][0]
    auto = db.pages.find_one({"_id": ObjectId(page["id"])})["candidates"][0]
    real = modules.pipeline.mask_from_outline
    monkeypatch.setattr(modules.pipeline, "mask_from_outline", lambda *a: real(*a).model_copy(
        update={"mask_hash": auto["mask_hash"]}))
    r = subject(page, {"label": "something else", "outline": OUTLINE}).json()
    assert r["candidates"][0]["label"] == auto["label"] and r["candidates"][0]["source"] == "auto"
