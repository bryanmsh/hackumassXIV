"""Display for Mirai (Owner B): Contract 2 `render`, `overlay` and `RENDER_VERSION`."""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .core import RENDER_VERSION, compose, encode, load_mask, load_rgb, ring_around

OVERLAY_COLOR = (0, 229, 255)
OVERLAY_TINT = 0.45
OVERLAY_DIM = 0.55
OVERLAY_RING_PX = 3

__all__ = ["RENDER_VERSION", "render", "overlay"]


def render(image_path, view_path, mask_path, settings, level, text: Optional[str] = None,
           fmt: str = "webp") -> bytes:
    """Adapted page for one profile and level, as WebP (or PNG for tests)."""
    return encode(compose(image_path, view_path, mask_path, settings, level, text).rgb, fmt)


def overlay(view_path, mask_path, fmt: str = "webp") -> bytes:
    """The cut-out tinted over the original working copy, for subject review."""
    view = load_rgb(view_path)
    vh, vw = view.shape[:2]
    mask = cv2.resize(load_mask(mask_path), (vw, vh), interpolation=cv2.INTER_AREA)
    a = (mask.astype(np.float32) / 255.0)[..., None]
    page = view.astype(np.float32)
    tinted = page * (1 - OVERLAY_TINT) + np.asarray(OVERLAY_COLOR, np.float32) * OVERLAY_TINT
    dimmed = page * OVERLAY_DIM
    out = np.clip(np.rint(tinted * a + dimmed * (1 - a)), 0, 255).astype(np.uint8)
    out[ring_around(mask >= 128, OVERLAY_RING_PX)] = OVERLAY_COLOR
    return encode(out, fmt)
