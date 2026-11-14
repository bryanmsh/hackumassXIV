"""Profile and display routes."""
from fastapi import APIRouter

from api.images import stub_render
from api.main import example

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


@router.post("/preview")
def preview():
    return stub_render()


@router.get("/render/{page_id}")
def render_page(page_id: str):
    return stub_render()
