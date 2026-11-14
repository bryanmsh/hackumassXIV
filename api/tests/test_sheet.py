from datetime import datetime, timedelta, timezone

from bson import ObjectId

from api import db, modules, versions
from api.tests.helpers import EX, client, confirmed_book, make_profile
from contracts.hashing import version_token

sheet = lambda book, p, level=1: client.get(f"/api/books/{book['id']}/sheet?profile={p['id']}&level={level}")


def test_sheet_rows():
    book, p = confirmed_book(), make_profile()
    body = sheet(book, p).json()
    example = EX["GET /api/books/{id}/sheet"]["response"]
    assert set(body) == set(example) and (body["level"], body["render_version"]) == (1, modules.display.RENDER_VERSION)
    row, unpicked, failed = body["pages"]
    assert set(row) == set(example["pages"][0])
    assert row["version"] == version_token(book["pages"][0]["subject_hash"], p["settings_hash"], 1, modules.display.RENDER_VERSION)
    assert (row["label"], row["source"], row["approval"]) == ("rabbit", "auto", "none")
    assert row["checks"]["fidelity"]["status"] == "pass" and row["second_look"]["status"] == "pass"
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


def test_a_check_that_raises_blanks_only_its_row(monkeypatch):
    def broken(*args):
        raise RuntimeError("boom")
    monkeypatch.setattr(modules.display, "run_checks", broken)
    book, p = confirmed_book(), make_profile()
    row = sheet(book, p).json()["pages"][0]
    assert row["checks"] is None and row["version"] is not None
    assert db.checks.count_documents({}) == 0


def test_approval_state_follows_the_newest_record_for_the_exact_version():
    page_id, profile_id = ObjectId(), ObjectId()
    version = versions.Version("a" * 12, "b" * 12, 1, "stub-1")
    now = datetime.now(timezone.utc)

    def record(decision, minutes, **over):
        fields = {"page_id": page_id, "profile_id": profile_id, "subject_hash": version.subject_hash,
                  "settings_hash": version.settings_hash, "level": version.level,
                  "render_version": version.render_version, "decision": decision,
                  "at": now + timedelta(minutes=minutes)}
        db.approvals.insert_one({**fields, **over})

    assert versions.approval_state(page_id, profile_id, version) == "none"
    assert versions.approval_state(page_id, profile_id, None) == "none"
    record("approve", 0)
    assert versions.approval_state(page_id, profile_id, version) == "approved"
    record("reject", 1)
    assert versions.approval_state(page_id, profile_id, version) == "rejected"
    record("approve", 2, level=2)                      # another look does not count
    assert versions.approval_state(page_id, profile_id, version) == "rejected"
    assert versions.approval_state(page_id, profile_id, version._replace(settings_hash="c" * 12)) == "none"
    assert versions.approval_state(page_id, ObjectId(), version) == "none"


def test_decisions_in_the_same_millisecond_are_ordered_by_id():
    version = versions.Version("a" * 12, "b" * 12, 1, "stub-1")
    at = datetime.now(timezone.utc)
    for physical_order in ("older first", "newer first"):       # the answer must not depend on where Mongo put them
        page_id, profile_id = ObjectId(), ObjectId()
        older, newer = sorted((ObjectId(), ObjectId()))
        docs = [{"_id": older, "decision": "approve"}, {"_id": newer, "decision": "reject"}]
        for doc in docs if physical_order == "older first" else reversed(docs):
            db.approvals.insert_one({**doc, "page_id": page_id, "profile_id": profile_id,
                                     "subject_hash": version.subject_hash, "settings_hash": version.settings_hash,
                                     "level": version.level, "render_version": version.render_version, "at": at})
        assert versions.approval_state(page_id, profile_id, version) == "rejected"
