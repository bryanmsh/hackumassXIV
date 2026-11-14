"""Approval routes."""
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from api import db, images, modules, versions
from api.main import example
from contracts.types import Settings

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

PENDING_SECOND_LOOK = {"status": "pending", "answer": None, "detail": None}


def _sheet_row(page: dict, profile: dict, level: int) -> dict:
    version = versions.current_version(page, profile, level)
    candidate = images.selected(page)
    row = {"page_id": str(page["_id"]), "number": page["number"], "version": None,
           "state": page["state"], "confirmed": page["confirmed"], "omitted": page["omitted"],
           "label": candidate["label"] if candidate else None,
           "source": candidate["source"] if candidate else None,
           "checks": None, "second_look": None,
           "approval": versions.approval_state(page["_id"], profile["_id"], version), "preview_url": None}
    if version is None:
        return row
    look = page.get("second_look")
    if look and look["subject_hash"] == version.subject_hash:
        look = {"status": look["status"], "answer": look["answer"], "detail": look["detail"]}
    else:
        look = dict(PENDING_SECOND_LOOK)
    try:
        checks = versions.stored_checks(page, version, Settings.model_validate(profile["settings"]))
    except Exception:  # one bad page must not blank the sheet
        logger.exception("checks failed for page %s", page["_id"])
        checks = None
    return {**row, "version": version.token, "checks": checks, "second_look": look,
            "preview_url": f"/api/render/{page['_id']}?profile={profile['_id']}&level={level}&v={version.token}"}


@router.get("/books/{book_id}/sheet")
def contact_sheet(book_id: str, profile: str, level: Annotated[int, Query(ge=1, le=4)]):
    book = db.books.find_one({"_id": db.oid(book_id)})
    saved = db.profiles.find_one({"_id": db.oid(profile)})
    if book is None or saved is None:
        raise HTTPException(404, "not found")
    pages = db.pages.find({"book_id": book["_id"]}).sort("number", 1)
    return {"book_id": str(book["_id"]), "profile_id": str(saved["_id"]), "level": level,
            "render_version": modules.display.RENDER_VERSION,
            "pages": [_sheet_row(page, saved, level) for page in pages]}


@router.post("/books/{book_id}/approve")
def approve(book_id: str):
    return example("POST /api/books/{id}/approve")
