"""Book routes."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError

from api import db, jobs, settings, views

router = APIRouter(prefix="/api")

CREDIT_KEYS = ("author", "illustrator", "publisher", "source", "license")
CHUNK = 1024 * 1024


class Credits(BaseModel):
    author: str | None = None
    illustrator: str | None = None
    publisher: str | None = None
    source: str | None = None
    license: str | None = None


class BookPatch(BaseModel):
    title: str | None = None
    credits: Credits | None = None


def _book_response(book: dict) -> dict:
    pages = list(db.pages.find({"book_id": book["_id"]}).sort("number", 1))
    return views.book_json(book, pages)


def _find_book(book_id: str) -> dict:
    book = db.books.find_one({"_id": db.oid(book_id)})
    if book is None:
        raise HTTPException(404, "not found")
    return book


@router.post("/books")
def upload_book(file: UploadFile, background: BackgroundTasks, title: str | None = Form(None),
                credits: str | None = Form(None)):
    try:
        given = Credits.model_validate(json.loads(credits)) if credits else Credits()
    except (ValueError, ValidationError):
        raise HTTPException(422, "credits must be a JSON object of text values.")

    chunks, size = [], 0
    while chunk := file.file.read(CHUNK):
        size += len(chunk)
        if size > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "The file is over 50 MB.")
        chunks.append(chunk)
    data = b"".join(chunks)

    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
        page_count = pdf.page_count
        pdf.close()
    except Exception:
        raise HTTPException(400, "This file is not a readable PDF.")
    if page_count > settings.MAX_UPLOAD_PAGES:
        raise HTTPException(413, "The book is over 30 pages.")

    book_id = ObjectId()
    directory = jobs.book_dir(book_id)
    directory.mkdir(parents=True)
    (directory / "source.pdf").write_bytes(data)
    db.books.insert_one({
        "_id": book_id, "title": title or Path(file.filename or "").stem or "Untitled",
        "credits": {key: getattr(given, key) for key in CREDIT_KEYS},
        "state": "ingesting", "page_count": 0, "created_at": datetime.now(timezone.utc)})
    background.add_task(jobs.ingest_book, book_id)
    return {"book_id": str(book_id), "state": "ingesting"}


@router.get("/books")
def list_books():
    return [_book_response(book) for book in db.books.find().sort("created_at", -1)]


@router.get("/books/{book_id}")
def get_book(book_id: str):
    return _book_response(_find_book(book_id))


@router.patch("/books/{book_id}")
def update_book(book_id: str, patch: BookPatch):
    book = _find_book(book_id)
    changes = {}
    if patch.title is not None:
        changes["title"] = patch.title
    if patch.credits is not None:
        for key, value in patch.credits.model_dump(exclude_unset=True).items():
            changes[f"credits.{key}"] = value
    if changes:
        db.books.update_one({"_id": book["_id"]}, {"$set": changes})
    return _book_response(db.books.find_one({"_id": book["_id"]}))


@router.post("/books/{book_id}/confirm-all")
def confirm_all(book_id: str, background: BackgroundTasks):
    """Confirm every ready page that has a subject and is neither left out nor already confirmed."""
    book = _find_book(book_id)
    waiting = db.pages.find({"book_id": book["_id"], "state": "ready", "selected": {"$ne": None},
                             "omitted": False, "confirmed": False}).sort("number", 1)
    done = []
    for page in waiting:
        written = db.pages.update_one({"_id": page["_id"], "subject_hash": page["subject_hash"],
                                       "state": {"$ne": "processing"}}, {"$set": {"confirmed": True}})
        if written.matched_count == 0:               # the subject changed since it was read: not reviewed
            continue
        if jobs.start_second_look(page):
            background.add_task(jobs.run_second_look, page["_id"], page["subject_hash"])
        done.append(views.page_json(db.pages.find_one({"_id": page["_id"]})))
    return done


@router.post("/books/{book_id}/rerun")
def rerun_book(book_id: str, background: BackgroundTasks):
    """Ask the pipeline again about every page that is not left out or already processing.
    New suggestions are added to the old ones. A confirmed page keeps its subject and its
    confirmation; any other page's subject becomes the pipeline's new answer.
    Returns the pages now processing."""
    book = _find_book(book_id)
    started = datetime.now(timezone.utc)
    open_pages = {"omitted": False, "state": {"$ne": "processing"}}
    page_ids = []
    for page in db.pages.find({"book_id": book["_id"], **open_pages}).sort("number", 1):
        # Checked again in the write: a page left out since it was read is left alone.
        taken = db.pages.update_one({"_id": page["_id"], **open_pages}, {"$set": {
            "state": "processing", "reason": None, "processing_started_at": started}})
        if taken.matched_count:
            page_ids.append(page["_id"])
    if page_ids:
        background.add_task(jobs.process_pages, page_ids)
    return [views.page_json(page) for page in db.pages.find({"_id": {"$in": page_ids}}).sort("number", 1)]
