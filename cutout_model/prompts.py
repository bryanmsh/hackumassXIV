"""Crop geometry and the 4-channel model input, shared by training and prediction.

The model sees a square crop around the box: R, G, B scaled to 0..1, plus one channel that
is 1.0 inside the box. NumPy and OpenCV only.
"""
from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np

INPUT_SIZE = 320
MARGIN = 0.25
MIN_BOX_PX = 2

Window = Tuple[int, int, int, int]


def _clipped_box(box, width, height) -> Optional[Tuple[float, float, float, float]]:
    x0, y0, x1, y1 = (float(v) for v in box)
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    x0, x1 = min(max(x0, 0.0), width), min(max(x1, 0.0), width)
    y0, y1 = min(max(y0, 0.0), height), min(max(y1, 0.0), height)
    if x1 - x0 < MIN_BOX_PX or y1 - y0 < MIN_BOX_PX:
        return None
    return x0, y0, x1, y1


def crop_window(box, width, height, margin=MARGIN) -> Optional[Window]:
    """The box clipped to the page and grown by `margin` of its size on each side, or None
    when less than 2 px of it is on the page."""
    clipped = _clipped_box(box, width, height)
    if clipped is None:
        return None
    x0, y0, x1, y1 = clipped
    grow_x, grow_y = margin * (x1 - x0), margin * (y1 - y0)
    return (max(0, int(round(x0 - grow_x))), max(0, int(round(y0 - grow_y))),
            min(int(width), int(round(x1 + grow_x))), min(int(height), int(round(y1 + grow_y))))


def build_input(image: np.ndarray, box, margin=MARGIN, size=INPUT_SIZE):
    """(input of shape (4, size, size) float32, window) or None for an empty or off-page box."""
    height, width = image.shape[:2]
    window = crop_window(box, width, height, margin)
    if window is None:
        return None
    wx0, wy0, wx1, wy1 = window
    crop = cv2.resize(image[wy0:wy1, wx0:wx1], (size, size), interpolation=cv2.INTER_AREA)
    rgb = crop.astype(np.float32).transpose(2, 0, 1) / 255.0

    bx0, by0, bx1, by1 = _clipped_box(box, width, height)
    marker = np.zeros((wy1 - wy0, wx1 - wx0), np.float32)
    marker[int(round(by0)) - wy0:int(round(by1)) - wy0, int(round(bx0)) - wx0:int(round(bx1)) - wx0] = 1.0
    marker = cv2.resize(marker, (size, size), interpolation=cv2.INTER_NEAREST)
    return np.concatenate([rgb, marker[None]], axis=0).astype(np.float32), window
