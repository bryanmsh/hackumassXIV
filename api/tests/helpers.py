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
    return client.get(f"/api/books/{posted.json()['id']}").json()
