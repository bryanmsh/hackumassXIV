"""Run a whole book through the real page code with the local mode in Gemini's place. No Gemini call.

python -m subject_model.try_book PDF OUT_DIR
"""
from __future__ import annotations

import argparse

import pipeline.process
from pipeline.run_book import run_book
from subject_model import local


def run(pdf_path, out_dir, concurrency=4) -> dict:
    """run_book's summary, with local.local_answer standing in for pipeline.process.choose_subjects."""
    before = pipeline.process.choose_subjects
    pipeline.process.choose_subjects = lambda view_path, text: local.local_answer(view_path, text)
    try:
        return run_book(pdf_path, out_dir, concurrency)
    finally:
        pipeline.process.choose_subjects = before


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run a book through the page code with the local subject finder.")
    parser.add_argument("pdf")
    parser.add_argument("out_dir")
    args = parser.parse_args(argv)
    summary = run(args.pdf, args.out_dir)
    for page in summary["pages"]:
        labels = ", ".join(c["label"] for c in page["candidates"]) or "-"
        print(f"page {page['page_number']:>2}  {page['state']:<17} {labels:<30} {page['reason'] or '-'}  "
              f"{page['seconds']:.1f}s", flush=True)
    print(f"{summary['counts']} in {summary['total_seconds']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
