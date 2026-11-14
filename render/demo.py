"""Render every sample page at all four levels for the demo profiles, with timings.

Run from the repo root:  python -m render.demo [--pages DIR] [--out DIR]

DIR holds Contract 3 style files: {n}.png, {n}_view.png, and a mask named
{n}_mask.png or masks/{n}_*.png. Page text is read from pages.json when present.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import overlay, render
from .core import load_mask, load_rgb

HERE = Path(__file__).resolve().parent

PROFILES = {
    "maya": {"level": 1, "settings": {"colors": ["#E53935"], "background": "#000000",
                                      "position": "center", "text_mode": "off"}},
    "leo": {"level": 2, "settings": {"colors": ["#FDD835", "#1E88E5"], "background": "#000000",
                                     "position": "left", "text_mode": "below"}},
}
LEVEL_NAMES = {1: "tinted", 2: "cutout", 3: "faded", 4: "outlined"}


def find_pages(folder: Path):
    for master in sorted(folder.glob("*.png")):
        n = master.stem
        if not n.isdigit():
            continue
        view = folder / f"{n}_view.png"
        mask = folder / f"{n}_mask.png"
        if not mask.exists():
            found = sorted((folder.parent / "masks").glob(f"{n}_*.png")) or sorted(folder.glob(f"masks/{n}_*.png"))
            mask = found[-1] if found else None
        if view.exists() and mask is not None:
            yield n, master, view, mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=Path, default=HERE / "samples")
    ap.add_argument("--out", type=Path, default=HERE / "out")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    meta_file = args.pages / "pages.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

    times = []
    for n, master, view, mask in find_pages(args.pages):
        load_rgb(master), load_rgb(view), load_mask(mask)
        text = meta.get(n, {}).get("text", "")
        (args.out / f"{n}_overlay.webp").write_bytes(overlay(view, mask))
        for who, prof in PROFILES.items():
            for level in (1, 2, 3, 4):
                t0 = time.perf_counter()
                data = render(master, view, mask, prof["settings"], level, text)
                times.append((time.perf_counter() - t0) * 1000)
                (args.out / f"{n}_{who}_{level}_{LEVEL_NAMES[level]}.webp").write_bytes(data)
    if not times:
        print("no pages found in", args.pages)
        return
    times.sort()
    print(f"{len(times)} renders, median {times[len(times) // 2]:.0f} ms, "
          f"worst {times[-1]:.0f} ms (warm decode cache)")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
