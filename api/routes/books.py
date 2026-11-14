"""Book routes."""
from fastapi import APIRouter, Form, UploadFile

from api.main import example

router = APIRouter(prefix="/api")


@router.post("/books")
def upload_book(file: UploadFile, credits: str | None = Form(None)):
    return example("POST /api/books")


@router.get("/books")
def list_books():
    return example("GET /api/books")


@router.get("/books/{book_id}")
def get_book(book_id: str):
    return example("GET /api/books/{id}")


@router.patch("/books/{book_id}")
def update_book(book_id: str):
    return example("PATCH /api/books/{id}")


@router.post("/books/{book_id}/confirm-all")
def confirm_all(book_id: str):
    return example("POST /api/books/{id}/confirm-all")
