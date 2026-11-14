"""The version of a page: what a child would be shown, in which look, and the token that names it."""
from typing import Literal, NamedTuple

from bson import ObjectId

from api import db, modules
from contracts.hashing import version_token
from contracts.types import Settings


class Version(NamedTuple):
    subject_hash: str
    settings_hash: str
    level: int
    render_version: str

    @property
    def token(self) -> str:
        return version_token(*self)


def current_version(page: dict, profile: dict, level: int) -> Version | None:
    """None unless the page has a subject, is confirmed and is not omitted."""
    if not page.get("subject_hash") or not page["confirmed"] or page["omitted"]:
        return None
    return Version(page["subject_hash"], profile["settings_hash"], level, modules.display.RENDER_VERSION)


def approval_state(page_id: ObjectId, profile_id: ObjectId,
                   version: Version | None) -> Literal["approved", "rejected", "none"]:
    """The newest decision on exactly this version for this child, or "none"."""
    if version is None:
        return "none"
    newest = db.approvals.find_one(
        {"page_id": page_id, "profile_id": profile_id, "subject_hash": version.subject_hash,
         "settings_hash": version.settings_hash, "level": version.level,
         "render_version": version.render_version},
        sort=[("at", -1), ("_id", -1)])  # _id breaks a tie inside one millisecond
    if newest is None:
        return "none"
    return "approved" if newest["decision"] == "approve" else "rejected"


def stored_checks(page: dict, version: Version, settings: Settings) -> dict:
    """The check results for this page and version. They are run once, then read back."""
    from api import images  # images imports this module

    key = {"page_id": page["_id"], "subject_hash": version.subject_hash,
           "settings_hash": version.settings_hash, "level": version.level,
           "render_version": version.render_version}
    stored = db.checks.find_one(key)
    if stored is not None:
        return stored["result"]
    result = modules.display.run_checks(page["image_path"], page["view_path"],
                                        images.selected(page)["mask_path"], settings, version.level,
                                        page["text"]).model_dump()
    db.checks.update_one(key, {"$setOnInsert": {"result": result}}, upsert=True)
    return result


def fully_approved(pages: list[dict], profile: dict, level: int) -> bool:
    """At least one page is approved, and every page is omitted or has a decision on its current version."""
    states = [None if page["omitted"] else
              approval_state(page["_id"], profile["_id"], current_version(page, profile, level))
              for page in pages]
    return "approved" in states and all(s in (None, "approved", "rejected") for s in states)
