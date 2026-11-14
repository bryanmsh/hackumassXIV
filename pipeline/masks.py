"""Mask helpers. A mask is a uint8 array at master size: 255 = subject, 0 = everything else."""
from pathlib import Path

import cv2
import numpy as np

from contracts.hashing import hash_bytes

KEEP_REGION_FRACTION = 0.05  # keep a region at least this fraction of the largest one
FILL_HOLE_FRACTION = 0.001  # fill a hole smaller than this fraction of the page


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """Keep the largest region plus any at least 5% of its size; fill holes under 0.1% of the page."""
    binary = (mask > 0).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if count <= 1:
        return np.zeros(mask.shape[:2], np.uint8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = np.flatnonzero(areas >= KEEP_REGION_FRACTION * areas.max()) + 1
    cleaned = np.isin(labels, keep)

    # A hole is a background region that does not touch the edge of the page.
    count, labels, stats, _ = cv2.connectedComponentsWithStats((~cleaned).astype(np.uint8), connectivity=4)
    height, width = cleaned.shape
    max_hole = FILL_HOLE_FRACTION * height * width
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        touches_edge = x == 0 or y == 0 or x + w == width or y + h == height
        if not touches_edge and area < max_hole:
            cleaned[labels == label] = True
    return cleaned.astype(np.uint8) * 255


def save_mask(mask: np.ndarray, image_path, out_dir) -> tuple[str, str]:
    """Save under out_dir/masks/{n}_{hash}.png. Returns (path, hash). Never overwrites a file."""
    ok, encoded = cv2.imencode(".png", mask)
    if not ok:
        raise ValueError("could not encode the mask as PNG")
    data = encoded.tobytes()
    mask_hash = hash_bytes(data)
    page_number = Path(image_path).stem  # masters are named {n}.png
    path = Path(out_dir) / "masks" / f"{page_number}_{mask_hash}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return str(path), mask_hash


def polygon_mask(points, width: int, height: int) -> np.ndarray:
    """Fill the polygon exactly as drawn. Parts outside the page are cut off."""
    mask = np.zeros((height, width), np.uint8)
    polygon = np.array([[round(x), round(y)] for x, y in points], np.int32)
    cv2.fillPoly(mask, [polygon], 255)
    return mask


def mask_box(mask: np.ndarray) -> tuple[float, float, float, float] | None:
    """(x0, y0, x1, y1) around the subject, or None when the mask is empty."""
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    return (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))


def iou(a: np.ndarray, b: np.ndarray) -> float:
    """Overlap of two masks: shared area over combined area. 0.0 when both are empty."""
    a, b = a > 0, b > 0
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(a, b).sum() / union)
