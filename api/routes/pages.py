"""Page and subject routes."""
from fastapi import APIRouter

from api import modules
from api.images import image, stub_page
from api.main import example

router = APIRouter(prefix="/api")


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
