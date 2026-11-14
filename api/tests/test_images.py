from api import db, modules
from api.tests.helpers import client, upload


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
