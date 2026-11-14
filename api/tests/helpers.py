"""Shared test helpers: the client, the contract examples, and a way to upload a generated PDF."""
import json
from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
EX = json.loads((Path(__file__).parents[2] / "contracts" / "examples.json").read_text())


def make_pdf(pages: int = 3) -> bytes:
    doc = pymupdf.open()
    for n in range(1, pages + 1):
        page = doc.new_page(width=800, height=600)
        page.insert_text((72, 300), f"Page {n}", fontsize=36)
    data = doc.tobytes()
    doc.close()
    return data


def upload(pages: int = 3) -> dict:
    """Post a PDF and return the book as GET /api/books/{id} shows it."""
    posted = client.post("/api/books", files={"file": ("book.pdf", make_pdf(pages), "application/pdf")})
    assert posted.status_code == 200, posted.text
    return client.get(f"/api/books/{posted.json()['book_id']}").json()


MAYA = {"name": "Maya", "level": 1, "contrast_override_note": None,
        "settings": {"colors": ["#E53935"], "background": "#000000", "size": "medium",
                     "position": "center", "text_mode": "off", "outline": "off"}}


def make_profile(**over) -> dict:
    """Save a profile (Maya's, with any field replaced) and return it."""
    return client.post("/api/profiles", json={**MAYA, **over}).json()


def confirmed_book(pages: int = 3) -> dict:
    """Upload a book, confirm every page that can be, and return the book as it now stands."""
    book = upload(pages)
    assert client.post(f"/api/books/{book['id']}/confirm-all").status_code == 200
    return client.get(f"/api/books/{book['id']}").json()


def approve_all(book: dict, profile: dict, level: int = 1):
    """Load the sheet and approve every row that has a version."""
    sheet = client.get(f"/api/books/{book['id']}/sheet?profile={profile['id']}&level={level}").json()
    return client.post(f"/api/books/{book['id']}/approve", json={
        "profile_id": profile["id"], "level": level,
        "pages": [{"page_id": r["page_id"], "version": r["version"], "decision": "approve"}
                  for r in sheet["pages"] if r["version"]]})
