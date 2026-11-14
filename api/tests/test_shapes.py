"""Every JSON route answers in the shape contracts/examples.json agreed with the web client."""
import pytest

from api.tests.helpers import EX, approve_all, client, confirmed_book, make_profile, upload


def same_shape(example, actual, path="$", must=frozenset()):
    """Every key the example shows is present, with the same JSON type unless either side is null.

    A path in `must` has to be filled (not null, not an empty list), so a response emptied by the
    test's own setup cannot pass by having nothing to compare.
    """
    if path in must:
        assert actual not in (None, [], {}), f"{path} is empty but the example shows content"
    if example is None or actual is None:
        return
    assert type(example) is type(actual) or {type(example), type(actual)} <= {int, float}, path
    if isinstance(example, dict):
        for key, value in example.items():
            assert key in actual, f"{path}.{key} is missing"
            same_shape(value, actual[key], f"{path}.{key}", must)
    elif isinstance(example, list) and example and actual:
        for i, item in enumerate(actual):
            same_shape(example[0], item, f"{path}[{i}]", must)


def check(key, response, must=()):
    assert response.status_code == 200, f"{key}: {response.status_code} {response.text}"
    same_shape(EX[key]["response"], response.json(), key, frozenset(f"{key}{m}" for m in must))


def test_every_json_route_has_the_agreed_shape():
    # Each route is compared while its response is populated like its example, so the calls that
    # fill things in come first and the ones that change or empty them come after.
    book, p = upload(), make_profile()
    check("POST /api/books/{id}/confirm-all", client.post(f"/api/books/{book['id']}/confirm-all"),
          ["", "[0].candidates"])
    book = client.get(f"/api/books/{book['id']}").json()
    page = book["pages"][0]["id"]
    q = f"?profile={p['id']}&level=1"
    check("GET /api/books/{id}/sheet", client.get(f"/api/books/{book['id']}/sheet{q}"),
          [".pages", ".pages[0].version", ".pages[0].checks", ".pages[0].preview_url", ".pages[0].label"])
    check("POST /api/books/{id}/approve", approve_all(book, p), [".approvals", ".approvals[0].page_id"])
    check("GET /api/reader/{book_id}", client.get(f"/api/reader/{book['id']}{q}"),
          [".pages", ".pages[0].v", ".pages[0].image_url", ".versions"])
    check("GET /api/books", client.get("/api/books"), [""])
    check("GET /api/books/{id}", client.get(f"/api/books/{book['id']}"), [".pages", ".pages[0].candidates"])
    check("GET /api/profiles", client.get("/api/profiles"), [""])
    check("PATCH /api/profiles/{id}", client.patch(f"/api/profiles/{p['id']}", json={"name": "May"}))
    # These change the page or the book, so they come last.
    check("PATCH /api/books/{id}", client.patch(f"/api/books/{book['id']}", json={"title": "T"}))
    check("POST /api/pages/{id}/subject", client.post(f"/api/pages/{page}/subject", json={"candidate": 1}),
          [".candidates"])
    check("POST /api/pages/{id}/confirm", client.post(f"/api/pages/{page}/confirm"), [".candidates"])
    check("POST /api/pages/{id}/omit", client.post(f"/api/pages/{page}/omit", json={"omitted": False}),
          [".candidates"])
    check("POST /api/pages/{id}/retry", client.post(f"/api/pages/{book['pages'][2]['id']}/retry", json={}))


def test_the_check_refuses_an_empty_response():
    with pytest.raises(AssertionError, match=r"\$.pages is empty"):
        same_shape({"pages": [1]}, {"pages": []}, must=frozenset({"$.pages"}))
    with pytest.raises(AssertionError, match=r"\$.v is empty"):
        same_shape({"v": "x"}, {"v": None}, must=frozenset({"$.v"}))


def test_error_bodies_have_the_agreed_shape():
    book, p = confirmed_book(), make_profile()
    stale = client.post(f"/api/books/{book['id']}/approve", json={"profile_id": p["id"], "level": 1,
        "pages": [{"page_id": book["pages"][0]["id"], "version": "000000000000", "decision": "approve"}]})
    assert stale.status_code == 409
    key = "POST /api/books/{id}/approve"
    same_shape(EX[key]["errors"]["409"], stale.json(), key, frozenset({f"{key}.changed", f"{key}.changed[0].page_id"}))
    refused = client.get(f"/api/reader/page/{book['pages'][0]['id']}?profile={p['id']}&level=1&v=x")
    assert refused.status_code == 403
    assert refused.json() == EX["GET /api/reader/page/{page_id}"]["errors"]["403"]
