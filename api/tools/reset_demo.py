"""Return one book to "just processed", so the demo's hard page is wrong again.

    python -m api.tools.reset_demo <book_id>

Pages go back to what the pipeline last returned. Approvals for this book's pages are deleted.
Checks, profiles, page images and mask files are kept.
"""
import sys

from bson import ObjectId
from bson.errors import InvalidId

from api import db


def _reset(page: dict) -> dict:
    """The fields that put one processed page back to what the pipeline returned."""
    candidates = [c for c in page["candidates"] if c["source"] == "auto"]
    wanted = page["auto_subject_hash"]
    selected = next((i for i, c in enumerate(candidates) if c["mask_hash"] == wanted), None)
    return {"candidates": candidates, "selected": selected,
            "subject_hash": wanted,
            "state": page["auto_state"], "reason": page["auto_reason"],
            "confirmed": False, "omitted": False, "second_look": None}


def main(argv: list[str]) -> int:
    book = None
    if argv:
        try:
            book = db.books.find_one({"_id": ObjectId(argv[0])})
        except InvalidId:
            pass
    if book is None:
        print(f"No book with id {argv[0] if argv else ''}.")
        return 1
    pages = list(db.pages.find({"book_id": book["_id"]}).sort("number", 1))
    for page in pages:
        if page.get("auto_state") is None:
            print(f"page {page['number']}: not processed yet, left as it is")
            continue
        fields = _reset(page)
        db.pages.update_one({"_id": page["_id"]}, {"$set": fields})
        label = fields["candidates"][fields["selected"]]["label"] if fields["selected"] is not None else "none"
        print(f"page {page['number']}: {fields['state']}, {label}")
    removed = db.approvals.delete_many({"page_id": {"$in": [p["_id"] for p in pages]}}).deleted_count
    print(f"{removed} approvals removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
