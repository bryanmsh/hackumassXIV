"""Score the local mode (and saved Gemini answers) on hand-labelled pages: which main subjects are found and named, whether
the first choice is one of them, and what the teacher gets. A page may have several main subjects; labels.csv has
one row per subject, `name,label,x0,y0,x1,y1,text`, with the rectangle in the page picture's pixels. A label may
list several accepted names with `/` ("police officer/officer/woman"), so a general and a specific name both count.

python -m subject_model.evaluate TESTSET_DIR [--modes local gemini] [--plain-crops]

The app no longer calls Gemini (since 2026-11-15). The `gemini` mode reads the answers saved in
TESTSET_DIR/gemini/ when it still did, so our model can be compared with it; a page with no saved answer fails.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path

import cv2
import pymupdf

from pipeline.subjects import SubjectAnswer, local_is_enough
from pipeline.ingest import rasterize
from pipeline.process import box_to_pixels, decide_state
from subject_model import local, namer
from subject_model.words import match

FOUND_IOU = 0.5
VIEW_MAX = 1600  # the pipeline's working size
OUTCOMES = ("ready_right", "ready_wrong", "asked", "nothing")


def _pages(testset_dir) -> list[Path]:
    return sorted(p for p in Path(testset_dir).glob("*.png") if not p.name.endswith("_mask.png"))


def load_labels(testset_dir) -> dict[str, tuple[list, str]]:
    """Page name to ([(subject word, (x0, y0, x1, y1)), ...], typed text), from labels.csv, one row per main
    subject. Every page must have at least one row."""
    labels = {}
    with open(Path(testset_dir) / "labels.csv", newline="") as f:
        for row in csv.DictReader(f):
            subjects, typed = labels.setdefault(row["name"], ([], ""))
            subjects.append((row["label"], tuple(float(row[k]) for k in ("x0", "y0", "x1", "y1"))))
            if not typed and row.get("text"):
                labels[row["name"]] = (subjects, row["text"])
    missing = [p.stem for p in _pages(testset_dir) if p.stem not in labels]
    if missing:
        raise ValueError(f"no row in labels.csv for: {', '.join(missing)}")
    return labels


def page_text(testset_dir, name, fallback="") -> str:
    """The words the pipeline would get for page n of books/{book}.pdf, for a page named {book}_{n}."""
    book, _, number = name.rpartition("_")
    pdf = Path(testset_dir) / "books" / f"{book}.pdf"
    if not book or not number.isdigit() or not pdf.exists():
        return fallback
    with pymupdf.open(str(pdf)) as doc:
        if not 1 <= int(number) <= doc.page_count:
            return fallback
        return doc[int(number) - 1].get_text().strip()


def box_iou(a, b) -> float:
    shared = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - shared
    return shared / union if union > 0 else 0.0


def ask_gemini(view_path, text, cache) -> SubjectAnswer:
    """Gemini's answer saved in `cache` before the app stopped calling it. Raises when none was saved."""
    if not Path(cache).exists():
        raise FileNotFoundError(f"no saved Gemini answer: {Path(cache).name}")
    return SubjectAnswer.model_validate_json(Path(cache).read_text())


def ask_local(view_path, text) -> SubjectAnswer:
    """Our model's answer with `trusted` set, exactly as the pipeline gets it."""
    answer = local.local_answer(view_path, text)
    answer.trusted = local_is_enough(answer, text)[0]
    return answer


def _is_a_subject(candidate, hand_boxes, width, height) -> bool:
    box = box_to_pixels(candidate.box_2d, width, height)
    return any(box_iou(box, hand) >= FOUND_IOU for hand in hand_boxes)


def judge(answer, subjects, width, height) -> tuple[int, bool, int]:
    """(subjects found, first choice is a main subject, subjects named) for a SubjectAnswer against the
    page's main subjects, [(word, (x0, y0, x1, y1)), ...]."""
    boxes = [box_to_pixels(c.box_2d, width, height) for c in answer.candidates]
    found = named = 0
    for word, hand in subjects:
        overlaps = [box_iou(box, hand) for box in boxes]
        if not overlaps or max(overlaps) < FOUND_IOU:
            continue
        found += 1
        best = answer.candidates[overlaps.index(max(overlaps))]
        named += match(" ".join([best.label, *best.synonyms]), word.split("/")) is not None
    first = bool(answer.candidates) and _is_a_subject(answer.candidates[0], [h for _, h in subjects], width, height)
    return found, first, named


def outcome(answer, hand_boxes, width, height) -> str:
    """What the teacher gets: ready_right (the pre-selected one is a main subject), ready_wrong, asked or nothing."""
    if not answer.candidates:
        return "nothing"
    _, members, _ = decide_state(answer.page_kind, answer.candidates)
    if len(members) != 1 or not answer.trusted:
        return "asked"
    right = _is_a_subject(answer.candidates[members[0]], hand_boxes, width, height)
    return "ready_right" if right else "ready_wrong"


def _working_copy(page: Path, folder: Path) -> Path:
    image = cv2.imread(str(page), cv2.IMREAD_COLOR)
    height, width = image.shape[:2]
    scale = VIEW_MAX / max(height, width)
    if scale < 1:
        image = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    path = folder / page.name
    cv2.imwrite(str(path), image)
    return path


def _answer(mode, view_path, text, testset_dir, name) -> SubjectAnswer:
    if mode == "local":
        return ask_local(view_path, text)
    if mode == "gemini":
        return ask_gemini(view_path, text, cache=Path(testset_dir) / "gemini" / f"{name}.json")
    raise ValueError(f"unknown mode {mode!r}")


def score(testset_dir, modes=("local",)) -> dict:
    """Counts for each mode over the hand-labelled pages; written to results_subjects.json. `found` and `named`
    count main subjects (of `subjects`); `first` and the outcomes count pages (of `total`)."""
    testset_dir = Path(testset_dir)
    labels = load_labels(testset_dir)
    result = {"pages": [], "found": {}, "first": {}, "named": {}, "candidates": {}, "outcomes": {},
              "total": 0, "subjects": 0, "plain_crops": not namer.WHITEN}
    for mode in modes:
        for key in ("found", "first", "named", "candidates"):
            result[key][mode] = 0
        result["outcomes"][mode] = {name: 0 for name in OUTCOMES}
    with tempfile.TemporaryDirectory() as folder:
        for page in _pages(testset_dir):
            name = page.stem
            subjects, typed = labels[name]
            height, width = cv2.imread(str(page), cv2.IMREAD_GRAYSCALE).shape
            view_path = _working_copy(page, Path(folder))
            text = page_text(testset_dir, name, fallback=typed)
            row = {"name": name, "subjects": [word.split("/")[0] for word, _ in subjects], "labels": {}, "found": {},
                   "first": {}, "named": {}, "outcome": {}, "error": {}}
            for mode in modes:
                try:
                    answer = _answer(mode, view_path, text, testset_dir, name)
                except Exception as error:
                    row["error"][mode] = f"{type(error).__name__}: {error}"
                    answer = SubjectAnswer(page_kind="scene")
                found, first, named = judge(answer, subjects, width, height)
                row["labels"][mode] = [c.label for c in answer.candidates]
                row["found"][mode], row["first"][mode], row["named"][mode] = found, first, named
                row["outcome"][mode] = outcome(answer, [box for _, box in subjects], width, height)
                result["found"][mode] += found
                result["first"][mode] += first
                result["named"][mode] += named
                result["candidates"][mode] += len(answer.candidates)
                result["outcomes"][mode][row["outcome"][mode]] += 1
            result["pages"].append(row)
            result["total"] += 1
            result["subjects"] += len(subjects)
    (testset_dir / "results_subjects.json").write_text(json.dumps(result, indent=2))
    return result


def _xyxy(box_2d):
    ymin, xmin, ymax, xmax = box_2d
    return min(xmin, xmax), min(ymin, ymax), max(xmin, xmax), max(ymin, ymax)


def agree(testset_dir, every=3, limit=20) -> dict:
    """How often the local mode's first choice is one of Gemini's subjects, on pages nobody picked:
    every `every`-th page of each book, leaving out hand-labelled pages, at most `limit` pages.
    Written to results_agreement.json."""
    testset_dir = Path(testset_dir)
    result = {"pages": [], "agree": 0, "named": 0, "total": 0, "failed": []}
    taken = 0
    for pdf in sorted((testset_dir / "books").glob("*.pdf")):
        if taken >= limit:
            break
        for asset in rasterize(pdf, testset_dir / "agreement" / pdf.stem):
            name = f"{pdf.stem}_{asset.page_number}"
            if asset.page_number % every or (testset_dir / f"{name}.png").exists():
                continue
            if taken >= limit:
                break
            taken += 1
            try:
                mine = local.local_answer(asset.view_path, asset.text)
                theirs = ask_gemini(asset.view_path, asset.text, cache=testset_dir / "gemini" / f"{name}.json")
            except Exception:
                result["failed"].append(name)
                continue
            agrees, named = not mine.candidates and not theirs.candidates, False
            if mine.candidates:
                first = mine.candidates[0]
                for other in theirs.candidates:
                    if box_iou(_xyxy(first.box_2d), _xyxy(other.box_2d)) >= FOUND_IOU:
                        agrees = True
                        if match(" ".join([other.label, *other.synonyms]), [first.label]):
                            named = True
                            break
            result["pages"].append({"name": name, "agree": agrees, "named": named})
            result["agree"] += agrees
            result["named"] += named
            result["total"] += 1
    (testset_dir / "results_agreement.json").write_text(json.dumps(result, indent=2))
    return result


def _summary(mode, result) -> str:
    o = result["outcomes"][mode]
    return (f"{mode}: found {result['found'][mode]} of {result['subjects']} subjects, named {result['named'][mode]}; "
            f"first choice a main subject on {result['first'][mode]} of {result['total']} pages, "
            f"ready right {o['ready_right']}, ready wrong {o['ready_wrong']}, "
            f"asked {o['asked']}, nothing {o['nothing']}, {result['candidates'][mode]} candidates")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Score subject finding on hand-labelled pages.")
    parser.add_argument("testset_dir")
    parser.add_argument("--modes", nargs="+", default=["local"], choices=["local", "gemini"])
    parser.add_argument("--plain-crops", action="store_true", help="name plain rectangles, not whitened cut-outs")
    parser.add_argument("--agree", action="store_true", help="agreement with saved Gemini answers on pages nobody picked")
    parser.add_argument("--every", type=int, default=3)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if args.plain_crops:
        namer.WHITEN = False
    if args.agree:
        result = agree(args.testset_dir, every=args.every, limit=args.limit)
        for row in result["pages"]:
            print(f"{row['name']:<24} agree {row['agree']!s:<5} named {row['named']}", flush=True)
        if result["failed"]:
            print(f"failed: {', '.join(result['failed'])}", flush=True)
        print(f"agreement: {result['agree']} of {result['total']} pages, names agree on {result['named']}",
              flush=True)
        return
    result = score(args.testset_dir, modes=tuple(args.modes))
    for row in result["pages"]:
        cells = [f"{mode}: {', '.join(row['labels'][mode]) or '-'} ({row['outcome'][mode]})"
                 + (f" [{row['error'][mode]}]" if mode in row["error"] else "") for mode in args.modes]
        print(f"{row['name']:<24} [{', '.join(row['subjects'])}] " + " | ".join(cells), flush=True)
    for mode in args.modes:
        print(_summary(mode, result), flush=True)


if __name__ == "__main__":
    main()
