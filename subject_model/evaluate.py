"""Score the local mode (and Gemini) on hand-labelled pages: what is found, chosen first, named, and what the
teacher gets.

python -m subject_model.evaluate TESTSET_DIR [--modes local gemini] [--plain-crops]
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path

import cv2
import pymupdf

from pipeline.gemini import SubjectAnswer, choose_subjects
from pipeline.ingest import rasterize
from pipeline.masks import mask_box
from pipeline.process import call_with_retry, decide_state, gemini_box_to_pixels
from subject_model import local, namer
from subject_model.words import match

FOUND_IOU = 0.5
VIEW_MAX = 1600  # the pipeline's working size
OUTCOMES = ("ready_right", "ready_wrong", "asked", "nothing")


def _pages(testset_dir) -> list[Path]:
    return sorted(p for p in Path(testset_dir).glob("*.png") if not p.name.endswith("_mask.png"))


def load_labels(testset_dir) -> dict[str, tuple[str, str]]:
    """Page name to (subject name, typed text), from labels.csv. Every page must have a row."""
    with open(Path(testset_dir) / "labels.csv", newline="") as f:
        labels = {row["name"]: (row["label"], row["text"] or "") for row in csv.DictReader(f)}
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


def ask_gemini(view_path, text, cache=None) -> SubjectAnswer:
    """Gemini's answer, read from `cache` when it is there and written there after a call that worked."""
    if cache is not None and Path(cache).exists():
        return SubjectAnswer.model_validate_json(Path(cache).read_text())
    answer = call_with_retry(lambda: choose_subjects(view_path, text))
    if cache is not None:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(answer.model_dump_json())
    return answer


def _overlaps(answer, hand_box, width, height) -> list[float]:
    return [box_iou(gemini_box_to_pixels(c.box_2d, width, height), hand_box) for c in answer.candidates]


def judge(answer, hand_box, hand_label, width, height) -> tuple[bool, bool, bool]:
    """(found, first, named) for a SubjectAnswer against the hand rectangle and name."""
    overlaps = _overlaps(answer, hand_box, width, height)
    if not overlaps or max(overlaps) < FOUND_IOU:
        return False, False, False
    best = answer.candidates[overlaps.index(max(overlaps))]
    named = match(" ".join([best.label, *best.synonyms]), [hand_label]) is not None
    return True, overlaps[0] >= FOUND_IOU, named


def outcome(answer, hand_box, width, height) -> str:
    """What the teacher gets: ready_right, ready_wrong, asked or nothing."""
    if not answer.candidates:
        return "nothing"
    _, members, _ = decide_state(answer.page_kind, answer.candidates)
    if len(members) != 1:
        return "asked"
    box = gemini_box_to_pixels(answer.candidates[members[0]].box_2d, width, height)
    return "ready_right" if box_iou(box, hand_box) >= FOUND_IOU else "ready_wrong"


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
        return local.local_answer(view_path, text)
    if mode == "gemini":
        return ask_gemini(view_path, text, cache=Path(testset_dir) / "gemini" / f"{name}.json")
    raise ValueError(f"unknown mode {mode!r}")


def score(testset_dir, modes=("local",)) -> dict:
    """Counts for each mode over the hand-labelled pages; written to results_subjects.json."""
    testset_dir = Path(testset_dir)
    labels = load_labels(testset_dir)
    result = {"pages": [], "found": {}, "first": {}, "named": {}, "candidates": {}, "outcomes": {},
              "total": 0, "plain_crops": not namer.WHITEN}
    for mode in modes:
        for key in ("found", "first", "named", "candidates"):
            result[key][mode] = 0
        result["outcomes"][mode] = {name: 0 for name in OUTCOMES}
    with tempfile.TemporaryDirectory() as folder:
        for page in _pages(testset_dir):
            name = page.stem
            hand_label, typed = labels[name]
            hand_mask = cv2.imread(str(testset_dir / f"{name}_mask.png"), cv2.IMREAD_GRAYSCALE) > 127
            height, width = hand_mask.shape
            hand_box = mask_box(hand_mask)
            view_path = _working_copy(page, Path(folder))
            text = page_text(testset_dir, name, fallback=typed)
            row = {"name": name, "labels": {}, "found": {}, "first": {}, "named": {}, "outcome": {}, "error": {}}
            for mode in modes:
                try:
                    answer = _answer(mode, view_path, text, testset_dir, name)
                except Exception as error:
                    row["error"][mode] = f"{type(error).__name__}: {error}"
                    answer = SubjectAnswer(page_kind="scene")
                found, first, named = judge(answer, hand_box, hand_label, width, height)
                row["labels"][mode] = [c.label for c in answer.candidates]
                row["found"][mode], row["first"][mode], row["named"][mode] = found, first, named
                row["outcome"][mode] = outcome(answer, hand_box, width, height)
                result["found"][mode] += found
                result["first"][mode] += first
                result["named"][mode] += named
                result["candidates"][mode] += len(answer.candidates)
                result["outcomes"][mode][row["outcome"][mode]] += 1
            result["pages"].append(row)
            result["total"] += 1
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
    return (f"{mode}: found {result['found'][mode]} of {result['total']}, first {result['first'][mode]}, "
            f"named {result['named'][mode]}, ready right {o['ready_right']}, ready wrong {o['ready_wrong']}, "
            f"asked {o['asked']}, nothing {o['nothing']}, {result['candidates'][mode]} candidates")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Score subject finding on hand-labelled pages.")
    parser.add_argument("testset_dir")
    parser.add_argument("--modes", nargs="+", default=["local"], choices=["local", "gemini"])
    parser.add_argument("--plain-crops", action="store_true", help="name plain rectangles, not whitened cut-outs")
    parser.add_argument("--agree", action="store_true", help="agreement with Gemini on pages nobody picked")
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
        print(f"{row['name']:<24} " + " | ".join(cells), flush=True)
    for mode in args.modes:
        print(_summary(mode, result), flush=True)


if __name__ == "__main__":
    main()
