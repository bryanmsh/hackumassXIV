"""Background work: take in a book and run the pipeline on its pages."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId

from api import db, modules, settings
from contracts.types import PageAsset, PageResult


def book_dir(book_id) -> Path:
    return settings.DATA_DIR / "books" / str(book_id)


def apply_result(page: dict, result: PageResult) -> None:
    """Store what the pipeline returned. Candidates are only ever added, never dropped."""
    candidates = list(page.get("candidates", []))
    known = {c["mask_hash"] for c in candidates}
    candidates += [c.model_dump() for c in result.candidates if c.mask_hash not in known]
    chosen = result.candidates[result.selected].mask_hash if result.selected is not None else None
    selected = next((i for i, c in enumerate(candidates) if c["mask_hash"] == chosen), None)
    changed = chosen != page.get("subject_hash")
    db.pages.update_one({"_id": page["_id"]}, {"$set": {
        "state": result.state, "reason": result.reason, "page_kind": result.page_kind,
        "candidates": candidates, "selected": selected, "subject_hash": chosen,
        "confirmed": page.get("confirmed", False) and not changed,
        "auto_state": result.state, "auto_subject_hash": chosen, "auto_reason": result.reason}})


def process_one(page_id: ObjectId, force: bool = False) -> None:
    """Run the pipeline on one page. A raising pipeline fails this page and no other."""
    page = db.pages.find_one({"_id": page_id})
    asset = PageAsset(page_number=page["number"], image_path=page["image_path"],
                      view_path=page["view_path"], width=page["width"], height=page["height"],
                      text=page["text"], text_source="layer" if page["text"] else "none",
                      flags=page["flags"])
    try:
        result = modules.pipeline.process_page(asset, book_dir(page["book_id"]), force)
    except Exception as error:
        result = PageResult(state="failed", page_kind=None, candidates=[], selected=None,
                            reason=str(error))
    apply_result(page, result)


def ingest_book(book_id: ObjectId) -> None:
    """Rasterize the saved PDF, add its pages, then process every page."""
    directory = book_dir(book_id)
    try:
        assets = modules.pipeline.rasterize(directory / "source.pdf", directory)
    except Exception:
        db.books.update_one({"_id": book_id}, {"$set": {"state": "failed"}})
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
    with ThreadPoolExecutor(max_workers=settings.PAGE_CONCURRENCY) as pool:
        list(pool.map(process_one, page_ids))
