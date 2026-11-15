"""Score segmenters on the hand-labelled test pages.

    python -m cutout_model.evaluate data/cutout_testset [--names grabcut sam2 mirai] [--save-masks DIR]

Every segmenter gets the same prompt per page: the hand mask's box grown by 5% each side.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import cv2
import numpy as np

from pipeline.masks import clean_mask, iou, mask_box


def grow_box(box, width, height, amount=0.05):
    x0, y0, x1, y1 = box
    dx, dy = amount * (x1 - x0), amount * (y1 - y0)
    return (max(0.0, x0 - dx), max(0.0, y0 - dy), min(float(width), x1 + dx), min(float(height), y1 + dy))


def _read(path, flags):
    return cv2.imdecode(np.fromfile(str(path), np.uint8), flags)


def load_testset(testset_dir):
    """[(name, RGB page, mask)]. Raises ValueError naming the page for a missing, empty or wrong-size mask."""
    folder = Path(testset_dir)
    pages = sorted(p for p in folder.glob("*.png") if p.is_file() and not p.stem.endswith("_mask"))
    loaded, problems = [], []
    for page in pages:
        name = page.stem
        mask_path = folder / f"{name}_mask.png"
        image = _read(page, cv2.IMREAD_COLOR)
        if image is None:
            problems.append(f"{name}: page cannot be read")
            continue
        if not mask_path.exists():
            problems.append(f"{name}: hand mask {mask_path.name} is missing")
            continue
        mask = _read(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None or not (mask > 127).any():
            problems.append(f"{name}: hand mask is empty")
            continue
        if mask.shape != image.shape[:2]:
            problems.append(f"{name}: hand mask is {mask.shape[1]}x{mask.shape[0]}, page is {image.shape[1]}x{image.shape[0]}")
            continue
        loaded.append((name, cv2.cvtColor(image, cv2.COLOR_BGR2RGB), np.where(mask > 127, 255, 0).astype(np.uint8)))
    if problems:
        raise ValueError("; ".join(problems))
    if not loaded:
        raise ValueError(f"no test pages in {folder}")
    return loaded


def _run(name, image, box):
    if name == "mirai":
        from cutout_model.predict import predict
        return predict(image, box)
    from pipeline.segment import segment
    previous = os.environ.get("SEGMENTER")
    os.environ["SEGMENTER"] = name
    try:
        return segment(image, box=box)
    finally:
        if previous is None:
            os.environ.pop("SEGMENTER", None)
        else:
            os.environ["SEGMENTER"] = previous


def _device():
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return "cpu"


def score(testset_dir, names=("grabcut", "sam2", "mirai"), save_masks=None) -> dict:
    pages = load_testset(testset_dir)
    prompts = []
    for _, image, hand in pages:
        h, w = hand.shape
        prompts.append(grow_box(mask_box(hand), w, h))
    for name in names:  # untimed warm-up, so model loading is not counted
        _run(name, pages[0][1], prompts[0])
    if save_masks:
        Path(save_masks).mkdir(parents=True, exist_ok=True)

    rows = []
    for (page_name, image, hand), box in zip(pages, prompts):
        row = {"name": page_name, "iou": {}, "seconds": {}}
        for name in names:
            began = time.perf_counter()
            mask = clean_mask(_run(name, image, box))
            row["seconds"][name] = round(time.perf_counter() - began, 3)
            row["iou"][name] = round(iou(mask, hand), 4)
            if save_masks:
                cv2.imwrite(str(Path(save_masks) / f"{page_name}_{name}.png"), mask)
        rows.append(row)

    result = {"pages": rows,
              "mean_iou": {n: round(statistics.mean(r["iou"][n] for r in rows), 4) for n in names},
              "median_seconds": {n: round(statistics.median(r["seconds"][n] for r in rows), 3) for n in names},
              "device": _device()}
    with open(Path(testset_dir) / "results.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score segmenters on hand-labelled pages.")
    ap.add_argument("testset", type=Path)
    ap.add_argument("--names", nargs="+", default=["grabcut", "sam2", "mirai"])
    ap.add_argument("--save-masks", type=Path)
    args = ap.parse_args(argv)
    result = score(args.testset, tuple(args.names), args.save_masks)
    for row in result["pages"]:
        print(f"{row['name']:<24}" + "".join(f"  {n} {row['iou'][n]:.3f} ({row['seconds'][n]:.2f}s)" for n in args.names))
    print("mean IoU      ", result["mean_iou"])
    print("median seconds", result["median_seconds"])
    print("device        ", result["device"])


if __name__ == "__main__":
    main()
