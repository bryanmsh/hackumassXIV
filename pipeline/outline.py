"""Manual label and outline: the teacher's drawn shape becomes the mask.

The raw path (tidy=False) calls no model, so it still works when the subject model and the
segmenter are both down. It is the demo safety net.
"""
import cv2
import numpy as np
from PIL import Image

from contracts.types import Candidate
from pipeline import segment as segmenter
from pipeline.masks import clean_mask, iou, mask_box, polygon_mask, save_mask

TIDY_MIN_IOU = 0.3  # below this the segmenter found something else, so the drawn shape wins
TIDY_GROW_FRACTION = 0.15  # growth on each side of the drawing's bounding box


def _tidy(image_path, polygon: np.ndarray, box) -> np.ndarray | None:
    """The segmenter's version of the outline, or None when the drawn shape should be kept."""
    try:
        image = np.array(Image.open(image_path).convert("RGB"))
        moments = cv2.moments(polygon, binaryImage=True)
        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        distance = cv2.distanceTransform(polygon, cv2.DIST_L2, 5)
        # A concave drawing's centroid can lie outside it: use the nearest interior pixel.
        if not polygon[round(cy), round(cx)]:
            ys, xs = np.nonzero(polygon)
            nearest = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
            cx, cy = int(xs[nearest]), int(ys[nearest])
        points = [(cx, cy, 1)]
        peaks = distance.copy()
        for _ in range(4):
            _, depth, _, (x, y) = cv2.minMaxLoc(peaks)
            if depth <= 1:
                break
            if (x, y) != (round(cx), round(cy)):
                points.append((x, y, 1))
            # Suppress this peak's interior neighbourhood to spread the prompts out.
            cv2.circle(peaks, (x, y), max(1, round(depth)), 0, -1)
        found = segmenter.segment(image, box=box, points=points)
        if iou(found, polygon) < TIDY_MIN_IOU:
            return None
        x0, y0, x1, y1 = box
        dx = (x1 - x0) * TIDY_GROW_FRACTION
        dy = (y1 - y0) * TIDY_GROW_FRACTION
        height, width = polygon.shape
        grown = np.zeros_like(polygon)
        grown[max(0, int(np.floor(y0 - dy))):min(height, int(np.ceil(y1 + dy))),
              max(0, int(np.floor(x0 - dx))):min(width, int(np.ceil(x1 + dx)))] = 255
        tidied = clean_mask(cv2.bitwise_and(found, grown))
        return tidied if tidied.any() else None
    except Exception:  # any tidy failure: the outline still works
        return None


def mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate:
    """Fill the polygon (at least 3 points, master pixels) and use it exactly as drawn.

    tidy=True (P1) lets the segmenter tighten the shape: its mask is used when it overlaps
    the polygon with an IoU of 0.3 or more, clipped to its box grown by 15%.
    Otherwise, and on any segmenter error, the raw polygon is kept.
    Raises ValueError for fewer than 3 points or an outline entirely off the page.
    """
    points = [(float(x), float(y)) for x, y in points]
    if len(points) < 3:
        raise ValueError("an outline needs at least 3 points")
    with Image.open(image_path) as image:  # reads the size without decoding the pixels
        width, height = image.size
    mask = polygon_mask(points, width, height)
    if not mask.any():
        raise ValueError("the outline is outside the page")

    xs, ys = [p[0] for p in points], [p[1] for p in points]
    box = (max(0.0, min(xs)), max(0.0, min(ys)), min(float(width), max(xs)), min(float(height), max(ys)))
    if tidy:
        tidied = _tidy(image_path, mask, box)
        if tidied is not None:
            mask, box = tidied, mask_box(tidied)
    mask_path, mask_hash = save_mask(mask, image_path, out_dir)
    return Candidate(label=label, synonyms=[], box=box, confidence=1.0,
                     mask_path=mask_path, mask_hash=mask_hash, source="manual")
