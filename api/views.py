"""Database documents to Contract 1 JSON. The only serializer: no path ever leaves through here."""
from datetime import datetime, timezone

from api import coords


def _iso(moment: datetime) -> str:
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")  # Mongo hands back naive UTC


def _candidate_json(candidate: dict, width: int, height: int) -> dict:
    return {
        "label": candidate["label"],
        "synonyms": candidate["synonyms"],
        "box": coords.box_to_fractions(candidate["box"], width, height),
        "confidence": candidate["confidence"],
        "mask_hash": candidate["mask_hash"],
        "source": candidate["source"],
    }


def page_json(page: dict) -> dict:
    width, height = page["width"], page["height"]
    look = page.get("second_look")
    if look and page["subject_hash"] is not None and look["subject_hash"] == page["subject_hash"]:
        look = {"status": look["status"], "answer": look["answer"], "detail": look["detail"]}
    else:
        look = None
    return {
        "id": str(page["_id"]),
        "book_id": str(page["book_id"]),
        "number": page["number"],
        "width": width,
        "height": height,
        "text": page["text"],
        "flags": page["flags"],
        "state": page["state"],
        "reason": page["reason"],
        "page_kind": page["page_kind"],
        "candidates": [_candidate_json(c, width, height) for c in page["candidates"]],
        "selected": page["selected"],
        "subject_hash": page["subject_hash"],
        "confirmed": page["confirmed"],
        "omitted": page["omitted"],
        "second_look": look,
    }


def book_json(book: dict, pages: list[dict]) -> dict:
    return {
        "id": str(book["_id"]),
        "title": book["title"],
        "credits": book["credits"],
        "state": book["state"],
        "page_count": book["page_count"],
        "created_at": _iso(book["created_at"]),
        "pages": [page_json(p) for p in pages],
    }


def profile_json(profile: dict) -> dict:
    return {
        "id": str(profile["_id"]),
        "name": profile["name"],
        "level": profile["level"],
        "settings": profile["settings"],
        "settings_hash": profile["settings_hash"],
        "contrast_override_note": profile["contrast_override_note"],
    }
