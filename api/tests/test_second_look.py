from bson import ObjectId

from api import db, jobs, modules
from api.tests.helpers import approve_all, client, confirmed_book, make_profile, upload
from api.tools import second_look as second_look_tool


def test_confirm_shows_pending_then_the_result():
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
    book = upload()
    # the stand-in always makes three pages: ready, needs a subject, failed
    client.post(f"/api/pages/{book['pages'][1]['id']}/subject", json={"candidate": 0})
    client.post(f"/api/books/{book['id']}/confirm-all")
    pages = client.get(f"/api/books/{book['id']}").json()["pages"]
    assert [p["second_look"]["status"] if p["second_look"] else None for p in pages] == \
           ["pass", "pass", None]


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


def test_command_refuses_an_unknown_book(capsys):
    for bad in ("nope", str(ObjectId())):
        assert second_look_tool.main([bad]) == 1
        assert capsys.readouterr().out.strip() == f"No book with id {bad}."
