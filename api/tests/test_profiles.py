import pytest

from api import modules
from api.tests.helpers import EX, client, upload

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
