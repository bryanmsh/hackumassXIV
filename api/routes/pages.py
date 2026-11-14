"""Page and subject routes."""
from fastapi import APIRouter, HTTPException

from api import db, images, modules
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
    page = db.pages.find_one({"_id": db.oid(page_id)})
    if page is None:
        raise HTTPException(404, "not found")
    subject = images.selected(page)
    if subject is None:
        return images.image(images.view_bytes(page))
    return images.image(modules.display.overlay(page["view_path"], subject["mask_path"]))
