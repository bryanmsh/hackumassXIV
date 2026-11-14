import pytest
from bson import ObjectId

from api import db, jobs
from api.tests.helpers import approve_all, client, confirmed_book, make_profile, upload
from api.tools import reset_demo


def test_reset_returns_the_book_to_just_processed(capsys):
    fresh = upload()
    book, p = fresh, make_profile()
    hard = book["pages"][1]                                           # needs_subject: the hard page
    client.post(f"/api/pages/{hard['id']}/subject", json={"point": [0.5, 0.5]})
    client.post(f"/api/pages/{book['pages'][2]['id']}/subject",
                json={"label": "frog", "outline": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.4]]})
    client.post(f"/api/pages/{book['pages'][0]['id']}/omit", json={"omitted": True})
    client.post(f"/api/books/{book['id']}/confirm-all")
    approve_all(book, p)
    other = confirmed_book(); approve_all(other, p)                   # a second book, untouched

    assert reset_demo.main([book["id"]]) == 0

    assert client.get(f"/api/books/{book['id']}").json() == fresh    # hard page is wrong again
    assert db.approvals.count_documents({}) == 1                      # only the other book's
    assert db.profiles.count_documents({}) == 1
    assert "needs_subject" in capsys.readouterr().out


def test_reset_keeps_the_mask_files():
    book = upload()
    client.post(f"/api/pages/{book['pages'][1]['id']}/subject", json={"point": [0.5, 0.5]})
    masks = lambda: sorted(p.name for p in (jobs.book_dir(ObjectId(book["id"])) / "masks").iterdir())
    before = masks()
    reset_demo.main([book["id"]])
    assert masks() == before


def test_reset_twice_is_the_same_as_once():
    book = upload()
    reset_demo.main([book["id"]]); reset_demo.main([book["id"]])
    assert client.get(f"/api/books/{book['id']}").json() == book


@pytest.mark.parametrize("book_id", ["nope", "65a000000000000000000009"])
def test_unknown_book_changes_nothing(book_id, capsys):
    upload()
    before = list(db.pages.find())
    assert reset_demo.main([book_id]) == 1
    assert "No book with id" in capsys.readouterr().out and list(db.pages.find()) == before


def test_a_page_not_yet_processed_is_left_alone(capsys):
    book = upload()
    first = ObjectId(book["pages"][0]["id"])
    db.pages.update_one({"_id": first}, {"$unset": {"auto_state": ""}, "$set": {"confirmed": True}})
    before = db.pages.find_one({"_id": first})
    assert reset_demo.main([book["id"]]) == 0
    assert db.pages.find_one({"_id": first}) == before
    assert "not processed yet" in capsys.readouterr().out
