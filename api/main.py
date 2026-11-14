"""Mirai API. Start with: uvicorn api.main:app --host 0.0.0.0 --port 8000

Hour 1 skeleton: every Contract 1 route answers with its example from contracts/examples.json
and ignores ids and bodies. Image routes return one stand-in page. Each route is its own
function so it can be replaced by the real version without touching the others.
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, FastAPI, Form, Response, UploadFile

from api import modules, settings
from contracts.types import Settings

EXAMPLES = json.loads((Path(__file__).parents[1] / "contracts" / "examples.json").read_text())

app = FastAPI(title="Mirai API")
router = APIRouter(prefix="/api")


def example(key: str):
    return EXAMPLES[key]["response"]


def image(data: bytes) -> Response:
    """Every image is WebP and must never be cached: an approval can lapse at any time."""
    return Response(data, media_type="image/webp", headers={"Cache-Control": "no-store"})


@lru_cache
def stub_page():
    """One stand-in page and its selected cut-out, built on first use."""
    out_dir = settings.DATA_DIR / "books" / "stub"
    asset = modules.pipeline.rasterize("", out_dir)[0]
    result = modules.pipeline.process_page(asset, out_dir)
    return asset, result.candidates[result.selected]


def stub_render() -> Response:
    asset, subject = stub_page()
    return image(modules.display.render(
        asset.image_path, asset.view_path, subject.mask_path, Settings(), 2, asset.text))


# --- books ---

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


# --- pages and subjects ---

@router.post("/pages/{page_id}/retry")
def retry_page(page_id: str):
    return example("POST /api/pages/{id}/retry")


@router.post("/pages/{page_id}/subject")
def set_subject(page_id: str):
    return example("POST /api/pages/{id}/subject")


@router.post("/pages/{page_id}/confirm")
def confirm_page(page_id: str):
    return example("POST /api/pages/{id}/confirm")


@router.post("/pages/{page_id}/omit")
def omit_page(page_id: str):
    return example("POST /api/pages/{id}/omit")


@router.get("/pages/{page_id}/overlay")
def page_overlay(page_id: str):
    asset, subject = stub_page()
    return image(modules.display.overlay(asset.view_path, subject.mask_path))


# --- profiles and display ---

@router.get("/profiles")
def list_profiles():
    return example("GET /api/profiles")


@router.post("/profiles")
def create_profile():
    return example("POST /api/profiles")


@router.patch("/profiles/{profile_id}")
def update_profile(profile_id: str):
    return example("PATCH /api/profiles/{id}")


@router.post("/preview")
def preview():
    return stub_render()


@router.get("/render/{page_id}")
def render_page(page_id: str):
    return stub_render()


# --- approval ---

@router.get("/books/{book_id}/sheet")
def contact_sheet(book_id: str):
    return example("GET /api/books/{id}/sheet")


@router.post("/books/{book_id}/approve")
def approve(book_id: str):
    return example("POST /api/books/{id}/approve")


# --- reader ---

@router.get("/reader/{book_id}")
def reader(book_id: str):
    return example("GET /api/reader/{book_id}")


@router.get("/reader/page/{page_id}")
def reader_page(page_id: str):
    return stub_render()


app.include_router(router)
