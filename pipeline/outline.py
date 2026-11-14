"""Manual label and outline: the teacher's drawn shape becomes the mask.

The raw path (tidy=False) calls no model, so it still works when Gemini and the
segmenter are both down. It is the demo safety net.
"""
import cv2
import numpy as np
from PIL import Image

from contracts.types import Candidate
from pipeline import segment as segmenter
from pipeline.masks import clean_mask, iou, mask_box, polygon_mask, save_mask

TIDY_MIN_IOU = 0.6  # below this the segmenter found something else, so the drawn shape wins
TIDY_GROW_PX = 12  # the tidied mask may reach this far outside the drawn shape


def _tidy(image_path, polygon: np.ndarray, box) -> np.ndarray | None:
    """The segmenter's version of the outline, or None when the drawn shape should be kept."""
    try:
        image = np.array(Image.open(image_path).convert("RGB"))
        found = segmenter.segment(image, box=box)
    except Exception:  # no model, a broken model, an unreadable page: the outline still works
        return None
    if iou(found, polygon) < TIDY_MIN_IOU:
        return None
    size = 2 * TIDY_GROW_PX + 1
    grown = cv2.dilate(polygon, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
    tidied = clean_mask(cv2.bitwise_and(found, grown))
    return tidied if tidied.any() else None


def mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate:
    """Fill the polygon (at least 3 points, master pixels) and use it exactly as drawn.

    tidy=True (P1) lets the segmenter tighten the shape: its mask is used when it overlaps
    the polygon with an IoU of 0.6 or more, clipped to the polygon grown by 12 px.
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
