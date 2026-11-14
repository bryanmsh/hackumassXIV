import pytest

from api.tests.helpers import EX, approve_all, client, confirmed_book, make_profile

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
    assert r.headers["content-type"] == "image/webp"


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
    "profile={p}&level=9&v={v}",
    "profile={p}&level=1&v=",                  # empty token
    "profile={p}&level=1.0&v={v}",             # level is not a whole number
    "level=1&v={v}"])                          # no profile
def test_every_other_request_is_refused(query):
    book, p, page = approved_page()
    r = client.get(f"/api/reader/page/{page['page_id']}?" + query.format(p=p["id"], v=page["v"]))
    assert r.status_code == 403 and r.json() == {"detail": "not approved"}
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
