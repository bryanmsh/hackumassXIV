"""Approval routes."""
import logging
from datetime import datetime, timezone
from typing import Annotated, Literal

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api import db, images, modules, versions, views
from contracts.types import Level, Settings

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


class PageDecision(BaseModel):
    page_id: str
    version: str
    decision: Literal["approve", "reject"]


class ApproveBody(BaseModel):
    profile_id: str
    level: Level
    pages: list[PageDecision]


def _current(book_id: ObjectId, page_id: str, profile: dict, level: int) -> tuple[dict | None, versions.Version | None]:
    """The page and its current version. A malformed, unknown or other-book page gives (None, None)."""
    try:
        page = db.pages.find_one({"_id": ObjectId(page_id), "book_id": book_id})
    except InvalidId:
        return None, None
    return page, (versions.current_version(page, profile, level) if page else None)


@router.post("/books/{book_id}/approve")
def approve(book_id: str, body: ApproveBody):
    """Record a decision on exactly the versions the sheet showed. Any that changed since is refused."""
    book = db.books.find_one({"_id": db.oid(book_id)})
    profile = db.profiles.find_one({"_id": db.oid(body.profile_id)})
    if book is None or profile is None:
        raise HTTPException(404, "not found")
    recorded, changed = [], []
    for row in body.pages:
        page, version = _current(book["_id"], row.page_id, profile, body.level)
        if version is None or version.token != row.version:
            changed.append({"page_id": row.page_id, "sent": row.version,
                            "current": version.token if version else None})
            continue
        record = {"page_id": page["_id"], "profile_id": profile["_id"], "subject_hash": version.subject_hash,
                  "settings_hash": version.settings_hash, "level": version.level,
                  "render_version": version.render_version, "decision": row.decision,
                  "at": datetime.now(timezone.utc)}
        record["_id"] = db.approvals.insert_one(record).inserted_id
        recorded.append(views.approval_json(record))
    if changed:
        return JSONResponse({"detail": "look again", "changed": changed, "recorded": recorded}, status_code=409)
    return {"approvals": recorded}
