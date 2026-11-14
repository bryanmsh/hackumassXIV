from bson import ObjectId

from api import db, jobs, modules
from api.tests.helpers import approve_all, client, make_profile, upload


def test_rerun_asks_about_every_page_and_a_confirmed_page_keeps_its_subject(monkeypatch):
    book = upload()
    ready, unpicked, failed = book["pages"]
    client.post(f"/api/pages/{ready['id']}/subject", json={"candidate": 1})  # not the pipeline's choice
    confirmed = client.post(f"/api/pages/{ready['id']}/confirm").json()
    profile = make_profile()
    assert approve_all(client.get(f"/api/books/{book['id']}").json(), profile).status_code == 200
    made = client.post(f"/api/pages/{unpicked['id']}/subject", json={"point": [0.5, 0.5]}).json()
    ran = []
    real = jobs.process_one
    monkeypatch.setattr(jobs, "process_one", lambda page_id, force=False: ran.append(str(page_id)) or real(page_id, force))

    r = client.post(f"/api/books/{book['id']}/rerun")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [p["id"] for p in book["pages"]] == ran
    assert {p["state"] for p in r.json()} == {"processing"}
    after = client.get(f"/api/books/{book['id']}").json()["pages"]
    assert "processing" not in {p["state"] for p in after}
    # confirmed: same subject, still confirmed, still readable
    assert (after[0]["selected"], after[0]["subject_hash"], after[0]["confirmed"], after[0]["state"]) == \
           (1, confirmed["subject_hash"], True, "ready")
    manifest = client.get(f"/api/reader/{book['id']}?profile={profile['id']}&level=1").json()
    assert [p["page_id"] for p in manifest["pages"]] == [ready["id"]]
    # not confirmed: the teacher's click is still in the list; the subject is the pipeline's answer again
    assert made["candidates"][made["selected"]]["mask_hash"] in [c["mask_hash"] for c in after[1]["candidates"]]
    assert (after[1]["state"], after[1]["selected"]) == (unpicked["state"], unpicked["selected"])


def test_a_confirmed_page_survives_a_rerun_that_fails(monkeypatch):
    page = upload()["pages"][0]
    confirmed = client.post(f"/api/pages/{page['id']}/confirm").json()
    monkeypatch.setattr(modules.pipeline, "process_page", lambda *a: 1 / 0)
    client.post(f"/api/books/{page['book_id']}/rerun")
    after = client.get(f"/api/books/{page['book_id']}").json()["pages"][0]
    assert (after["state"], after["subject_hash"], after["confirmed"], after["reason"]) == \
           ("ready", confirmed["subject_hash"], True, None)


def test_rerun_skips_pages_left_out_or_already_processing():
    book = upload()
    first, second, third = (ObjectId(p["id"]) for p in book["pages"])
    client.post(f"/api/pages/{first}/omit", json={"omitted": True})
    db.pages.update_one({"_id": second}, {"$set": {"state": "processing"}})
    assert [p["id"] for p in client.post(f"/api/books/{book['id']}/rerun").json()] == [str(third)]


def test_rerun_refuses_an_unknown_book():
    assert client.post(f"/api/books/{ObjectId()}/rerun").status_code == 404
