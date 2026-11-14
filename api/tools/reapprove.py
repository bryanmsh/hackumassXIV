"""Copy one book's approvals from an earlier render version to the one the display code has now.

    python -m api.tools.reapprove <book_id> <old_render_version>

For emergencies only: a late render change voids every approval, and this brings a backup book
back without approving each sheet again. Run it only after someone has looked at the book's
contact sheets under the new version. It prints every record it writes.

For each page, child and look, the newest decision under the old version is copied, approve or
reject. A decision already made under the new version is left alone. Nothing is deleted.
"""
import sys
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from api import db, modules

SAME = ("page_id", "profile_id", "subject_hash", "settings_hash", "level")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python -m api.tools.reapprove <book_id> <old_render_version>")
        return 1
    try:
        book = db.books.find_one({"_id": ObjectId(argv[0])})
    except InvalidId:
        book = None
    if book is None:
        print(f"No book with id {argv[0]}.")
        return 1
    old, new = argv[1], modules.display.RENDER_VERSION
    if old == new:
        print(f"{new} is already the current render version. Nothing to copy.")
        return 1

    numbers = {page["_id"]: page["number"] for page in db.pages.find({"book_id": book["_id"]})}
    in_book = {"page_id": {"$in": list(numbers)}}
    newest = {}  # oldest first, so the newest decision on each version is the one left
    for record in db.approvals.find({**in_book, "render_version": old}).sort([("at", 1), ("_id", 1)]):
        newest[tuple(record[field] for field in SAME)] = record
    if not newest:
        found = sorted(db.approvals.distinct("render_version", in_book))
        print(f"No approvals for this book under render version {old}. "
              f"It has approvals under: {', '.join(found) or 'none'}.")
        return 1

    names = {profile["_id"]: profile["name"] for profile in db.profiles.find()}
    copied = 0
    for record in sorted(newest.values(), key=lambda r: (numbers[r["page_id"]], str(r["profile_id"]), r["level"])):
        same = {field: record[field] for field in SAME}
        if db.approvals.find_one({**same, "render_version": new}) is not None:
            continue
        db.approvals.insert_one({**same, "render_version": new, "decision": record["decision"],
                                 "at": datetime.now(timezone.utc), "copied_from": old})
        print(f"page {numbers[record['page_id']]}, {names.get(record['profile_id'], record['profile_id'])}, "
              f"look {record['level']}, {record['decision']}: {old} -> {new}")
        copied += 1
    print(f"{copied} approvals copied from {old} to {new}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
