import pytest
from bson import ObjectId
from fastapi import HTTPException

from api import db


def test_tests_use_a_throwaway_database():
    assert db.books.database.name.startswith("mirai_test_")


def test_oid_accepts_a_real_id_and_refuses_a_bad_one():
    real = ObjectId()
    assert db.oid(str(real)) == real
    with pytest.raises(HTTPException) as e:
        db.oid("b1")
    assert e.value.status_code == 404


def test_each_test_starts_empty():
    assert db.books.count_documents({}) == 0
    db.books.insert_one({"title": "x"})
