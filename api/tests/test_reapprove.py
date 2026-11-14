import pytest

from api import db, modules
from api.tests.helpers import approve_all, client, confirmed_book, make_profile
from api.tools import reapprove

manifest = lambda book, p: client.get(f"/api/reader/{book['id']}?profile={p['id']}&level=1").json()
rows = lambda book, p: client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}&level=1").json()["pages"]
decide = lambda book, p, row, decision: client.post(f"/api/books/{book['id']}/approve", json={
    "profile_id": p["id"], "level": 1,
    "pages": [{"page_id": row["page_id"], "version": row["version"], "decision": decision}]})


@pytest.fixture
def old(monkeypatch):
    """The render version the books were approved under. The display code is then one version on."""
    version = modules.display.RENDER_VERSION
    monkeypatch.setattr(modules.display, "RENDER_VERSION", version)   # put back after the test
    return version


def new_render_version():
    modules.display.RENDER_VERSION = "next"


def test_reapprove_brings_a_book_back_under_the_new_render_version(old, capsys):
    book, p = confirmed_book(), make_profile()
    assert approve_all(book, p).status_code == 200
    new_render_version()
    assert manifest(book, p)["pages"] == []

    assert reapprove.main([book["id"], old]) == 0

    pages = manifest(book, p)["pages"]
    assert [x["number"] for x in pages] == [1]
    assert client.get(pages[0]["image_url"]).status_code == 200
    out = capsys.readouterr().out
    assert f"page 1, Maya, look 1, approve: {old} -> next" in out     # every record written is printed
    assert f"1 approvals copied from {old} to next." in out
    copy = db.approvals.find_one({"render_version": "next"})
    assert copy["copied_from"] == old                                 # told apart from a teacher's click


def test_only_the_named_book_is_copied(old):
    book, other, p = confirmed_book(), confirmed_book(), make_profile()
    approve_all(book, p); approve_all(other, p)
    new_render_version()
    reapprove.main([book["id"], old])
    assert len(manifest(book, p)["pages"]) == 1 and manifest(other, p)["pages"] == []
    assert db.approvals.count_documents({}) == 3


def test_running_it_twice_writes_nothing_more(old, capsys):
    book, p = confirmed_book(), make_profile()
    approve_all(book, p)
    new_render_version()
    reapprove.main([book["id"], old])
    assert reapprove.main([book["id"], old]) == 0
    assert db.approvals.count_documents({}) == 2
    assert f"0 approvals copied from {old} to next." in capsys.readouterr().out


def test_the_newest_decision_is_the_one_copied(old):
    book, p = confirmed_book(), make_profile()
    approve_all(book, p)
    decide(book, p, rows(book, p)[0], "reject")
    new_render_version()
    reapprove.main([book["id"], old])
    assert rows(book, p)[0]["approval"] == "rejected"
    assert db.approvals.count_documents({"render_version": "next"}) == 1


def test_a_decision_already_made_under_the_new_version_is_kept(old):
    book, p = confirmed_book(), make_profile()
    approve_all(book, p)
    new_render_version()
    decide(book, p, rows(book, p)[0], "reject")       # the teacher looked again and said no
    reapprove.main([book["id"], old])
    assert rows(book, p)[0]["approval"] == "rejected"
    assert db.approvals.count_documents({}) == 2


@pytest.mark.parametrize("argv", [[], ["nope", "stub-1"], ["65a000000000000000000009", "stub-1"], ["{book}"]])
def test_a_bad_call_writes_nothing(argv, old, capsys):
    book, p = confirmed_book(), make_profile()
    approve_all(book, p)
    new_render_version()
    assert reapprove.main([a.format(book=book["id"]) for a in argv]) == 1
    assert db.approvals.count_documents({}) == 1
    assert capsys.readouterr().out


def test_a_version_with_no_approvals_says_which_ones_exist(old, capsys):
    book, p = confirmed_book(), make_profile()
    approve_all(book, p)
    new_render_version()
    assert reapprove.main([book["id"], "typo"]) == 1
    out = capsys.readouterr().out
    assert "No approvals" in out and old in out
    assert db.approvals.count_documents({}) == 1


def test_the_current_version_is_not_copied_onto_itself(old, capsys):
    book, p = confirmed_book(), make_profile()
    approve_all(book, p)
    assert reapprove.main([book["id"], old]) == 1
    assert db.approvals.count_documents({}) == 1
    assert "already" in capsys.readouterr().out
