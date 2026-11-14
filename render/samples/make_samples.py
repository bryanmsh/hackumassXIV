"""Build B1's stand-in inputs: two cluttered picture-book pages and their masks.

Run from the repo root:  python -m render.samples.make_samples

Writes, following the Contract 3 naming:
  {n}.png         master page, RGB
  {n}_view.png    working copy, longer side 1,600 px
  {n}_mask.png    8-bit mask, 255 = subject
  bad_scattered_mask.png, bad_huge_mask.png   deliberately bad masks for page 1
  pages.json      page text and subject label
These are replaced by Owner A's real StoryWeaver pages and masks in task B7.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent
AA = cv2.LINE_AA


def bgr(hex_color: str):
    s = hex_color.lstrip("#")
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return (b, g, r)


def gradient(h, w, top, bottom):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a, b = np.array(bgr(top), np.float32), np.array(bgr(bottom), np.float32)
    return np.repeat((a * (1 - t) + b * t), w, axis=1).astype(np.uint8)


def clutter_tree(img, rng, x, base_y, height, trunk_w):
    cv2.rectangle(img, (x - trunk_w // 2, base_y - height), (x + trunk_w // 2, base_y), bgr("#6D4C41"), -1)
    for _ in range(14):
        yy = int(rng.integers(base_y - height, base_y))
        cv2.line(img, (x - trunk_w // 2 + 6, yy), (x + trunk_w // 2 - 6, yy + int(rng.integers(-15, 15))),
                 bgr("#4E342E"), 4, AA)
    for _ in range(140):
        cx = int(x + rng.normal(0, height * 0.28))
        cy = int(base_y - height + rng.normal(0, height * 0.18))
        r = int(rng.integers(30, 70))
        shade = ["#2E7D32", "#388E3C", "#43A047", "#1B5E20", "#66BB6A"][int(rng.integers(0, 5))]
        cv2.circle(img, (cx, cy), r, bgr(shade), -1, AA)


def grass_and_flowers(img, rng, y0):
    h, w = img.shape[:2]
    for _ in range(1400):
        x = int(rng.integers(0, w))
        y = int(rng.integers(y0, h))
        cv2.line(img, (x, y), (x + int(rng.integers(-18, 18)), y - int(rng.integers(20, 60))),
                 bgr(["#558B2F", "#7CB342", "#33691E"][int(rng.integers(0, 3))]), 3, AA)
    for _ in range(90):
        x, y = int(rng.integers(0, w)), int(rng.integers(y0 + 20, h))
        col = bgr(["#F06292", "#FFF176", "#BA68C8", "#FFFFFF"][int(rng.integers(0, 4))])
        for k in range(5):
            ang = k * 2 * np.pi / 5
            cv2.circle(img, (int(x + 14 * np.cos(ang)), int(y + 14 * np.sin(ang))), 10, col, -1, AA)
        cv2.circle(img, (x, y), 8, bgr("#FFB300"), -1, AA)


def clouds(img, rng, n, y_max):
    w = img.shape[1]
    for _ in range(n):
        cx, cy = int(rng.integers(100, w - 100)), int(rng.integers(80, y_max))
        for _ in range(6):
            cv2.ellipse(img, (cx + int(rng.integers(-120, 120)), cy + int(rng.integers(-30, 30))),
                        (int(rng.integers(70, 130)), int(rng.integers(40, 70))), 0, 0, 360,
                        bgr("#FAFAFA"), -1, AA)


def draw_both(img, mask, fn, color, *args, **kwargs):
    """Draw a shape on the page (anti-aliased) and on the mask (hard edges)."""
    fn(img, *args, color=bgr(color), lineType=AA, **kwargs)
    fn(mask, *args, color=255, lineType=cv2.LINE_8, **kwargs)


def page_bird():
    rng = np.random.default_rng(7)
    h, w = 1800, 2400
    img = gradient(h, w, "#81D4FA", "#E1F5FE")
    clouds(img, rng, 6, 500)
    cv2.circle(img, (2150, 230), 130, bgr("#FFEB3B"), -1, AA)
    cv2.ellipse(img, (600, 1500), (1100, 380), 0, 180, 360, bgr("#9CCC65"), -1, AA)
    cv2.ellipse(img, (1900, 1550), (1000, 420), 0, 180, 360, bgr("#8BC34A"), -1, AA)
    cv2.rectangle(img, (0, 1450), (w, h), bgr("#7CB342"), -1)
    clutter_tree(img, rng, 380, 1500, 900, 120)
    clutter_tree(img, rng, 2050, 1480, 820, 110)
    grass_and_flowers(img, rng, 1450)
    # branch the bird sits on (page content, not subject)
    cv2.line(img, (700, 1060), (1750, 1000), bgr("#5D4037"), 34, AA)
    cv2.line(img, (1500, 1012), (1650, 920), bgr("#5D4037"), 18, AA)

    mask = np.zeros((h, w), np.uint8)
    draw_both(img, mask, cv2.ellipse, "#C62828", (1200, 860), (230, 150), -10, 0, 360, thickness=-1)
    draw_both(img, mask, cv2.circle, "#D32F2F", (1410, 700), 105, thickness=-1)
    tail = np.array([[1000, 860], [760, 760], [720, 860], [780, 960], [1000, 930]], np.int32)
    draw_both(img, mask, cv2.fillPoly, "#B71C1C", [tail])
    beak = np.array([[1500, 670], [1620, 715], [1500, 750]], np.int32)
    draw_both(img, mask, cv2.fillPoly, "#FFA000", [beak])
    for x in (1150, 1260):
        draw_both(img, mask, cv2.line, "#FF8F00", (x, 990), (x + 10, 1040), thickness=14)
    cv2.ellipse(img, (1170, 860), (150, 85), -20, 0, 360, bgr("#8E0000"), -1, AA)
    cv2.ellipse(img, (1200, 930), (150, 50), -10, 0, 180, bgr("#EF9A9A"), -1, AA)
    cv2.circle(img, (1440, 680), 22, bgr("#FFFFFF"), -1, AA)
    cv2.circle(img, (1446, 682), 12, bgr("#000000"), -1, AA)
    return img, mask, "A little red bird sat on the branch and sang."


def page_rabbit():
    rng = np.random.default_rng(11)
    h, w = 2400, 1800
    img = gradient(h, w, "#B3E5FC", "#FFF9C4")
    clouds(img, rng, 4, 500)
    cv2.rectangle(img, (0, 1700), (w, h), bgr("#8BC34A"), -1)
    clutter_tree(img, rng, 1250, 1800, 1300, 220)
    clutter_tree(img, rng, 250, 1750, 900, 90)
    grass_and_flowers(img, rng, 1700)
    for _ in range(40):
        x, y = int(rng.integers(0, w)), int(rng.integers(1750, h))
        cv2.ellipse(img, (x, y), (int(rng.integers(20, 45)), int(rng.integers(12, 25))), 0, 0, 360,
                    bgr("#9E9E9E"), -1, AA)

    mask = np.zeros((h, w), np.uint8)
    draw_both(img, mask, cv2.ellipse, "#8D6E63", (760, 1900), (250, 190), 0, 0, 360, thickness=-1)
    draw_both(img, mask, cv2.circle, "#A1887F", (560, 1700), 130, thickness=-1)
    draw_both(img, mask, cv2.ellipse, "#8D6E63", (500, 1440), (45, 170), -12, 0, 360, thickness=-1)
    draw_both(img, mask, cv2.ellipse, "#8D6E63", (610, 1430), (45, 170), 10, 0, 360, thickness=-1)
    draw_both(img, mask, cv2.circle, "#EFEBE9", (1010, 1860), 60, thickness=-1)
    draw_both(img, mask, cv2.ellipse, "#795548", (700, 2080), (110, 45), 0, 0, 360, thickness=-1)
    draw_both(img, mask, cv2.ellipse, "#795548", (900, 2070), (110, 45), 0, 0, 360, thickness=-1)
    cv2.ellipse(img, (500, 1450), (20, 120), -12, 0, 360, bgr("#F8BBD0"), -1, AA)
    cv2.ellipse(img, (610, 1440), (20, 120), 10, 0, 360, bgr("#F8BBD0"), -1, AA)
    cv2.circle(img, (520, 1680), 20, bgr("#000000"), -1, AA)
    cv2.circle(img, (450, 1730), 14, bgr("#F48FB1"), -1, AA)
    cv2.ellipse(img, (780, 1930), (150, 100), 0, 0, 360, bgr("#BCAAA4"), -1, AA)
    return img, mask, "The rabbit was hiding under the big tree."


def bad_masks(shape):
    h, w = shape
    scattered = np.zeros((h, w), np.uint8)
    for cx, cy in [(400, 400), (1200, 900), (2000, 400), (600, 1400), (1800, 1400)]:
        cv2.circle(scattered, (cx, cy), 160, 255, -1)
    huge = np.zeros((h, w), np.uint8)
    cv2.rectangle(huge, (0, 0), (int(w * 0.9), int(h * 0.9)), 255, -1)
    return scattered, huge


def write(path: Path, img):
    ok, buf = cv2.imencode(".png", img)
    assert ok
    buf.tofile(str(path))


def view_of(img):
    h, w = img.shape[:2]
    s = 1600 / max(h, w)
    return cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)


def main():
    meta = {}
    for n, (fn, label, synonyms) in enumerate(
            [(page_bird, "bird", ["red bird", "robin", "animal"]),
             (page_rabbit, "rabbit", ["bunny", "hare", "animal"])], start=1):
        img, mask, text = fn()
        write(OUT / f"{n}.png", img)
        write(OUT / f"{n}_view.png", view_of(img))
        write(OUT / f"{n}_mask.png", mask)
        meta[str(n)] = {"text": text, "label": label, "synonyms": synonyms}
    scattered, huge = bad_masks((1800, 2400))
    write(OUT / "bad_scattered_mask.png", scattered)
    write(OUT / "bad_huge_mask.png", huge)
    (OUT / "pages.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("wrote samples to", OUT)


if __name__ == "__main__":
    main()
