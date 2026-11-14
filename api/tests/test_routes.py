import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
EX = json.loads((Path(__file__).parents[2] / "contracts" / "examples.json").read_text())

JSON_ROUTES = [  # (method, url, examples key)
    ("POST", "/api/pages/p1/retry", "POST /api/pages/{id}/retry"),
    ("POST", "/api/pages/p1/subject", "POST /api/pages/{id}/subject"),
    ("POST", "/api/pages/p1/confirm", "POST /api/pages/{id}/confirm"),
    ("POST", "/api/books/b1/confirm-all", "POST /api/books/{id}/confirm-all"),
    ("POST", "/api/pages/p1/omit", "POST /api/pages/{id}/omit"),
    ("GET", "/api/profiles", "GET /api/profiles"),
    ("POST", "/api/profiles", "POST /api/profiles"),
    ("PATCH", "/api/profiles/pr1", "PATCH /api/profiles/{id}"),
    ("GET", "/api/books/b1/sheet?profile=pr1&level=1", "GET /api/books/{id}/sheet"),
    ("POST", "/api/books/b1/approve", "POST /api/books/{id}/approve"),
    ("GET", "/api/reader/b1?profile=pr1&level=1", "GET /api/reader/{book_id}"),
]


@pytest.mark.parametrize("method,url,key", JSON_ROUTES)
def test_json_route_answers_with_its_example(method, url, key):
    r = client.request(method, url, json=EX[key]["request"])
    assert r.status_code == 200 and r.json() == EX[key]["response"]


IMAGE_ROUTES = [
    ("GET", "/api/pages/p1/overlay"),
    ("POST", "/api/preview"),
    ("GET", "/api/render/p1?profile=pr1&level=1&v=x"),
    ("GET", "/api/reader/page/p1?profile=pr1&level=1&v=x"),
]


@pytest.mark.parametrize("method,url", IMAGE_ROUTES)
def test_image_route_sends_uncached_webp(method, url):
    body = EX["POST /api/preview"]["request"] if method == "POST" else None
    r = client.request(method, url, json=body)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"
    assert r.headers["cache-control"] == "no-store"
    assert r.content[:4] == b"RIFF" and r.content[8:12] == b"WEBP"


def test_unknown_route_is_404():
    assert client.get("/api/nope").status_code == 404


def test_every_example_route_is_served():
    served = {f"{method.upper()} {path}" for path, methods in app.openapi()["paths"].items()
              for method in methods}
    documented = {key for key in EX if not key.startswith("_")}
    # Path parameter names differ ({id} vs {book_id}), so compare with them blanked.
    blank = lambda keys: {re.sub(r"\{\w+\}", "{}", k) for k in keys}
    assert blank(documented) <= blank(served)
