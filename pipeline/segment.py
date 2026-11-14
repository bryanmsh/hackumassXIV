"""The one door to the segmenter. Nothing outside this file knows which one is in use.

SEGMENTER picks it: `stub`, `grabcut` (the default), `edgesam` or `sam2`.
The setting is read on every call, so it can be changed without a restart.
"""
import os

import cv2
import numpy as np

POINT_BOX_FRACTION = 0.20  # half-size of the box put around a lone point, as a share of the longer side
GRABCUT_MAX_SIDE = 1024  # GrabCut runs on a copy this size, which keeps a 3,000 px page near a second
GRABCUT_ITERATIONS = 5
POINT_RADIUS_FRACTION = 0.01  # sure-foreground disc around each point


def point_box(x, y, width, height, fraction=POINT_BOX_FRACTION) -> tuple[float, float, float, float]:
    """The box used when only a point is given: a square around it, clipped to the page."""
    half = fraction * max(width, height)
    return (max(0.0, x - half), max(0.0, y - half), min(float(width), x + half), min(float(height), y + half))


def segment(image: np.ndarray, box=None, points=None) -> np.ndarray:
    """Cut one subject out of a page.

    image:  RGB uint8 array of the master page, shape (height, width, 3).
    box:    (x0, y0, x1, y1) in master pixels around the subject, or None.
    points: list of (x, y) master-pixel points known to be on the subject, or None.
    At least one of box and points must be given.

    Returns a uint8 array of shape (height, width): 255 = subject, 0 = everything else.
    The mask is raw; callers run pipeline.masks.clean_mask on it.
    """
    if box is None and not points:
        raise ValueError("segment needs a box or at least one point")
    name = os.environ.get("SEGMENTER") or "grabcut"
    if name not in _SEGMENTERS:
        raise ValueError(f"SEGMENTER must be one of {sorted(_SEGMENTERS)}, got {name!r}")
    return _SEGMENTERS[name](image, box, list(points or []))


def _box_or_point_box(image, box, points):
    if box is not None:
        return box
    height, width = image.shape[:2]
    return point_box(points[0][0], points[0][1], width, height)


def _stub(image, box, points) -> np.ndarray:
    """Fills the box as a rectangle. No model."""
    height, width = image.shape[:2]
    x0, y0, x1, y1 = _box_or_point_box(image, box, points)
    x0, x1 = sorted((int(np.clip(round(x0), 0, width)), int(np.clip(round(x1), 0, width))))
    y0, y1 = sorted((int(np.clip(round(y0), 0, height)), int(np.clip(round(y1), 0, height))))
    mask = np.zeros((height, width), np.uint8)
    mask[y0:y1, x0:x1] = 255
    return mask


def _grabcut(image, box, points) -> np.ndarray:
    """OpenCV GrabCut seeded by the box. Points are marked as sure foreground."""
    height, width = image.shape[:2]
    empty = np.zeros((height, width), np.uint8)
    scale = min(1.0, GRABCUT_MAX_SIDE / max(height, width))
    small = image if scale == 1.0 else cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small_h, small_w = small.shape[:2]

    x0, y0, x1, y1 = _box_or_point_box(image, box, points)
    x0, x1 = sorted((int(np.clip(round(x0 * scale), 0, small_w)), int(np.clip(round(x1 * scale), 0, small_w))))
    y0, y1 = sorted((int(np.clip(round(y0 * scale), 0, small_h)), int(np.clip(round(y1 * scale), 0, small_h))))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return empty

    labels = np.full((small_h, small_w), cv2.GC_BGD, np.uint8)
    background_model, foreground_model = np.zeros((1, 65)), np.zeros((1, 65))
    try:
        if points:
            labels[y0:y1, x0:x1] = cv2.GC_PR_FGD
            radius = max(2, round(POINT_RADIUS_FRACTION * max(small_h, small_w)))
            for x, y in points:
                cv2.circle(labels, (round(x * scale), round(y * scale)), radius, int(cv2.GC_FGD), -1)
            cv2.grabCut(small, labels, None, background_model, foreground_model,
                        GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_MASK)
        else:
            cv2.grabCut(small, labels, (x0, y0, x1 - x0, y1 - y0), background_model, foreground_model,
                        GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return empty  # GrabCut refuses prompts with no background or no foreground to learn from

    subject = ((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD)).astype(np.uint8) * 255
    if scale == 1.0:
        return subject
    return cv2.resize(subject, (width, height), interpolation=cv2.INTER_NEAREST)


def _edgesam(image, box, points) -> np.ndarray:
    """EdgeSAM on CPU. Not built yet: PyTorch is installed by Bryan, not by this code.

    Input, exactly as segment() receives it:
      image:  RGB uint8 numpy array of the master page, shape (height, width, 3), up to 3,000 px.
      box:    (x0, y0, x1, y1) floats in master pixels, or None. Pass as the box prompt.
      points: list of (x, y) floats in master pixels, possibly empty. Pass each as a
              positive point prompt (label 1). When box is None there is always one point.
    Output:
      uint8 numpy array of shape (height, width), the same size as `image`:
      255 where the subject is, 0 elsewhere. No other values. Do not clean it;
      callers run clean_mask.
    Rules:
      Load the model once and keep it in a module-level variable; never per call.
      Import torch inside this function so the rest of the pipeline runs without it.
      Raise on failure; process_page turns any exception into a Failed page.
    """
    raise NotImplementedError("Bryan: PyTorch segmenter goes here")


def _sam2(image, box, points) -> np.ndarray:
    """SAM 2 small. Not built yet. Same input, output and rules as _edgesam above."""
    raise NotImplementedError("Bryan: PyTorch segmenter goes here")


_SEGMENTERS = {"stub": _stub, "grabcut": _grabcut, "edgesam": _edgesam, "sam2": _sam2}
