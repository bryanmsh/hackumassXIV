"""Page and subject routes."""
import io
import logging
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException
from PIL import Image, ImageChops
from pydantic import BaseModel, model_validator

from api import coords, db, images, jobs, modules, views
from contracts.hashing import hash_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

CUTOUT_FAILED = "The cut-out could not be made. Try again or draw an outline."


class SubjectBody(BaseModel):
    """One of four shapes: a candidate, several candidates shown together, a click, or a label
    with an outline."""
    model_config = {"extra": "forbid"}

    candidate: int | None = None
    candidates: list[int] | None = None
    point: tuple[float, float] | None = None
    label: str | None = None
    outline: list[tuple[float, float]] | None = None

    @model_validator(mode="after")
    def exactly_one_shape(self):
        by_candidate = self.candidate is not None
        by_point = self.point is not None
        by_several = self.candidates is not None
        by_outline = self.label is not None and self.outline is not None
        partial_outline = (self.label is not None) != (self.outline is not None)
        if partial_outline or [by_candidate, by_several, by_point, by_outline].count(True) != 1:
            raise ValueError("send a candidate, several candidates, a point, or a label with an outline")
        if by_several and (len(self.candidates) < 2 or len(set(self.candidates)) != len(self.candidates)):
            raise ValueError("showing subjects together needs at least 2 different candidates")
        if by_outline and (not self.label.strip() or len(self.outline) < 3):
            raise ValueError("an outline needs a label and at least 3 points")
        return self


class RetryBody(BaseModel):
    force: bool = False


class OmitBody(BaseModel):
    omitted: bool


def _find_page(page_id: str) -> dict:
    page = db.pages.find_one({"_id": db.oid(page_id)})
    if page is None:
        raise HTTPException(404, "not found")
    return page


def _page_response(page_id: ObjectId) -> dict:
    return views.page_json(db.pages.find_one({"_id": page_id}))


def select(page: dict, index: int) -> dict:
    """Make candidate `index` the subject. The page is then ready; a changed subject needs
    confirming again, the same one does not. Stores and returns the updated page.

    Refuses (409) if the page went into processing meanwhile; nothing is written then."""
    subject_hash = page["candidates"][index]["mask_hash"]
    changed = subject_hash != page["subject_hash"]
    fields = {"candidates": page["candidates"], "selected": index, "subject_hash": subject_hash,
              "state": "ready", "reason": None,
              "confirmed": page["confirmed"] and not changed}
    done = db.pages.update_one({"_id": page["_id"], "state": {"$ne": "processing"}}, {"$set": fields})
    if done.matched_count == 0:
        raise HTTPException(409, "This page is being processed.")
    return {**page, **fields}


def _cutout(page: dict, make) -> dict:
    """Run a pipeline call that makes a candidate. Anything it raises leaves the page untouched."""
    try:
        return make(jobs.book_dir(page["book_id"])).model_dump()
    except Exception:
        logger.exception("cut-out failed for page %s", page["_id"])
        raise HTTPException(502, CUTOUT_FAILED)


def _together(page: dict, indexes: list[int]) -> dict:
    """One candidate that shows several together: their masks joined into one new mask file.
    Still only copied artwork; the parts keep their places on the page."""
    parts = [page["candidates"][i] for i in indexes]
    mask = Image.open(parts[0]["mask_path"]).convert("L")
    for part in parts[1:]:
        mask = ImageChops.lighter(mask, Image.open(part["mask_path"]).convert("L"))
    buffer = io.BytesIO()
    mask.save(buffer, "PNG")
    mask_hash = hash_bytes(buffer.getvalue())
    path = jobs.book_dir(page["book_id"]) / "masks" / f"{Path(page['image_path']).stem}_{mask_hash}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(buffer.getvalue())
    labels = list(dict.fromkeys(part["label"] for part in parts))
    boxes = [part["box"] for part in parts]
    return {"label": " and ".join(labels),
            "synonyms": list(dict.fromkeys([*labels, *(s for part in parts for s in part["synonyms"])])),
            "box": (min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes)),
            "confidence": 1.0, "mask_path": str(path), "mask_hash": mask_hash, "source": "manual"}


def _pixels(point, page: dict) -> tuple[float, float]:
    try:
        return coords.to_pixels(point, page["width"], page["height"])
    except ValueError as error:
        raise HTTPException(422, str(error))


@router.post("/pages/{page_id}/retry")
def retry_page(page_id: str, background: BackgroundTasks, body: RetryBody | None = None):
    page = _find_page(page_id)
    force = body.force if body else False
    allowed = ["failed", "unsupported"] if force else ["failed"]
    started = db.pages.update_one({"_id": page["_id"], "state": {"$in": allowed}}, {"$set": {
        "state": "processing", "reason": None, "processing_started_at": datetime.now(timezone.utc)}})
    if started.matched_count == 0:
        raise HTTPException(409, "Only a failed page can be retried; an unsupported page needs force.")
    background.add_task(jobs.process_one, page["_id"], force)
    return _page_response(page["_id"])


@router.post("/pages/{page_id}/subject")
def set_subject(page_id: str, body: SubjectBody):
    page = _find_page(page_id)
    if page["state"] == "processing":
        raise HTTPException(409, "This page is still being processed.")
    candidates = page["candidates"]
    if body.candidate is not None:
        if not 0 <= body.candidate < len(candidates):
            raise HTTPException(422, "That candidate does not exist.")
        return views.page_json(select(page, body.candidate))

    image_path = page["image_path"]
    if body.candidates is not None:
        if not all(0 <= i < len(candidates) for i in body.candidates):
            raise HTTPException(422, "That candidate does not exist.")
        found = _together(page, body.candidates)
    elif body.point is not None:
        x, y = _pixels(body.point, page)
        found = _cutout(page, lambda out_dir: modules.pipeline.segment_at_point(image_path, x, y, out_dir))
    else:
        points = [_pixels(p, page) for p in body.outline]
        found = _cutout(page, lambda out_dir: modules.pipeline.mask_from_outline(
            image_path, body.label.strip(), points, out_dir))
    # The pipeline is slow: add to the page as it is now, never to the copy read before the call.
    page = _find_page(page_id)
    if page["state"] == "processing":
        raise HTTPException(409, "This page is still being processed.")
    candidates = page["candidates"]
    index = next((i for i, c in enumerate(candidates) if c["mask_hash"] == found["mask_hash"]), None)
    if index is None:
        candidates = [*candidates, found]
        index = len(candidates) - 1
    elif body.outline is not None and candidates[index]["source"] == "manual":
        # The same outline sent again with a corrected label. Auto and click candidates keep theirs.
        candidates = [{**c, "label": found["label"]} if i == index else c for i, c in enumerate(candidates)]
    return views.page_json(select({**page, "candidates": candidates}, index))


@router.post("/pages/{page_id}/confirm")
def confirm_page(page_id: str, background: BackgroundTasks):
    page = _find_page(page_id)
    if page["selected"] is None or page["state"] == "processing":
        raise HTTPException(409, "This page has no subject to confirm.")
    # Only the subject this route read may be confirmed: a click that landed meanwhile needs its own review.
    done = db.pages.update_one({"_id": page["_id"], "subject_hash": page["subject_hash"],
                                "state": {"$ne": "processing"}}, {"$set": {"confirmed": True}})
    if done.matched_count == 0:
        raise HTTPException(409, "The subject changed. Look at the page again.")
    if jobs.start_second_look(page):
        background.add_task(jobs.run_second_look, page["_id"], page["subject_hash"])
    return _page_response(page["_id"])


@router.post("/pages/{page_id}/omit")
def omit_page(page_id: str, body: OmitBody):
    page = _find_page(page_id)
    db.pages.update_one({"_id": page["_id"]}, {"$set": {"omitted": body.omitted}})
    return _page_response(page["_id"])


@router.get("/pages/{page_id}/overlay")
def page_overlay(page_id: str):
    page = db.pages.find_one({"_id": db.oid(page_id)})
    if page is None:
        raise HTTPException(404, "not found")
    subject = images.selected(page)
    if subject is None:
        return images.image(images.view_bytes(page))
    return images.image(modules.display.overlay(page["view_path"], subject["mask_path"]))
