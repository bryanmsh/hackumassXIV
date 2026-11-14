"""Every JSON route answers in the shape contracts/examples.json agreed with the web client."""
from api.tests.helpers import EX, approve_all, client, confirmed_book, make_profile


def same_shape(example, actual, path="$"):
    """Every key the example shows is present, with the same JSON type unless either side is null."""
    if example is None or actual is None:
        return
    assert type(example) is type(actual) or {type(example), type(actual)} <= {int, float}, path
    if isinstance(example, dict):
        for key, value in example.items():
            assert key in actual, f"{path}.{key} is missing"
            same_shape(value, actual[key], f"{path}.{key}")
    elif isinstance(example, list) and example and actual:
        for i, item in enumerate(actual):
            same_shape(example[0], item, f"{path}[{i}]")


def test_every_json_route_has_the_agreed_shape():
    book, p = confirmed_book(), make_profile()
    approve = approve_all(book, p)
    page = book["pages"][0]["id"]
    q = f"?profile={p['id']}&level=1"
    seen = {
        "GET /api/books": client.get("/api/books"),
        "GET /api/books/{id}": client.get(f"/api/books/{book['id']}"),
        "PATCH /api/books/{id}": client.patch(f"/api/books/{book['id']}", json={"title": "T"}),
        "POST /api/pages/{id}/subject": client.post(f"/api/pages/{page}/subject", json={"candidate": 1}),
        "POST /api/pages/{id}/confirm": client.post(f"/api/pages/{page}/confirm"),
        "POST /api/pages/{id}/omit": client.post(f"/api/pages/{page}/omit", json={"omitted": False}),
        "POST /api/pages/{id}/retry": client.post(f"/api/pages/{book['pages'][2]['id']}/retry", json={}),
        "POST /api/books/{id}/confirm-all": client.post(f"/api/books/{book['id']}/confirm-all"),
        "GET /api/profiles": client.get("/api/profiles"),
        "PATCH /api/profiles/{id}": client.patch(f"/api/profiles/{p['id']}", json={"name": "May"}),
        "GET /api/books/{id}/sheet": client.get(f"/api/books/{book['id']}/sheet{q}"),
        "POST /api/books/{id}/approve": approve,
        "GET /api/reader/{book_id}": client.get(f"/api/reader/{book['id']}{q}"),
    }
    for key, response in seen.items():
        assert response.status_code == 200, key
        same_shape(EX[key]["response"], response.json(), key)


def test_error_bodies_have_the_agreed_shape():
    book, p = confirmed_book(), make_profile()
    stale = client.post(f"/api/books/{book['id']}/approve", json={"profile_id": p["id"], "level": 1,
        "pages": [{"page_id": book["pages"][0]["id"], "version": "000000000000", "decision": "approve"}]})
    same_shape(EX["POST /api/books/{id}/approve"]["errors"]["409"], stale.json())
    refused = client.get(f"/api/reader/page/{book['pages'][0]['id']}?profile={p['id']}&level=1&v=x")
    assert refused.json() == EX["GET /api/reader/page/{page_id}"]["errors"]["403"]
