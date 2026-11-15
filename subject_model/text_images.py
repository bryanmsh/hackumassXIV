"""Lines of printed words: the namer's `text` class, and the words drawn on the finder's training photos.

python -m subject_model.text_images OUT_DIR [--count 550] [--seed 0] [--fonts DIR ...]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIRS = ("/System/Library/Fonts/Supplemental", "/usr/share/fonts/truetype/dejavu",
             "/usr/share/fonts/truetype/liberation")
FONT_PREFIXES = ("Arial", "Georgia", "Verdana", "Trebuchet", "Times New Roman", "Comic Sans", "Courier New",
                 "Tahoma", "DejaVuSans", "DejaVuSerif", "LiberationSans", "LiberationSerif")
WORDS = ("the", "little", "rabbit", "went", "home", "after", "school", "she", "looked", "under", "big", "tree",
         "and", "found", "a", "small", "red", "ball", "they", "played", "all", "day", "long", "with", "their",
         "friends", "mother", "said", "come", "back", "soon", "where", "is", "my", "hat", "he", "asked", "one",
         "morning", "sun", "was", "bright", "warm", "happy", "children", "ran", "to", "river", "saw", "boat",
         "night", "moon", "star", "sleep", "dream", "garden", "flowers", "bird", "sang", "song", "together")
LINE_SPACING = 1.3   # distance between lines, as a multiple of the letter size
MIN_LETTERS = 6      # px: letters are never shrunk below this to make a block fit
PAPER_MIN = 225


def find_fonts(dirs=FONT_DIRS) -> list[Path]:
    """The .ttf files in `dirs` whose names start with a font known to draw Latin letters, sorted."""
    found = []
    for folder in map(Path, dirs):
        if folder.is_dir():
            found += [p for p in folder.iterdir() if p.suffix.lower() == ".ttf" and p.name.startswith(FONT_PREFIXES)]
    return sorted(found)


def _lines(rng, count) -> list[str]:
    return [" ".join(str(w) for w in rng.choice(WORDS, size=int(rng.integers(2, 7)))) for _ in range(count)]


def _font(path, size):
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default(size)


def _fit(lines, font_path, size, max_width, max_height):
    """(font, line step, block width, block height) at the largest size up to `size` where the block fits."""
    while True:
        font = _font(font_path, size)
        step = round(size * LINE_SPACING)
        width, height = int(max(font.getlength(line) for line in lines)) + 1, step * len(lines)
        if (width <= max_width and height <= max_height) or size <= MIN_LETTERS:
            return font, step, width, height
        size = max(MIN_LETTERS, int(size * 0.85))


def _write(canvas, lines, font, step, x, y, ink) -> None:
    draw = ImageDraw.Draw(canvas)
    for i, line in enumerate(lines):
        draw.text((x, y + i * step), line, font=font, fill=ink)


def _pick_font(rng, fonts):
    return fonts[int(rng.integers(len(fonts)))] if fonts else None


def draw_lines(image: np.ndarray, rng, fonts) -> np.ndarray:
    """A copy of the RGB uint8 image with 1 to 4 lines of 2 to 6 words, dark on light and light on dark."""
    height, width = image.shape[:2]
    lines = _lines(rng, int(rng.integers(1, 5)))
    size = max(MIN_LETTERS, round(rng.uniform(0.03, 0.08) * min(height, width)))
    font, step, block_w, block_h = _fit(lines, _pick_font(rng, fonts), size, width, height)
    x = int(rng.integers(0, max(0, width - block_w) + 1))
    y = int(rng.integers(0, max(0, height - block_h) + 1))
    under = image[y:y + block_h, x:x + block_w]
    if under.mean() > 127:
        ink = tuple(int(v) for v in rng.integers(0, 41, 3))
    else:
        ink = tuple(int(v) for v in rng.integers(215, 256, 3))
    canvas = Image.fromarray(image.copy())
    _write(canvas, lines, font, step, x, y, ink)
    return np.asarray(canvas).copy()


def text_page(rng, fonts, width=256, height=192) -> np.ndarray:
    """A plain light page, uint8 (height, width, 3), with 2 to 5 lines of dark words on it."""
    paper = tuple(int(v) for v in rng.integers(PAPER_MIN, 256, 3))
    edge = 8
    lines = _lines(rng, int(rng.integers(2, 6)))
    size = max(MIN_LETTERS, round(rng.uniform(0.08, 0.16) * height))
    font, step, block_w, block_h = _fit(lines, _pick_font(rng, fonts), size, width - 2 * edge, height - 2 * edge)
    x = int(rng.integers(edge, max(edge, width - edge - block_w) + 1))
    y = int(rng.integers(edge, max(edge, height - edge - block_h) + 1))
    ink = tuple(int(v) for v in rng.integers(0, 41, 3))
    canvas = Image.new("RGB", (width, height), paper)
    _write(canvas, lines, font, step, x, y, ink)
    return np.asarray(canvas).copy()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Write pictures of printed words.")
    parser.add_argument("out_dir")
    parser.add_argument("--count", type=int, default=550)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--fonts", nargs="+", default=list(FONT_DIRS))
    args = parser.parse_args(argv)
    fonts = find_fonts(args.fonts)
    print(f"{len(fonts)} fonts found", flush=True)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    for i in range(args.count):
        Image.fromarray(text_page(rng, fonts)).save(out / f"{i:04d}.png")
    print(f"wrote {args.count} pictures to {out}", flush=True)


if __name__ == "__main__":
    main()
