"""Click to pick a subject, and click to add a missing part to a cut-out."""
import cv2
import numpy as np

from contracts.types import Candidate
from pipeline import segment as segmenter
from pipeline.masks import clean_mask, mask_box, save_mask
from pipeline.subjects import label_crop

CROP_PADDING = 0.08  # margin around the cut-out in the crop sent for a label, as a share of its longer side
REFINE_REACH = 0.05  # a refine click may grow the old box by this share of the page's longer side


def _load_rgb(image_path) -> np.ndarray:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError("the page image could not be read")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _on_page(x, y, image) -> tuple[float, float]:
    """Pull a click onto the page. A click at the far edge arrives as x == width."""
    height, width = image.shape[:2]
    return min(max(x, 0), width - 1), min(max(y, 0), height - 1)


def _label(image: np.ndarray, box) -> str:
    """Ask our subject model to name what is in the box. Empty when it is not sure, and the teacher types it."""
    try:
        height, width = image.shape[:2]
        x0, y0, x1, y1 = box
        pad = round(CROP_PADDING * max(x1 - x0, y1 - y0))
        crop = image[max(0, int(y0) - pad):min(height, int(y1) + pad),
                     max(0, int(x0) - pad):min(width, int(x1) + pad)]
        ok, png = cv2.imencode(".png", cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        if not ok:
            return ""
        return label_crop(png.tobytes())
    except Exception:
        return ""


def _candidate(mask, label, image_path, out_dir) -> Candidate:
    mask_path, mask_hash = save_mask(mask, image_path, out_dir)
    return Candidate(label=label, synonyms=[], box=mask_box(mask), confidence=1.0,
                     mask_path=mask_path, mask_hash=mask_hash, source="click")


def segment_at_point(image_path, x, y, out_dir) -> Candidate:
    """Cut out whatever the teacher clicked, at (x, y) in master pixels, and try to name it."""
    image = _load_rgb(image_path)
    x, y = _on_page(x, y, image)
    mask = clean_mask(segmenter.segment(image, points=[(x, y)]))
    if not mask.any():
        # Nothing found, for example a click on flat background. Give the teacher a
        # rectangle around the click to look at, not an error.
        height, width = image.shape[:2]
        x0, y0, x1, y1 = (int(value) for value in segmenter.point_box(x, y, width, height))
        mask[y0:y1, x0:x1] = 255
    return _candidate(mask, _label(image, mask_box(mask)), image_path, out_dir)


def refine_mask(image_path, mask_path, x, y, out_dir) -> Candidate:
    """Add a missing part, such as a tail, by clicking it. Writes a new mask file; the old one stays.

    The original prompt is not passed in, so the old mask's own box stands in for it,
    grown just far enough to reach the click. The result is the old mask, untouched,
    plus what was found, so a refine click can only add. The piece under the click is
    always kept, however small. The label is empty: the page keeps its own.
    """
    image = _load_rgb(image_path)
    x, y = _on_page(x, y, image)
    old = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if old is None:
        raise FileNotFoundError("the mask to refine could not be read")
    height, width = image.shape[:2]
    reach = segmenter.point_box(x, y, width, height, fraction=REFINE_REACH)
    old_box = mask_box(old) or reach
    box = (min(old_box[0], reach[0]), min(old_box[1], reach[1]),
           max(old_box[2], reach[2]), max(old_box[3], reach[3]))
    found = segmenter.segment(image, box=box, points=[(x, y)])
    added = clean_mask(found)
    # Cleanup drops small detached pieces, but the one the teacher clicked is the point.
    _, pieces = cv2.connectedComponents((found > 0).astype(np.uint8), connectivity=8)
    clicked = pieces[int(y), int(x)]
    if clicked:
        added[pieces == clicked] = 255
    return _candidate(cv2.bitwise_or(old, added), "", image_path, out_dir)
