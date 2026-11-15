"""Display for Miraai (Owner B): Contract 2 `render`, `overlay` and `RENDER_VERSION`."""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .core import RENDER_VERSION, compose, encode, load_mask, load_rgb, ring_around

OVERLAY_COLOR = (0, 229, 255)
OVERLAY_TINT = 0.45
OVERLAY_DIM = 0.55
OVERLAY_RING_PX = 3
OVERLAY_OTHER_TINT = 0.30

# Must match web/src/index.css --color-subject-1..6, in candidate order. No green.
SUBJECT_PALETTE = (
    (29, 78, 216),    # #1D4ED8 blue
    (194, 65, 12),    # #C2410C orange
    (109, 40, 217),   # #6D28D9 purple
    (190, 24, 93),    # #BE185D pink
    (15, 118, 110),   # #0F766E teal
    (234, 179, 8),    # #EAB308 yellow
)

__all__ = ["RENDER_VERSION", "render", "overlay", "overlay_palette"]


def render(image_path, view_path, mask_path, settings, level, text: Optional[str] = None,
           fmt: str = "webp", text_boxes=None) -> bytes:
    """Adapted page for one profile and level, as WebP (or PNG for tests).

    text_boxes: where the page's words sit, as 0 to 1 fractions of the page (additive; may be None).
    """
    return encode(compose(image_path, view_path, mask_path, settings, level, text, text_boxes).rgb, fmt)


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


def overlay_palette(view_path, mask_paths, selected: Optional[int], fmt: str = "webp") -> bytes:
    """Every candidate tinted in its own palette colour over the dimmed working copy.

    Candidate i uses SUBJECT_PALETTE[i % 6]. Larger masks are painted first and the
    selected one last, so a combined candidate does not hide its parts; only the
    selected one is tinted at full strength and gets a ring. Unreadable masks are skipped.
    """
    view = load_rgb(view_path)
    vh, vw = view.shape[:2]
    page = view.astype(np.float32)
    out = page * OVERLAY_DIM

    masks = []
    for index, path in enumerate(mask_paths or []):
        try:
            mask = cv2.resize(load_mask(path), (vw, vh), interpolation=cv2.INTER_AREA)
        except Exception:  # noqa: BLE001 - a bad mask must not break the review screen
            continue
        masks.append((index, mask))
    masks.sort(key=lambda item: (item[0] == selected, -int(np.count_nonzero(item[1] >= 128))))

    for index, mask in masks:
        tint = OVERLAY_TINT if index == selected else OVERLAY_OTHER_TINT
        color = np.asarray(SUBJECT_PALETTE[index % len(SUBJECT_PALETTE)], np.float32)
        a = (mask.astype(np.float32) / 255.0)[..., None]
        out = (page * (1 - tint) + color * tint) * a + out * (1 - a)

    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    for index, mask in masks:
        if index == selected:
            out[ring_around(mask >= 128, OVERLAY_RING_PX)] = SUBJECT_PALETTE[index % len(SUBJECT_PALETTE)]
    return encode(out, fmt)
