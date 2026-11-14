from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError

from api.tests.helpers import client


def test_health_answers_on_both_paths():
    for path in ("/health", "/api/health"):
        r = client.get(path)
        assert (r.status_code, r.json()) == (200, {"status": "ok"})


def test_health_says_503_when_the_database_is_down(monkeypatch):
    def down(*_args, **_kwargs):
        raise ServerSelectionTimeoutError("no database")

    monkeypatch.setattr(Database, "command", down)
    assert client.get("/api/health").status_code == 503
