"""Pure compositing for the four display levels.

Images and settings in, pixels out. No network, no database, no stored
state beyond an in-process cache of decoded files keyed by path, mtime and
size, so a changed file is always re-read.
"""
from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ._types import LocalSettings, coerce_settings
from .color import RGB, contrast_ratio, hex_to_rgb, text_color_for

RENDER_VERSION = "b3"

CANVAS_LONG = 1600
TEXT_BAND = 0.20
TEXT_SIZE = 0.075
TEXT_MIN_PX = 12
TEXT_CONTRAST_MIN = 4.5  # the main colour is used for text only when it reaches this
PAGE_NUMBER = re.compile(r"^\s*\d+\s*(/\s*\d+)?\s*$")
# Levels 1 and 2: the subject is scaled to fit a box this fraction of the picture's width AND
# height, so a wide subject fills the width and a tall one the height (not the shorter side only).
SIZE_FRACTION = {"small": 0.50, "medium": 0.70, "large": 0.90}
POSITIONS = {
    "center": (0.5, 0.5),
    "left": (0.3, 0.5),
    "right": (0.7, 0.5),
    "upper": (0.5, 0.3),
    "lower": (0.5, 0.7),
}
EDGE_MARGIN = 0.04
# Ring widths on the 1,600 px canvas. Outlined (level 4) always rings the subject: "thick"
# unless the profile asks for thin. The extra ring at Cut-out and Faded page follows the profile.
OUTLINE_PX = {"off": 0, "thin": 8, "thick": 20}
# A subject in several pieces far apart (two animals, a child and an ant) would stay tiny if its
# whole box were scaled, so at levels 1 and 2 the pieces are gathered: cut from the original as
# they are, kept in left-to-right order and at one common scale, laid out side by side.
GATHER_EMPTY_RATIO = 2.5  # gather when the union box is this many times the pieces' own boxes
GATHER_PART_MIN = 0.02  # a piece under this share of the largest piece is mask noise, not drawn
GATHER_GAP = 0.08  # gap between gathered pieces, as a share of the widest piece
GATHER_ROW_MAX = 4  # more pieces than this go on two rows
SOFTEN_SIGMA = 1.0  # about a 2 px edge blur
FADE_SATURATION = 0.20
FADE_PAGE_WEIGHT = 0.30
TINT_FLOOR = 0.35

FONT_DIR = Path(__file__).resolve().parent / "fonts"
_SATURATION_LUT = np.rint(np.arange(256) * FADE_SATURATION).astype(np.uint8)


@dataclass
class Rendered:
    rgb: np.ndarray  # H x W x 3, uint8
    subject: np.ndarray  # H x W bool, the subject as placed on the canvas
    outline: np.ndarray  # H x W bool, ring drawn around the subject (may be empty)
    outline_px: int
    picture_height: int  # rows above the text band
    background: RGB
    text_color: Optional[RGB]
    level: int
    scale: float  # canvas pixels per master pixel for the subject
    subject_box: Tuple[int, int, int, int]  # x, y, w, h of the mask in master pixels
    master_size: Tuple[int, int]  # w, h
    page_rect: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h of the page at levels 3 and 4


# --- file loading -----------------------------------------------------------


def _key(path) -> Tuple[str, int, int]:
    p = os.fspath(path)
    st = os.stat(p)
    return (p, st.st_mtime_ns, st.st_size)


@lru_cache(maxsize=48)
def _read_rgb(key: Tuple[str, int, int]) -> np.ndarray:
    data = np.fromfile(key[0], dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cannot read image: {key[0]}")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    rgb.setflags(write=False)
    return rgb


@lru_cache(maxsize=48)
def _read_mask(key: Tuple[str, int, int]) -> np.ndarray:
    data = np.fromfile(key[0], dtype=np.uint8)
    m = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if m is None:
        raise ValueError(f"cannot read mask: {key[0]}")
    m = np.where(m > 127, 255, 0).astype(np.uint8)
    m.setflags(write=False)
    return m


def load_rgb(path) -> np.ndarray:
    return _read_rgb(_key(path))


def load_mask(path) -> np.ndarray:
    return _read_mask(_key(path))


@lru_cache(maxsize=8)
def _font(size: int) -> ImageFont.ImageFont:
    for name in ("AtkinsonHyperlegible-Bold.ttf", "AtkinsonHyperlegible-Regular.ttf"):
        f = FONT_DIR / name
        if f.exists():
            return ImageFont.truetype(str(f), size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


# --- helpers ----------------------------------------------------------------


def canvas_size(master_w: int, master_h: int) -> Tuple[int, int]:
    if master_w >= master_h:
        return CANVAS_LONG, max(1, round(CANVAS_LONG * master_h / master_w))
    return max(1, round(CANVAS_LONG * master_w / master_h)), CANVAS_LONG


def text_lines(text: Optional[str]) -> List[str]:
    """The page's own lines, in order: blank lines and lines that are only a page number dropped."""
    lines = (" ".join(line.split()) for line in (text or "").splitlines())
    return [line for line in lines if line and not PAGE_NUMBER.match(line)]


def shows_text(settings: LocalSettings, text: Optional[str]) -> bool:
    return settings.text_mode == "below" and bool(text_lines(text))


def band_text_color(s: LocalSettings, background: RGB) -> RGB:
    """The child's main colour when it reaches 4.5:1 on the background, else white or black."""
    main = _main_color(s)
    if contrast_ratio(main, background) >= TEXT_CONTRAST_MIN:
        return main
    return text_color_for(background)


def _disk(radius: int) -> np.ndarray:
    d = 2 * radius + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))


def ring_around(mask: np.ndarray, width: int) -> np.ndarray:
    if width <= 0:
        return np.zeros_like(mask, dtype=bool)
    grown = cv2.dilate(mask.astype(np.uint8), _disk(width)) > 0
    return grown & ~mask


def _soften(hard: np.ndarray) -> np.ndarray:
    """Soften a hard mask inward only, so nothing outside the mask is shown."""
    pad = 4
    padded = cv2.copyMakeBorder(hard.astype(np.float32), pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    a = cv2.GaussianBlur(padded, (0, 0), SOFTEN_SIGMA)[pad:-pad, pad:-pad]
    a = np.minimum(a, hard.astype(np.float32))
    a[a > 0.999] = 1.0
    return a


def _blend(fg: np.ndarray, bg: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """fg over bg; pixels with alpha 1 are copied from fg unchanged."""
    out = bg.copy()
    full = alpha >= 1.0
    out[full] = fg[full]
    part = (alpha > 0) & ~full
    if part.any():
        a = alpha[part][:, None]
        mixed = fg[part].astype(np.float32) * a + bg[part].astype(np.float32) * (1.0 - a)
        out[part] = np.clip(np.rint(mixed), 0, 255).astype(np.uint8)
    return out


def _main_color(s: LocalSettings) -> RGB:
    return hex_to_rgb(s.colors[0])


def _second_color(s: LocalSettings) -> RGB:
    return hex_to_rgb(s.colors[1] if len(s.colors) > 1 else s.colors[0])


def tint(sub: np.ndarray, hard: np.ndarray, color: RGB) -> np.ndarray:
    """Tint keeping shading: color * (0.35 + 0.65 * value), value stretched to the subject's range."""
    gray = cv2.cvtColor(sub, cv2.COLOR_RGB2GRAY).astype(np.float32)
    inside = gray[hard]
    if inside.size:
        lo, hi = np.percentile(inside, [2, 98])
    else:
        lo, hi = 0.0, 255.0
    value = np.clip((gray - lo) / max(hi - lo, 1.0), 0.0, 1.0)
    factor = TINT_FLOOR + (1.0 - TINT_FLOOR) * value
    out = np.asarray(color, dtype=np.float32)[None, None, :] * factor[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def subject_placement(box_w: int, box_h: int, canvas_w: int, picture_h: int,
                      size: str, position: str) -> Tuple[float, int, int, int, int]:
    """Scale and top-left position of the subject at levels 1 and 2.

    The subject fits inside a box SIZE_FRACTION wide and high of the picture area, so it is
    as large as that box allows in whichever direction binds first.
    """
    frac = SIZE_FRACTION[size]
    scale = frac * min(canvas_w / box_w, picture_h / box_h)
    nw, nh = max(1, round(box_w * scale)), max(1, round(box_h * scale))
    fx, fy = POSITIONS[position]
    mx, my = round(EDGE_MARGIN * canvas_w), round(EDGE_MARGIN * picture_h)

    def clamp(start: int, length: int, total: int, margin: int) -> int:
        lo, hi = margin, total - margin - length
        if hi < lo:
            return (total - length) // 2
        return int(min(max(start, lo), hi))

    left = clamp(round(fx * canvas_w - nw / 2), nw, canvas_w, mx)
    top = clamp(round(fy * picture_h - nh / 2), nh, picture_h, my)
    return scale, nw, nh, left, top


def subject_parts(mask: np.ndarray):
    """Connected pieces of the mask worth drawing, left to right: (x, y, w, h, label), and the label map."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats((mask >= 128).astype(np.uint8), connectivity=8)
    if n <= 1:
        return [], labels
    areas = stats[1:, cv2.CC_STAT_AREA]
    floor = GATHER_PART_MIN * float(areas.max())
    parts = [(int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP]), int(stats[i, cv2.CC_STAT_WIDTH]),
              int(stats[i, cv2.CC_STAT_HEIGHT]), i) for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= floor]
    parts.sort(key=lambda p: (p[0], p[1]))
    return parts, labels


def should_gather(parts, union_w: int, union_h: int) -> bool:
    """True when the pieces sit far apart: scaling their union box would leave each one small."""
    if len(parts) < 2:
        return False
    own = sum(w * h for _, _, w, h, _ in parts)
    return union_w * union_h > GATHER_EMPTY_RATIO * own


def gather_layout(parts, canvas_w: int, picture_h: int, size: str, position: str):
    """One common scale and a canvas spot for each piece, side by side (two rows past GATHER_ROW_MAX).

    Returns (scale, [(label, x, y, w, h, left, top, nw, nh), ...]) with master-pixel boxes and
    canvas placements. Relative sizes between pieces are kept: one scale for all.
    """
    rows = [parts] if len(parts) <= GATHER_ROW_MAX else [parts[: (len(parts) + 1) // 2], parts[(len(parts) + 1) // 2:]]
    gap = GATHER_GAP * max(w for _, _, w, _, _ in parts)
    row_w = [sum(w for _, _, w, _, _ in row) + gap * (len(row) - 1) for row in rows]
    row_h = [max(h for _, _, _, h, _ in row) for row in rows]
    block_w, block_h = max(row_w), sum(row_h) + gap * (len(rows) - 1)
    scale = SIZE_FRACTION[size] * min(canvas_w / block_w, picture_h / block_h)
    bw, bh = max(1, round(block_w * scale)), max(1, round(block_h * scale))
    fx, fy = POSITIONS[position]
    mx, my = round(EDGE_MARGIN * canvas_w), round(EDGE_MARGIN * picture_h)

    def clamp(start: int, length: int, total: int, margin: int) -> int:
        lo, hi = margin, total - margin - length
        return (total - length) // 2 if hi < lo else int(min(max(start, lo), hi))

    block_left = clamp(round(fx * canvas_w - bw / 2), bw, canvas_w, mx)
    block_top = clamp(round(fy * picture_h - bh / 2), bh, picture_h, my)
    spots = []
    y = block_top
    for row, rw, rh in zip(rows, row_w, row_h):
        x = block_left + (bw - round(rw * scale)) / 2  # each row centred in the block
        for px, py, w, h, label in row:
            nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
            top = y + (round(rh * scale) - nh) // 2  # centred in its row
            spots.append((label, px, py, w, h, int(round(x)), int(top), nw, nh))
            x += (w + gap) * scale
        y += round((rh + gap) * scale)
    return scale, spots


def resample(crop: np.ndarray, nw: int, nh: int, scale: float) -> np.ndarray:
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(crop, (nw, nh), interpolation=interp)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> List[str]:
    """Each source line stays its own line; a line wraps only when wider than the band."""
    lines: List[str] = []
    for para in text_lines(text):
        words, cur = para.split(), ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if draw.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def layout_text(draw: ImageDraw.ImageDraw, text: str, width: int, height: int, band_h: int):
    """(font size, font, lines, line height): the largest size up to TEXT_SIZE that fits the band."""
    size = max(TEXT_MIN_PX, round(TEXT_SIZE * height))
    max_w = round(0.92 * width)
    while True:
        font = _font(size)
        lines = _wrap(draw, text, font, max_w)
        line_h = round(size * 1.2)
        fits = len(lines) * line_h <= 0.9 * band_h and all(
            draw.textlength(l, font=font) <= max_w for l in lines)
        if fits or size <= TEXT_MIN_PX:
            return size, font, lines, line_h
        size = max(TEXT_MIN_PX, round(size * 0.9))


def draw_text_band(rgb: np.ndarray, top: int, text: str, color: RGB) -> np.ndarray:
    h, w = rgb.shape[:2]
    band_h = h - top
    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)
    size, font, lines, line_h = layout_text(draw, text, w, h, band_h)
    y = top + (band_h - len(lines) * line_h) / 2
    for line in lines:
        lw = draw.textlength(line, font=font)
        draw.text(((w - lw) / 2, y + (line_h - size) / 2), line, font=font, fill=tuple(color))
        y += line_h
    return np.asarray(img)


# --- composition ------------------------------------------------------------


def compose(image_path, view_path, mask_path, settings, level: int,
            text: Optional[str] = None) -> Rendered:
    s = coerce_settings(settings)
    level = int(level)
    if level not in (1, 2, 3, 4):
        raise ValueError(f"level must be 1 to 4, got {level}")

    mask = load_mask(mask_path)
    mh, mw = mask.shape[:2]
    W, H = canvas_size(mw, mh)
    text_on = shows_text(s, text)
    pic_h = H - round(TEXT_BAND * H) if text_on else H
    bg = hex_to_rgb(s.background)
    canvas = np.empty((H, W, 3), dtype=np.uint8)
    canvas[:] = bg
    subject = np.zeros((H, W), dtype=bool)
    bx, by, bw, bh = cv2.boundingRect(mask)
    outline_px = 0
    outline_color = _main_color(s)
    scale = 0.0
    page_rect = None

    if level in (1, 2):
        if bw > 0 and bh > 0:
            master = load_rgb(image_path)
            if master.shape[:2] != mask.shape[:2]:
                raise ValueError("mask and master page differ in size")

            def draw_piece(mcrop: np.ndarray, px: int, py: int, w: int, h: int,
                           left: int, top: int, nw: int, nh: int, k: float) -> None:
                sub = resample(master[py:py + h, px:px + w], nw, nh, k)
                hard = cv2.resize(mcrop, (nw, nh), interpolation=cv2.INTER_LINEAR) >= 128
                if level == 1:
                    sub = tint(sub, hard, _main_color(s))
                subject[top:top + nh, left:left + nw] |= hard
                roi = canvas[top:top + nh, left:left + nw]
                canvas[top:top + nh, left:left + nw] = _blend(sub, roi, _soften(hard))

            parts, labels = subject_parts(mask)
            if should_gather(parts, bw, bh):
                scale, spots = gather_layout(parts, W, pic_h, s.size, s.position)
                for label, px, py, w, h, left, top, nw, nh in spots:
                    piece = (labels[py:py + h, px:px + w] == label).astype(np.uint8) * 255
                    draw_piece(piece, px, py, w, h, left, top, nw, nh, scale)
            else:
                scale, nw, nh, left, top = subject_placement(bw, bh, W, pic_h, s.size, s.position)
                draw_piece(mask[by:by + bh, bx:bx + bw], bx, by, bw, bh, left, top, nw, nh, scale)
        if level == 2:
            outline_px = OUTLINE_PX[s.outline]
            outline_color = _second_color(s)
    else:
        view = load_rgb(view_path)
        vh, vw = view.shape[:2]
        fit = min(W / vw, pic_h / vh)
        pw, ph = max(1, round(vw * fit)), max(1, round(vh * fit))
        px, py = (W - pw) // 2, (pic_h - ph) // 2
        page_rect = (px, py, pw, ph)
        page = view if (pw, ph) == (vw, vh) else cv2.resize(view, (pw, ph), interpolation=cv2.INTER_AREA)
        soft = cv2.resize(mask, (pw, ph), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        hard = soft >= 0.5
        subject[py:py + ph, px:px + pw] = hard
        scale = pw / mw
        if level == 3:
            hsv = cv2.cvtColor(page, cv2.COLOR_RGB2HSV)
            hsv[..., 1] = cv2.LUT(hsv[..., 1], _SATURATION_LUT)
            faded = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            plain = np.empty_like(faded)
            plain[:] = bg
            faded = cv2.addWeighted(faded, FADE_PAGE_WEIGHT, plain, 1 - FADE_PAGE_WEIGHT, 0)
            alpha = cv2.GaussianBlur(soft, (0, 0), SOFTEN_SIGMA)
            alpha[alpha > 0.999] = 1.0
            canvas[py:py + ph, px:px + pw] = _blend(page, faded, alpha)
            outline_px = OUTLINE_PX[s.outline]
            outline_color = _second_color(s)
        else:
            canvas[py:py + ph, px:px + pw] = page
            outline_px = OUTLINE_PX["thin"] if s.outline == "thin" else OUTLINE_PX["thick"]
            outline_color = _main_color(s)

    outline = ring_around(subject, outline_px) if subject.any() else np.zeros_like(subject)
    if outline.any():
        canvas[outline] = outline_color

    text_color = None
    if text_on:
        text_color = band_text_color(s, bg)
        canvas = draw_text_band(canvas, pic_h, text, text_color)

    return Rendered(
        rgb=canvas, subject=subject, outline=outline, outline_px=outline_px,
        picture_height=pic_h, background=bg, text_color=text_color, level=level,
        scale=scale, subject_box=(bx, by, bw, bh), master_size=(mw, mh), page_rect=page_rect,
    )


def original_layout(view_path, canvas_w: int, canvas_h: int, picture_h: int,
                    background: RGB) -> np.ndarray:
    """The untouched working copy in the level 3 and 4 layout, for comparisons."""
    view = load_rgb(view_path)
    vh, vw = view.shape[:2]
    fit = min(canvas_w / vw, picture_h / vh)
    pw, ph = max(1, round(vw * fit)), max(1, round(vh * fit))
    px, py = (canvas_w - pw) // 2, (picture_h - ph) // 2
    out = np.empty((canvas_h, canvas_w, 3), dtype=np.uint8)
    out[:] = background
    page = view if (pw, ph) == (vw, vh) else cv2.resize(view, (pw, ph), interpolation=cv2.INTER_AREA)
    out[py:py + ph, px:px + pw] = page
    return out


def encode(rgb: np.ndarray, fmt: str = "webp") -> bytes:
    fmt = fmt.lower()
    buf = io.BytesIO()
    img = Image.fromarray(rgb)
    if fmt == "webp":
        img.save(buf, format="WEBP", quality=90, method=0)
    elif fmt == "png":
        img.save(buf, format="PNG", compress_level=1)
    else:
        raise ValueError(f"unsupported format: {fmt}")
    return buf.getvalue()
