"""The reader shows approved versions only, checked from outside over HTTP.

1. An approved page is served.
2. A page that was never approved is refused.
3. A page approved and then changed is refused.
4. An approval sent for a version that is no longer current gets "look again".

Subjects are drawn as outlines, which need no AI, so these pass with the real pipeline or the
stand-ins.
"""
import json
import secrets
import time

import pymupdf
import pytest

SQUARE = [(0.30, 0.30), (0.70, 0.30), (0.70, 0.70), (0.30, 0.70)]
SMALLER = [(0.40, 0.40), (0.60, 0.40), (0.60, 0.60), (0.40, 0.60)]
SETTINGS = {"colors": ["#E53935"], "background": "#000000", "size": "medium",
            "position": "center", "text_mode": "off", "outline": "off"}


def make_pdf(pages: int = 2) -> bytes:
    doc = pymupdf.open()
    for n in range(1, pages + 1):
        page = doc.new_page(width=800, height=600)
        page.draw_rect(pymupdf.Rect(260, 200, 540, 400), color=(0.8, 0.1, 0.1), fill=(0.9, 0.2, 0.2))
        page.insert_text((72, 560), f"The red square is on page {n}.", fontsize=24)
    data = doc.tobytes()
    doc.close()
    return data


def upload_and_wait(api, timeout: float = 240) -> dict:
    credits = {"author": "Test", "illustrator": "Test", "publisher": "Test",
               "source": "generated", "license": "CC BY 4.0"}
    r = api.post("/api/books", files={"file": ("zz-test.pdf", make_pdf(), "application/pdf")},
                 data={"title": f"zz-test reader {secrets.token_hex(3)}", "credits": json.dumps(credits)})
    assert r.status_code == 200, r.text
    book_id = r.json()["book_id"]
    deadline = time.monotonic() + timeout
    while True:
        book = api.get(f"/api/books/{book_id}").json()
        busy = book["state"] == "ingesting" or any(p["state"] == "processing" for p in book["pages"])
        if not busy and book["pages"]:
            return book
        assert time.monotonic() < deadline, f"book still processing: {book['state']}"
        time.sleep(1)


def outline_and_confirm(api, page_id: str, outline=SQUARE, label: str = "square") -> dict:
    r = api.post(f"/api/pages/{page_id}/subject", json={"label": label, "outline": outline})
    assert r.status_code == 200, r.text
    r = api.post(f"/api/pages/{page_id}/confirm")
    assert r.status_code == 200, r.text
    return r.json()


def make_profile(api, **over) -> dict:
    body = {"name": f"zz-test {secrets.token_hex(3)}", "level": 1, "settings": SETTINGS,
            "contrast_override_note": None, **over}
    r = api.post("/api/profiles", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def sheet_row(api, book_id: str, profile_id: str, page_id: str, level: int = 1) -> dict:
    r = api.get(f"/api/books/{book_id}/sheet", params={"profile": profile_id, "level": level})
    assert r.status_code == 200, r.text
    return next(row for row in r.json()["pages"] if row["page_id"] == page_id)


def approve(api, book_id: str, profile_id: str, page_id: str, version: str, level: int = 1):
    return api.post(f"/api/books/{book_id}/approve", json={
        "profile_id": profile_id, "level": level,
        "pages": [{"page_id": page_id, "version": version, "decision": "approve"}]})


def manifest(api, book_id: str, profile_id: str, level: int = 1) -> dict:
    r = api.get(f"/api/reader/{book_id}", params={"profile": profile_id, "level": level})
    assert r.status_code == 200, r.text
    return r.json()


def assert_refused(api, url: str):
    r = api.get(url)
    assert r.status_code == 403, f"{url} answered {r.status_code}"
    assert r.json() == {"detail": "not approved"}


@pytest.fixture
def book_page_profile(api):
    """A book whose first page has a confirmed, hand-outlined subject, and a fresh profile."""
    book = upload_and_wait(api)
    page_id = book["pages"][0]["id"]
    outline_and_confirm(api, page_id)
    return book["id"], page_id, make_profile(api)


@pytest.fixture
def approved(api, book_page_profile):
    book_id, page_id, profile = book_page_profile
    row = sheet_row(api, book_id, profile["id"], page_id)
    assert row["version"], row
    r = approve(api, book_id, profile["id"], page_id, row["version"])
    assert r.status_code == 200, r.text
    shown = manifest(api, book_id, profile["id"])["pages"]
    assert [p["page_id"] for p in shown] == [page_id]
    return book_id, page_id, profile, shown[0]


def test_an_approved_page_is_served(api, approved):
    _, _, _, page = approved
    r = api.get(page["image_url"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/webp"
    assert r.content[:4] == b"RIFF" and r.content[8:12] == b"WEBP"
    assert "no-store" in r.headers["cache-control"]


def test_a_never_approved_page_is_refused(api, book_page_profile):
    book_id, page_id, profile = book_page_profile
    row = sheet_row(api, book_id, profile["id"], page_id)
    assert row["version"] and row["approval"] != "approved"
    assert_refused(api, f"/api/reader/page/{page_id}?profile={profile['id']}&level=1&v={row['version']}")
    m = manifest(api, book_id, profile["id"])
    assert m["pages"] == []
    assert page_id in [s["page_id"] for s in m["skipped"]]


CHANGES = {
    "profile colors": lambda api, page_id, profile: api.patch(
        f"/api/profiles/{profile['id']}", json={"settings": {**SETTINGS, "colors": ["#FDD835"]}}),
    "subject": lambda api, page_id, profile: outline_and_confirm(api, page_id, SMALLER, "small square"),
}


@pytest.mark.parametrize("change", CHANGES)
def test_approved_then_changed_is_refused(api, approved, change):
    book_id, page_id, profile, page = approved
    CHANGES[change](api, page_id, profile)
    assert_refused(api, page["image_url"])
    assert manifest(api, book_id, profile["id"])["pages"] == []
    fresh = sheet_row(api, book_id, profile["id"], page_id)
    assert fresh["version"] != page["v"]
    assert_refused(api, f"/api/reader/page/{page_id}?profile={profile['id']}&level=1&v={fresh['version']}")


def test_a_stale_approval_gets_look_again(api, book_page_profile):
    book_id, page_id, profile = book_page_profile
    shown = sheet_row(api, book_id, profile["id"], page_id)
    api.patch(f"/api/profiles/{profile['id']}", json={"settings": {**SETTINGS, "background": "#FFFFFF"}})
    r = approve(api, book_id, profile["id"], page_id, shown["version"])
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["detail"] == "look again"
    assert [c["page_id"] for c in body["changed"]] == [page_id]
    assert body["recorded"] == []
    assert manifest(api, book_id, profile["id"])["pages"] == []
    current = sheet_row(api, book_id, profile["id"], page_id)
    assert current["approval"] != "approved"
    assert_refused(api, f"/api/reader/page/{page_id}?profile={profile['id']}&level=1&v={current['version']}")
