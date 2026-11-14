"""Profile and display routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import db, images
from api.images import stub_render
from api.main import example
from contracts.types import Level, Settings

router = APIRouter(prefix="/api")


@router.get("/profiles")
def list_profiles():
    return example("GET /api/profiles")


@router.post("/profiles")
def create_profile():
    return example("POST /api/profiles")


@router.patch("/profiles/{profile_id}")
def update_profile(profile_id: str):
    return example("PATCH /api/profiles/{id}")


class PreviewRequest(BaseModel):
    page_id: str
    settings: Settings
    level: Level


@router.post("/preview")
def preview(body: PreviewRequest):
    """Render a page with settings that are not saved anywhere. Stores nothing."""
    page = db.pages.find_one({"_id": db.oid(body.page_id)})
    if page is None:
        raise HTTPException(404, "not found")
    return images.image(images.render_page(page, body.settings, body.level))


@router.get("/render/{page_id}")
def render_page(page_id: str):
    return stub_render()
