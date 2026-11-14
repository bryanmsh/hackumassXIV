from bson import ObjectId

from api import db, jobs
from api.tests.helpers import client, upload


def test_rerun_processes_open_pages_and_leaves_settled_ones(monkeypatch):
    book = upload()
    ready, unpicked, failed = book["pages"]
    client.post(f"/api/pages/{ready['id']}/confirm")
    made = client.post(f"/api/pages/{unpicked['id']}/subject", json={"point": [0.5, 0.5]}).json()
    ran = []
    real = jobs.process_one
    monkeypatch.setattr(jobs, "process_one", lambda page_id, force=False: ran.append(str(page_id)) or real(page_id, force))
    r = client.post(f"/api/books/{book['id']}/rerun")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [unpicked["id"], failed["id"]] == ran
    assert {p["state"] for p in r.json()} == {"processing"}
    after = client.get(f"/api/books/{book['id']}").json()["pages"]
    assert after[0] == client.get(f"/api/books/{book['id']}").json()["pages"][0] and after[0]["confirmed"] is True
    # the teacher's click suggestion is still in the list; the subject is the pipeline's answer again
    assert made["candidates"][made["selected"]]["mask_hash"] in [c["mask_hash"] for c in after[1]["candidates"]]
    assert (after[1]["state"], after[1]["selected"]) == (unpicked["state"], unpicked["selected"])
    assert "processing" not in {p["state"] for p in after}


def test_rerun_skips_pages_left_out_or_already_processing():
    book = upload()
    first, second, third = (ObjectId(p["id"]) for p in book["pages"])
    client.post(f"/api/pages/{first}/omit", json={"omitted": True})
    db.pages.update_one({"_id": second}, {"$set": {"state": "processing"}})
    assert [p["id"] for p in client.post(f"/api/books/{book['id']}/rerun").json()] == [str(third)]


def test_rerun_refuses_an_unknown_book():
    assert client.post(f"/api/books/{ObjectId()}/rerun").status_code == 404
