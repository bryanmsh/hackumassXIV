"""MongoDB: the five collections, id parsing and indexes. The database name is the path of MONGODB_URI."""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo import MongoClient

from api import settings

client = MongoClient(settings.MONGODB_URI or "mongodb://localhost:27017/mirai", serverSelectionTimeoutMS=5000)
database = client.get_default_database(default="mirai")

books = database["books"]
pages = database["pages"]
profiles = database["profiles"]
checks = database["checks"]
approvals = database["approvals"]


def oid(value: str) -> ObjectId:
    """Parse an id from a URL or body. A malformed id is the same as an unknown one: 404."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(404, "not found")


def ensure_indexes() -> None:
    pages.create_index([("book_id", 1), ("number", 1)])
    checks.create_index([("page_id", 1), ("subject_hash", 1), ("settings_hash", 1),
                         ("level", 1), ("render_version", 1)])
    approvals.create_index([("page_id", 1), ("profile_id", 1), ("at", 1)])
