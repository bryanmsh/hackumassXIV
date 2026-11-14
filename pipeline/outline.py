"""Manual label and outline: the teacher's drawn shape becomes the mask.

The raw path (tidy=False) calls no model, so it still works when Gemini and the
segmenter are both down. It is the demo safety net.
"""
from PIL import Image

from contracts.types import Candidate
from pipeline.masks import mask_box, polygon_mask, save_mask


def mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate:
    """Fill the polygon (at least 3 points, master pixels) and use it exactly as drawn.

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
    # tidy=True (P1) is added in the next task; until then the raw polygon is used.
    mask_path, mask_hash = save_mask(mask, image_path, out_dir)
    return Candidate(label=label, synonyms=[], box=box, confidence=1.0,
                     mask_path=mask_path, mask_hash=mask_hash, source="manual")
