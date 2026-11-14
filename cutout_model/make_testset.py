"""Build a test set from held-out drawn cut-outs, so no one paints masks by hand.

    python -m cutout_model.make_testset --cutouts DIR --backgrounds DIR --out DIR [--count 100] [--seed 0]

Each page is a background with 1 to 3 transparent cut-outs pasted on it (`paste.compose`). The
subject is the last one pasted, which is on top, and its mask is that cut-out's own transparency,
so no model makes any label. Writes `{out}/anime_{i:03d}.png` and `anime_{i:03d}_mask.png` (white
on the subject), the layout `evaluate.py` reads, plus `manifest.json` naming the source files.

The cut-out and background files must come from archives that training never sees; the notebook
checks this.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from cutout_model.data import read_rgb
from cutout_model.paste import compose, read_rgba

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _files(folder, suffixes):
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"no such folder: {folder}")
    found = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in suffixes)
    if not found:
        raise FileNotFoundError(f"no images in {folder}")
    return found


def make_testset(cutouts_dir, backgrounds_dir, out_dir, count=100, seed=0, canvas=1024,
                 min_fraction=0.02, max_fraction=0.6) -> list[dict]:
    """Writes `count` pages and masks to `out_dir`; returns the manifest rows. Same seed, same pages."""
    cutouts = _files(cutouts_dir, {".png"})
    backgrounds = _files(backgrounds_dir, IMAGE_SUFFIXES)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows, tries = [], 0
    while len(rows) < count:
        tries += 1
        if tries > count * 50:
            raise ValueError(f"made only {len(rows)} of {count} pages: check the cut-outs have transparency")
        background_path = backgrounds[rng.integers(len(backgrounds))]
        chosen = [cutouts[rng.integers(len(cutouts))] for _ in range(rng.integers(1, 4))]
        art = [read_rgba(p) for p in chosen]
        if any(a is None for a in art):
            continue
        try:
            background = read_rgb(background_path)
        except Exception:
            continue
        if background is None:
            continue
        picture, mask = compose(background, art, rng, canvas=canvas)
        if not (min_fraction <= mask.mean() <= max_fraction):
            continue                                   # subject too small to box, or the whole page
        name = f"anime_{len(rows):03d}"
        cv2.imwrite(str(out / f"{name}.png"), cv2.cvtColor(picture, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(out / f"{name}_mask.png"), np.where(mask, 255, 0).astype(np.uint8))
        rows.append({"name": name, "background": background_path.name,
                     "cutouts": [p.name for p in chosen], "subject": chosen[-1].name,
                     "subject_fraction": round(float(mask.mean()), 4)})
    manifest = {"seed": seed, "canvas": canvas, "count": count, "pages": rows}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cutouts", type=Path, required=True)
    ap.add_argument("--backgrounds", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--canvas", type=int, default=1024)
    args = ap.parse_args(argv)
    rows = make_testset(args.cutouts, args.backgrounds, args.out, args.count, args.seed, args.canvas)
    print(f"{len(rows)} pages in {args.out}")


if __name__ == "__main__":
    main()
