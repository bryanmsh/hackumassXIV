"""Approval routes."""
from fastapi import APIRouter

from api.main import example

router = APIRouter(prefix="/api")


@router.get("/books/{book_id}/sheet")
def contact_sheet(book_id: str):
    return example("GET /api/books/{id}/sheet")


@router.post("/books/{book_id}/approve")
def approve(book_id: str):
    return example("POST /api/books/{id}/approve")
