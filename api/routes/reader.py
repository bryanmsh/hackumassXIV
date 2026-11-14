"""Reader routes."""
from fastapi import APIRouter

from api.images import stub_render
from api.main import example

router = APIRouter(prefix="/api")


@router.get("/reader/{book_id}")
def reader(book_id: str):
    return example("GET /api/reader/{book_id}")


@router.get("/reader/page/{page_id}")
def reader_page(page_id: str):
    return stub_render()
