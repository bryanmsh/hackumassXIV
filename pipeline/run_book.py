"""Process a whole PDF from the command line, with no API and no database.

    python -m pipeline.run_book <pdf> <out_dir>

Writes the same files the API would (out_dir/source.pdf, pages/, masks/) plus
out_dir/summary.json, and prints each page's state, reason and time.
Reads .env from the current folder for GEMINI_API_KEY and the other settings.
"""
import json
import os
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from contracts.types import PageResult
from pipeline.ingest import rasterize
from pipeline.process import process_page

DEFAULT_CONCURRENCY = 4


def load_env(path=".env") -> None:
    """Set names from a KEY=VALUE file that are not already set. Prints nothing."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        name, separator, value = line.strip().partition("=")
        value = value.strip().strip('"').strip("'")
        if not separator or not name or name.startswith("#") or " " in name or not value:
            continue
        os.environ.setdefault(name, value)


def _one_page(asset, out_dir) -> dict:
    start = time.time()
    try:
        result = process_page(asset, out_dir)
    except Exception as error:  # process_page should never raise; a runner must not die if it does
        result = PageResult(state="failed", page_kind=None, candidates=[], selected=None,
                            reason=f"{type(error).__name__}: {error}"[:200])
    return {"page_number": asset.page_number, "state": result.state, "page_kind": result.page_kind,
            "reason": result.reason, "seconds": round(time.time() - start, 2), "flags": asset.flags,
            "candidates": [candidate.model_dump(mode="json") for candidate in result.candidates],
            "selected": result.selected}


def run_book(pdf_path, out_dir, concurrency=DEFAULT_CONCURRENCY, on_page=None) -> dict:
    """Rasterize, then process `concurrency` pages at a time. Returns and saves the summary."""
    start = time.time()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf_path, out_dir / "source.pdf")
    assets = rasterize(pdf_path, out_dir)
    pages = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for page in pool.map(lambda asset: _one_page(asset, out_dir), assets):  # in page order
            pages.append(page)
            if on_page:
                on_page(page)
    summary = {"pdf": str(pdf_path), "pages": pages,
               "counts": dict(Counter(page["state"] for page in pages)),
               "total_seconds": round(time.time() - start, 2)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _print_page(page: dict) -> None:
    print(f"page {page['page_number']:>2}  {page['state']:<17} {page['reason'] or '-'}  {page['seconds']:.1f}s",
          flush=True)


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: python -m pipeline.run_book <pdf> <out_dir>", file=sys.stderr)
        return 2
    pdf_path, out_dir = argv
    if not Path(pdf_path).is_file():
        print(f"no such PDF: {pdf_path}", file=sys.stderr)
        return 1
    concurrency = int(os.environ.get("PAGE_CONCURRENCY") or DEFAULT_CONCURRENCY)
    summary = run_book(pdf_path, out_dir, concurrency, on_page=_print_page)
    counts = ", ".join(f"{state} {count}" for state, count in sorted(summary["counts"].items()))
    print(f"{len(summary['pages'])} pages in {summary['total_seconds']:.1f}s: {counts}")
    print(f"summary: {Path(out_dir) / 'summary.json'}")
    return 0


if __name__ == "__main__":
    load_env()
    sys.exit(main(sys.argv[1:]))
