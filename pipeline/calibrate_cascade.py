"""Set the cut-out cascade's threshold by measuring it, not guessing it.

    python -m pipeline.calibrate_cascade <source> [--fallback sam2] [--margin M] [--out DIR]

<source> is one of two things:
  a test set   the layout cutout_model/evaluate.py reads: {name}.png and {name}_mask.png (white
               on the subject). Every page gets the same prompt as there: the hand mask's box
               grown by 5% on each side. IoU is against the hand masks. Default margin 0.02.
  a book run   a pipeline.run_book output folder (summary.json, pages/). Every single-subject
               candidate's box is a prompt; combined cut-outs are left out, since the pipeline
               builds those by joining single ones. There are no hand masks, so the fallback's
               own mask is the reference: "IoU" is agreement with SAM, not accuracy, and the
               fallback alone scores 1.0 by definition. Default margin 0.10.

Each page is cut once by our model and once by the fallback. Then every threshold is tried
on those results: pages scoring at least the threshold keep our mask, the rest take the
fallback's. For each threshold it reports the share of pages our model kept, the mean IoU
against the hand masks, and the mean seconds per page. The recommended threshold keeps the
most pages on our model while staying within `margin` IoU of the fallback alone.

This is the calibration step of LOTUS-style cascades, done once on held-out pages instead of
per batch: a picture book is too few pages to sample from. No statistical guarantee is claimed.

Writes calibration.json, calibration.csv and calibration.svg (the chart for the pitch).
"""
import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from pipeline import cascade
from pipeline.masks import clean_mask, iou, mask_box

PROMPT_GROW = 0.05  # the same prompt cutout_model/evaluate.py uses
THRESHOLDS = [round(i * 0.05, 2) for i in range(21)]
DEFAULT_MARGIN = 0.02  # test set: within 0.02 IoU of the fallback against hand masks
BOOK_MARGIN = 0.10  # book run: mean agreement with the fallback of at least 0.90
JOIN_SLACK = 1.0  # px: a box that is the union of others' boxes to within this is a combined cut-out


def grow_box(box, width, height, amount=PROMPT_GROW):
    x0, y0, x1, y1 = box
    dx, dy = amount * (x1 - x0), amount * (y1 - y0)
    return (max(0.0, x0 - dx), max(0.0, y0 - dy), min(float(width), x1 + dx), min(float(height), y1 + dy))


def _read(path, flags):
    if not Path(path).is_file():
        return None
    return cv2.imdecode(np.fromfile(str(path), np.uint8), flags)


def load_testset(folder) -> list[tuple]:
    """[(name, RGB page, 0/255 hand mask, prompt box)]. Pages without a usable mask are skipped and named on stderr."""
    folder = Path(folder)
    items = []
    for page in sorted(p for p in folder.glob("*.png") if not p.stem.endswith("_mask")):
        image = _read(page, cv2.IMREAD_COLOR)
        mask = _read(folder / f"{page.stem}_mask.png", cv2.IMREAD_GRAYSCALE)
        if image is None or mask is None or mask.shape != image.shape[:2] or not (mask > 127).any():
            print(f"skipped {page.name}: no usable hand mask", file=sys.stderr)
            continue
        hand = np.where(mask > 127, 255, 0).astype(np.uint8)
        items.append((page.stem, cv2.cvtColor(image, cv2.COLOR_BGR2RGB), hand,
                      grow_box(mask_box(hand), hand.shape[1], hand.shape[0])))
    if not items:
        raise ValueError(f"no test pages with hand masks in {folder}")
    return items


def _contains(outer, inner) -> bool:
    return (inner[0] >= outer[0] - JOIN_SLACK and inner[1] >= outer[1] - JOIN_SLACK
            and inner[2] <= outer[2] + JOIN_SLACK and inner[3] <= outer[3] + JOIN_SLACK)


def is_combined(box, others) -> bool:
    """True when `box` is the bounding box of two or more of the other boxes: a joined cut-out."""
    inside = [o for o in others if _contains(box, o)]
    if len(inside) < 2:
        return False
    union = (min(o[0] for o in inside), min(o[1] for o in inside), max(o[2] for o in inside), max(o[3] for o in inside))
    return all(abs(a - b) <= JOIN_SLACK for a, b in zip(union, box))


def load_book_run(run_dir) -> list[tuple]:
    """[(name, RGB page, None, box)] for every single-subject candidate in a run_book output folder."""
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    items = []
    for page in summary["pages"]:
        boxes = [tuple(c["box"]) for c in page["candidates"]]
        singles = [b for i, b in enumerate(boxes) if not is_combined(b, boxes[:i] + boxes[i + 1:])]
        if not singles:
            continue
        image = _read(run_dir / "pages" / f"{page['page_number']}.png", cv2.IMREAD_COLOR)
        if image is None:
            print(f"skipped page {page['page_number']}: no page image", file=sys.stderr)
            continue
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        for i, box in enumerate(singles):
            items.append((f"page{page['page_number']}_{i}", image, None, box))
    if not items:
        raise ValueError(f"no single-subject candidates in {run_dir / 'summary.json'}")
    return items


def load(source):
    """(items, kind): a book run when the folder has summary.json, else a hand-masked test set."""
    if (Path(source) / "summary.json").is_file():
        return load_book_run(source), "book"
    return load_testset(source), "testset"


def measure(items, fallback="sam2") -> list[dict]:
    """One row per prompt: our confidence and checks, both models' IoU and seconds.
    With no hand mask the fallback's mask is the reference, so iou_fallback is 1.0."""
    from pipeline.segment import _SEGMENTERS
    run_fallback = _SEGMENTERS[fallback]
    _, image, _, box = items[0]  # untimed warm-up, so loading a model is not counted
    cascade.ours_probability(image, box)
    run_fallback(image, box, [])

    rows = []
    for name, image, hand, box in items:
        started = time.perf_counter()
        prob = cascade.ours_probability(image, box)
        flipped = cascade._flipped_probability(image, box) if cascade.use_flip() else None
        score, parts = cascade.mask_confidence(prob, box, flipped)
        ours = clean_mask(np.where(prob > 0.5, 255, 0).astype(np.uint8))
        ours_seconds = time.perf_counter() - started

        started = time.perf_counter()
        theirs = clean_mask(run_fallback(image, box, []))
        fallback_seconds = time.perf_counter() - started
        reference = theirs if hand is None else hand
        rows.append({"name": name, "confidence": round(score, 3), "parts": parts,
                     "iou_ours": round(iou(ours, reference), 4), "iou_fallback": round(iou(theirs, reference), 4),
                     "agreement": round(iou(ours, theirs), 4),
                     "seconds_ours": round(ours_seconds, 3), "seconds_fallback": round(fallback_seconds, 3)})
    return rows


def sweep(rows, thresholds=THRESHOLDS) -> list[dict]:
    """What the cascade would have done at each threshold. Every page pays for our model; unsure ones also pay the fallback."""
    out = []
    for threshold in thresholds:
        kept = [row["confidence"] >= threshold for row in rows]
        out.append({
            "threshold": threshold,
            "share_ours": round(sum(kept) / len(rows), 4),
            "mean_iou": round(statistics.mean(r["iou_ours"] if k else r["iou_fallback"] for r, k in zip(rows, kept)), 4),
            "mean_seconds": round(statistics.mean(
                r["seconds_ours"] + (0 if k else r["seconds_fallback"]) for r, k in zip(rows, kept)), 3),
        })
    return out


def recommend(rows, swept, margin=DEFAULT_MARGIN) -> dict:
    """The threshold that keeps the most pages on our model within `margin` IoU of the fallback alone.
    A tie goes to the higher, stricter threshold."""
    target = statistics.mean(r["iou_fallback"] for r in rows) - margin
    allowed = [s for s in swept if s["mean_iou"] >= target]
    if not allowed:  # nothing reaches it: send everything to the fallback
        return max(swept, key=lambda s: s["threshold"])
    return max(allowed, key=lambda s: (s["share_ours"], s["threshold"]))


def summary(rows, swept, chosen, margin) -> dict:
    return {
        "pages": len(rows),
        "ours_alone": {"mean_iou": round(statistics.mean(r["iou_ours"] for r in rows), 4),
                       "mean_seconds": round(statistics.mean(r["seconds_ours"] for r in rows), 3)},
        "fallback_alone": {"mean_iou": round(statistics.mean(r["iou_fallback"] for r in rows), 4),
                           "mean_seconds": round(statistics.mean(r["seconds_fallback"] for r in rows), 3)},
        "margin": margin,
        "chosen": chosen,
        "speedup_vs_fallback": round(statistics.mean(r["seconds_fallback"] for r in rows) / chosen["mean_seconds"], 2)
        if chosen["mean_seconds"] > 0 else None,
    }


def chart_svg(swept, result) -> str:
    """Share of pages cut by our model (x) against mean IoU (y), the fallback-alone line, and the chosen point."""
    width, height, left, right, top, bottom = 640, 400, 64, 24, 40, 56
    ious = [s["mean_iou"] for s in swept] + [result["fallback_alone"]["mean_iou"], result["ours_alone"]["mean_iou"]]
    y_low = max(0.0, np.floor(min(ious) * 20) / 20 - 0.05)
    y_high = min(1.0, np.ceil(max(ious) * 20) / 20 + 0.02)

    def x(share):
        return left + share * (width - left - right)

    def y(value):
        return top + (y_high - value) / max(1e-9, y_high - y_low) * (height - top - bottom)

    points = sorted({(s["share_ours"], s["mean_iou"]) for s in swept})
    path = " ".join(f"{'M' if i == 0 else 'L'}{x(a):.1f},{y(b):.1f}" for i, (a, b) in enumerate(points))
    fallback_y = y(result["fallback_alone"]["mean_iou"])
    chosen = result["chosen"]
    ticks = []
    for i in range(6):
        share = i / 5
        ticks.append(f'<text x="{x(share):.1f}" y="{height - bottom + 18}" text-anchor="middle">{int(share * 100)}%</text>')
    step = 0.05 if y_high - y_low <= 0.4 else 0.1
    value = np.ceil(y_low / step) * step
    while value <= y_high + 1e-9:
        ticks.append(f'<text x="{left - 8}" y="{y(value) + 4:.1f}" text-anchor="end">{value:.2f}</text>')
        ticks.append(f'<line x1="{left}" x2="{width - right}" y1="{y(value):.1f}" y2="{y(value):.1f}" class="grid"/>')
        value += step
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="system-ui, sans-serif" font-size="12">
<style>.grid{{stroke:#d8d8d8;stroke-width:1}} .axis{{stroke:#555}} .curve{{fill:none;stroke:#2f6fdf;stroke-width:2.5}}
.base{{stroke:#c0392b;stroke-dasharray:6 4;stroke-width:1.5}} text{{fill:#333}}</style>
<rect width="{width}" height="{height}" fill="#fff"/>
<text x="{left}" y="22" font-size="15" font-weight="600">Cut-out cascade: pages our model keeps vs accuracy</text>
{''.join(ticks)}
<line x1="{left}" x2="{left}" y1="{top}" y2="{height - bottom}" class="axis"/>
<line x1="{left}" x2="{width - right}" y1="{height - bottom}" y2="{height - bottom}" class="axis"/>
<line x1="{left}" x2="{width - right}" y1="{fallback_y:.1f}" y2="{fallback_y:.1f}" class="base"/>
<text x="{width - right}" y="{fallback_y - 6:.1f}" text-anchor="end" fill="#c0392b">SAM alone {result["fallback_alone"]["mean_iou"]:.3f}</text>
<path d="{path}" class="curve"/>
<circle cx="{x(chosen["share_ours"]):.1f}" cy="{y(chosen["mean_iou"]):.1f}" r="6" fill="#2f6fdf" stroke="#fff" stroke-width="2"/>
<text x="{x(chosen["share_ours"]) + 10:.1f}" y="{y(chosen["mean_iou"]) + 18:.1f}">threshold {chosen["threshold"]:.2f}: {chosen["share_ours"]:.0%} ours, IoU {chosen["mean_iou"]:.3f}</text>
<text x="{(left + width - right) / 2}" y="{height - 14}" text-anchor="middle">share of pages cut by our model</text>
<text x="16" y="{(top + height - bottom) / 2}" text-anchor="middle" transform="rotate(-90 16 {(top + height - bottom) / 2})">{"agreement with SAM (IoU)" if result.get("kind") == "book" else "mean IoU vs hand masks"}</text>
</svg>"""


def calibrate(source, out_dir=None, fallback="sam2", margin=None) -> dict:
    items, kind = load(source)
    if margin is None:
        margin = BOOK_MARGIN if kind == "book" else DEFAULT_MARGIN
    rows = measure(items, fallback)
    swept = sweep(rows)
    result = summary(rows, swept, recommend(rows, swept, margin), margin)
    result["fallback"], result["kind"] = fallback, kind
    result["reference"] = "the fallback's own mask (agreement, not accuracy)" if kind == "book" else "hand masks"
    result["sweep"], result["rows"] = swept, rows
    out = Path(out_dir or source)
    out.mkdir(parents=True, exist_ok=True)
    (out / "calibration.json").write_text(json.dumps(result, indent=2))
    with open(out / "calibration.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(swept[0]))
        writer.writeheader()
        writer.writerows(swept)
    (out / "calibration.svg").write_text(chart_svg(swept, result), encoding="utf-8")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="a hand-masked test set, or a run_book output folder")
    parser.add_argument("--fallback", default="sam2")
    parser.add_argument("--margin", type=float, default=None,
                        help=f"IoU the cascade may give up against the fallback alone (default {DEFAULT_MARGIN}, book {BOOK_MARGIN})")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = calibrate(args.source, args.out, args.fallback, args.margin)
    chosen = result["chosen"]
    print(f"{result['pages']} prompts ({result['kind']}, IoU against {result['reference']}). Ours alone IoU {result['ours_alone']['mean_iou']:.3f} "
          f"({result['ours_alone']['mean_seconds']:.2f} s), {args.fallback} alone "
          f"{result['fallback_alone']['mean_iou']:.3f} ({result['fallback_alone']['mean_seconds']:.2f} s)")
    print(f"Set CASCADE_MIN_CONFIDENCE={chosen['threshold']}: {chosen['share_ours']:.0%} of pages cut by our model, "
          f"IoU {chosen['mean_iou']:.3f}, {chosen['mean_seconds']:.2f} s a page "
          f"({result['speedup_vs_fallback']}x the fallback's speed)")
    print(f"Wrote calibration.json, calibration.csv and calibration.svg in {args.out or args.source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
