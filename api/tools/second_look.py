"""Run the second look for confirmed pages that have no result for their subject.

    python -m api.tools.second_look [book_id]
"""
import sys

from bson import ObjectId
from bson.errors import InvalidId

from api import db, jobs


def _needs_it(page: dict) -> bool:
    look = page.get("second_look")
    return (page["subject_hash"] is not None
            and (look is None or look["status"] == "pending" or look["subject_hash"] != page["subject_hash"]))


def main(argv: list[str]) -> int:
    query = {"confirmed": True}
    if argv:
        try:
            book = db.books.find_one({"_id": ObjectId(argv[0])})
        except InvalidId:
            book = None
        if book is None:
            print(f"No book with id {argv[0]}.")
            return 1
        query["book_id"] = book["_id"]
    for page in db.pages.find(query).sort([("book_id", 1), ("number", 1)]):
        if not _needs_it(page):
            continue
        jobs.run_second_look(page["_id"], page["subject_hash"])
        look = (db.pages.find_one({"_id": page["_id"]}) or {}).get("second_look") or {}
        print(page["_id"], page["number"], look.get("status"), look.get("answer"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
