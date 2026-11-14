"""Profile and display routes."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, StringConstraints

from api import db, images, versions, views
from contracts.hashing import settings_hash
from contracts.types import Level, Settings

router = APIRouter(prefix="/api")

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProfileBody(BaseModel):
    name: Name
    level: Level
    settings: Settings
    contrast_override_note: str | None = None


class ProfilePatch(BaseModel):
    """Any subset. A field that is sent is validated, so null is refused except for the note.
    The None defaults stand for "not sent" and are never read: only fields_set is."""
    name: Name = None
    level: Level = None
    settings: Settings = None
    contrast_override_note: str | None = None


@router.get("/profiles")
def list_profiles():
    return [views.profile_json(p) for p in db.profiles.find().sort("_id", 1)]


@router.post("/profiles")
def create_profile(body: ProfileBody):
    profile = {**body.model_dump(mode="json"), "settings_hash": settings_hash(body.settings)}
    profile["_id"] = db.profiles.insert_one(profile).inserted_id
    return views.profile_json(profile)


@router.patch("/profiles/{profile_id}")
def update_profile(profile_id: str, body: ProfilePatch):
    fields = {name: getattr(body, name) for name in body.model_fields_set}
    if "settings" in fields:
        fields["settings_hash"] = settings_hash(fields["settings"])
        fields["settings"] = fields["settings"].model_dump(mode="json")
    if fields:
        profile = db.profiles.find_one_and_update({"_id": db.oid(profile_id)}, {"$set": fields},
                                                  return_document=True)
    else:
        profile = db.profiles.find_one({"_id": db.oid(profile_id)})
    if profile is None:
        raise HTTPException(404, "not found")
    return views.profile_json(profile)


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
def render_page(page_id: str, profile: str, level: Annotated[int, Query(ge=1, le=4)], v: str | None = None):
    """A page as a saved profile shows it. A `v` that is not the page's current token is refused."""
    page = db.pages.find_one({"_id": db.oid(page_id)})
    saved = db.profiles.find_one({"_id": db.oid(profile)})
    if page is None or saved is None:
        raise HTTPException(404, "not found")
    if v is not None:
        version = versions.current_version(page, saved, level)
        if version is None or version.token != v:
            raise HTTPException(409, "This page has changed since that version.")
    return images.image(images.cached_render(page, saved, level))
