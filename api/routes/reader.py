"""Reader routes: only versions the teacher approved are listed or served."""
from typing import Annotated

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api import db, images, versions

router = APIRouter(prefix="/api")

ADAPTATION_NOTE = "These pages were adapted from the original book."


def _version_pairs(book_pages: list[dict]) -> list[tuple[dict, int]]:
    """Each profile at its own level, plus every other (profile, level) with an approval on this book."""
    page_ids = [page["_id"] for page in book_pages]
    saved = {p["_id"]: p for p in db.profiles.find()}
    pairs = {(p["_id"], p["level"]) for p in saved.values()}
    pairs |= {(a["profile_id"], a["level"]) for a in
              db.approvals.find({"page_id": {"$in": page_ids}}, {"profile_id": 1, "level": 1})}
    return sorted(((saved[profile_id], level) for profile_id, level in pairs if profile_id in saved),
                  key=lambda pair: (pair[0]["name"], pair[1]))


@router.get("/reader/{book_id}")
def reader(book_id: str, profile: str, level: Annotated[int, Query(ge=1, le=4)]):
    book = db.books.find_one({"_id": db.oid(book_id)})
    saved = db.profiles.find_one({"_id": db.oid(profile)})
    if book is None or saved is None:
        raise HTTPException(404, "not found")
    book_pages = list(db.pages.find({"book_id": book["_id"]}).sort("number", 1))
    shown, skipped = [], []
    for page in book_pages:
        version = versions.current_version(page, saved, level)
        state = versions.approval_state(page["_id"], saved["_id"], version)
        if state == "approved":
            shown.append({"page_id": str(page["_id"]), "number": page["number"], "v": version.token,
                          "image_url": f"/api/reader/page/{page['_id']}?profile={saved['_id']}"
                                       f"&level={level}&v={version.token}"})
            continue
        reason = "omitted" if page["omitted"] else "rejected" if state == "rejected" else "not_approved"
        skipped.append({"page_id": str(page["_id"]), "number": page["number"], "reason": reason})
    return {"book_id": str(book["_id"]), "title": book["title"], "profile_id": str(saved["_id"]),
            "level": level, "pages": shown, "skipped": skipped, "credits": book["credits"],
            "adaptation_note": ADAPTATION_NOTE,
            "versions": [{"profile_id": str(p["_id"]), "profile_name": p["name"], "level": lvl,
                          "fully_approved": versions.fully_approved(book_pages, p, lvl)}
                         for p, lvl in _version_pairs(book_pages)]}


def _refuse() -> JSONResponse:
    return JSONResponse({"detail": "not approved"}, status_code=403)


@router.get("/reader/page/{page_id}")
def reader_page(page_id: str, profile: str | None = None, level: str | None = None, v: str | None = None):
    """The image, only while this exact version is approved. Every failure is the same 403."""
    if level not in ("1", "2", "3", "4") or not v:
        return _refuse()
    try:
        page = db.pages.find_one({"_id": ObjectId(page_id)})
        saved = db.profiles.find_one({"_id": ObjectId(profile)})
    except (InvalidId, TypeError):
        return _refuse()
    if page is None or saved is None:
        return _refuse()
    version = versions.current_version(page, saved, int(level))
    if version is None or version.token != v:
        return _refuse()
    if versions.approval_state(page["_id"], saved["_id"], version) != "approved":
        return _refuse()
    return images.image(images.cached_render(page, saved, int(level)))
