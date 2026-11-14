"""Render and check every candidate of a book that Bryan's pipeline processed.

    python -m pipeline.run_book book.pdf data/books/my-book       # Bryan's step: makes summary.json
    python -m render.try_book data/books/my-book [--out DIR]

For each page and candidate it writes the overlay and all four looks, runs every check, and
prints one line per look. No AI calls.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from checks import run_checks

from . import overlay, render
from .core import load_mask, load_rgb

HERE = Path(__file__).resolve().parent
LEVEL_NAMES = {1: "tinted", 2: "cutout", 3: "faded", 4: "outlined"}
PROFILE = {"colors": ["#E53935"], "background": "#000000", "size": "medium",
           "position": "center", "text_mode": "below", "outline": "off"}
CHECKS = ("fidelity", "page_edge", "background", "contrast", "size", "text_contrast")


def page_text(book: Path, number: int) -> str:
    try:
        import pymupdf
        with pymupdf.open(book / "source.pdf") as doc:
            return doc[number - 1].get_text().strip()
    except Exception:  # noqa: BLE001
        return ""


def short(result) -> str:
    parts = []
    for name in CHECKS:
        item = getattr(result, name)
        if item is None:
            continue
        if item.status != "pass":
            parts.append(f"{name}={item.status.upper()}")
    return ", ".join(parts) or "all pass"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    book = args.book
    out = args.out or HERE / "out" / book.name
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((book / "summary.json").read_text(encoding="utf-8"))

    times, details = [], []
    for page in summary["pages"]:
        n = page["page_number"]
        master, view = book / "pages" / f"{n}.png", book / "pages" / f"{n}_view.png"
        text = page_text(book, n)
        print(f"page {n}: {page['state']} ({page.get('reason') or ''})")
        load_rgb(master), load_rgb(view)
        for i, cand in enumerate(page["candidates"]):
            mask = Path(cand["mask_path"])
            if not mask.is_absolute() and not mask.exists():
                mask = book / "masks" / mask.name
            load_mask(mask)
            tag = f"{n}_{i}_{cand['label'].replace(' ', '-')}"
            (out / f"{tag}_overlay.webp").write_bytes(overlay(view, mask))
            print(f"  [{i}] {cand['label']} ({cand['confidence']:.2f})")
            for level in (1, 2, 3, 4):
                t0 = time.perf_counter()
                data = render(master, view, mask, PROFILE, level, text)
                times.append((time.perf_counter() - t0) * 1000)
                (out / f"{tag}_{level}_{LEVEL_NAMES[level]}.webp").write_bytes(data)
                result = run_checks(master, view, mask, PROFILE, level, text)
                print(f"      {LEVEL_NAMES[level]:<8} {short(result)}")
                details.append({"page": n, "candidate": i, "label": cand["label"], "level": level,
                                "checks": result.model_dump()})
    (out / "checks.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    times.sort()
    print(f"{len(times)} renders: median {times[len(times) // 2]:.0f} ms, worst {times[-1]:.0f} ms")
    print("wrote", out)


if __name__ == "__main__":
    main()
