import os
import secrets
import tempfile

import pytest

# Set before any api module is imported, so tests never write into the repo's data folder
# and never touch the real database.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mirai-test-")
os.environ["MONGODB_URI"] = f"mongodb://localhost:27017/mirai_test_{secrets.token_hex(4)}"


@pytest.fixture(scope="session", autouse=True)
def throwaway_database():
    from pymongo.errors import PyMongoError

    from api import db

    try:
        db.client.admin.command("ping")
    except PyMongoError:
        pytest.exit("MongoDB is not running. Start it: docker start mirai-mongo", returncode=1)
    db.ensure_indexes()
    yield
    db.client.drop_database(db.database.name)


@pytest.fixture(autouse=True)
def clean_db(throwaway_database):
    from api import db

    for collection in (db.books, db.pages, db.profiles, db.checks, db.approvals):
        collection.delete_many({})
