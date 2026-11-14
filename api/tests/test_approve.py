from api import db
from api.tests.helpers import EX, client, confirmed_book, make_profile, upload

send = lambda book, p, rows, level=1, decision="approve": client.post(
    f"/api/books/{book['id']}/approve", json={
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
    book, p = confirmed_book(), make_profile()
    second = book["pages"][1]["id"]                       # needs_subject: give it a subject and confirm it
    client.post(f"/api/pages/{second}/subject", json={"candidate": 0})
    client.post(f"/api/pages/{second}/confirm")
    first, other = [r for r in rows(book, p) if r["version"]]
    client.post(f"/api/pages/{first['page_id']}/subject", json={"candidate": 1})
    client.post(f"/api/pages/{first['page_id']}/confirm")
    r = send(book, p, [first, other])
    assert r.status_code == 409 and r.json()["detail"] == "look again"
    assert r.json()["changed"] == [{"page_id": first["page_id"], "sent": first["version"],
                                    "current": rows(book, p)[0]["version"]}]
    assert [a["page_id"] for a in r.json()["recorded"]] == [other["page_id"]]
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


def test_a_page_id_that_is_malformed_or_unknown_is_look_again_not_404():
    book, p = confirmed_book(), make_profile()
    fake = [{"page_id": "not-an-id", "version": "000000000000"},
            {"page_id": "65b000000000000000000009", "version": "000000000000"}]
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
    assert send(book, {"id": "not-an-id"}, [row]).status_code == 404
    assert client.post("/api/books/65a000000000000000000009/approve", json={
        "profile_id": p["id"], "level": 1, "pages": []}).status_code == 404
