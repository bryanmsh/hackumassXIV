import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
EX = json.loads((Path(__file__).parents[2] / "contracts" / "examples.json").read_text())


def test_unknown_route_is_404():
    assert client.get("/api/nope").status_code == 404


def test_every_example_route_is_served():
    served = {f"{method.upper()} {path}" for path, methods in app.openapi()["paths"].items()
              for method in methods}
    documented = {key for key in EX if not key.startswith("_")}
    # Path parameter names differ ({id} vs {book_id}), so compare with them blanked.
    blank = lambda keys: {re.sub(r"\{\w+\}", "{}", k) for k in keys}
    assert blank(documented) <= blank(served)
