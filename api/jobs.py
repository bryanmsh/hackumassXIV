"""Background work: take in a book and run the pipeline on its pages."""
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId

from api import db, modules, settings
from contracts.types import PageAsset, PageResult

logger = logging.getLogger(__name__)


def book_dir(book_id) -> Path:
    return settings.DATA_DIR / "books" / str(book_id)


def failure_reason(error: Exception, book_id=None) -> str:
    """Error text safe to show a client: the data folder path removed, and the book's folder when
    the book is known (it is also removed in its relative form). Class name if no text."""
    text = str(error)
    roots = [str(settings.DATA_DIR.resolve())]
    if settings.DATA_DIR.is_absolute():  # a relative one ("data") would mangle ordinary words
        roots.append(str(settings.DATA_DIR))
    if book_id is not None:
        roots += [str(book_dir(book_id)), str(book_dir(book_id).resolve())]
    for root in roots:
        text = text.replace(root, "")
    return text.strip() or type(error).__name__


def apply_result(page: dict, result: PageResult) -> None:
    """Store what the pipeline returned. Candidates are only ever added, never dropped.

    Merges against the page as stored now, not the caller's copy. A page the teacher has
    confirmed keeps its subject and stays confirmed: asking again only adds suggestions.
    """
    page = db.pages.find_one({"_id": page["_id"]})
    if page is None:
        return
    candidates = list(page.get("candidates", []))
    known = {c["mask_hash"] for c in candidates}
    candidates += [c.model_dump() for c in result.candidates if c.mask_hash not in known]
    chosen = result.candidates[result.selected].mask_hash if result.selected is not None else None
    selected = next((i for i, c in enumerate(candidates) if c["mask_hash"] == chosen), None)
    auto = {"auto_state": result.state, "auto_subject_hash": chosen, "auto_reason": result.reason}
    if page.get("confirmed") and page.get("selected") is not None:
        db.pages.update_one({"_id": page["_id"]}, {"$set": {
            "state": "ready", "reason": None, "candidates": candidates, **auto}})
        return
    db.pages.update_one({"_id": page["_id"]}, {"$set": {
        "state": result.state, "reason": result.reason, "page_kind": result.page_kind,
        "candidates": candidates, "selected": selected, "subject_hash": chosen,
        "confirmed": False, **auto}})


def _failed(error: Exception, book_id=None) -> PageResult:
    return PageResult(state="failed", page_kind=None, candidates=[], selected=None,
                      reason=failure_reason(error, book_id))


def process_one(page_id: ObjectId, force: bool = False) -> None:
    """Run the pipeline on one page. Whatever goes wrong fails this page and no other."""
    try:
        page = db.pages.find_one({"_id": page_id})
        if page is None:  # the book was deleted while this page waited its turn
            return
        asset = PageAsset(page_number=page["number"], image_path=page["image_path"],
                          view_path=page["view_path"], width=page["width"],
                          height=page["height"], text=page["text"],
                          text_source="layer" if page["text"] else "none", flags=page["flags"])
        try:
            result = modules.pipeline.process_page(asset, book_dir(page["book_id"]), force)
        except Exception as error:
            logger.exception("process_page failed for page %s", page_id)
            result = _failed(error, page["book_id"])
        apply_result(page, result)
    except Exception as error:
        logger.exception("processing page %s failed", page_id)
        try:
            apply_result({"_id": page_id}, _failed(error))
        except Exception:
            logger.exception("could not mark page %s failed", page_id)


def ingest_book(book_id: ObjectId) -> None:
    """Rasterize the saved PDF, add its pages, then process every page."""
    directory = book_dir(book_id)
    try:
        assets = modules.pipeline.rasterize(directory / "source.pdf", directory)
    except Exception:
        logger.exception("rasterize failed for book %s", book_id)
        db.books.update_one({"_id": book_id}, {"$set": {"state": "failed"}})
        return
    if db.books.find_one({"_id": book_id}) is None:  # deleted while rasterizing: leave nothing behind
        shutil.rmtree(directory, ignore_errors=True)
        return
    started = datetime.now(timezone.utc)
    page_ids = []
    for asset in assets:
        page_ids.append(db.pages.insert_one({
            "book_id": book_id, "number": asset.page_number, "image_path": asset.image_path,
            "view_path": asset.view_path, "width": asset.width, "height": asset.height,
            "text": asset.text, "flags": asset.flags, "state": "processing", "reason": None,
            "page_kind": None, "candidates": [], "selected": None, "subject_hash": None,
            "confirmed": False, "omitted": False, "processing_started_at": started,
            "auto_state": None, "auto_subject_hash": None, "auto_reason": None,
            "second_look": None}).inserted_id)
    db.books.update_one({"_id": book_id}, {"$set": {"state": "ready", "page_count": len(assets)}})
    process_pages(page_ids)


def process_pages(page_ids: list[ObjectId]) -> None:
    """Run the pipeline on these pages, a few at a time."""
    with ThreadPoolExecutor(max_workers=settings.PAGE_CONCURRENCY) as pool:
        list(pool.map(process_one, page_ids))


def start_second_look(page: dict) -> bool:
    """Mark the second look pending for this page's subject. False if one already exists for it,
    or if the page no longer has that subject."""
    look = page.get("second_look")
    if look and look["subject_hash"] == page["subject_hash"]:
        return False
    started = db.pages.update_one({"_id": page["_id"], "subject_hash": page["subject_hash"]}, {"$set": {
        "second_look": {"subject_hash": page["subject_hash"], "status": "pending",
                        "answer": None, "detail": None}}})
    return started.matched_count == 1


def run_second_look(page_id: ObjectId, subject_hash: str) -> None:
    """Name the subject from the adapted page and store it. A warning only: failure never raises.

    A result for a subject the page no longer has is dropped.
    """
    try:
        page = db.pages.find_one({"_id": page_id})
        if page is None:  # the book was deleted meanwhile
            return
        candidate = next(c for c in page["candidates"] if c["mask_hash"] == subject_hash)
        found = modules.display.second_look(page["image_path"], candidate["mask_path"],
                                            candidate["label"], candidate["synonyms"])
        result = {"status": found.status, "answer": found.answer, "detail": found.detail}
    except Exception:
        logger.exception("second look failed for page %s", page_id)
        result = {"status": "warn", "answer": None, "detail": "The second look could not run."}
    db.pages.update_one({"_id": page_id, "subject_hash": subject_hash},
                        {"$set": {"second_look": {"subject_hash": subject_hash, **result}}})


def recover_interrupted() -> None:
    """Jobs run inside the server process, so a restart strands them: fail what was in flight."""
    db.books.update_many({"state": "ingesting"}, {"$set": {"state": "failed"}})
    db.pages.update_many({"state": "processing"},
                         {"$set": {"state": "failed", "reason": "interrupted, retry"}})
