"""The one door to the segmenter. Nothing outside this file knows which one is in use.

SEGMENTER picks it: `stub`, `grabcut` (the default), `sam2` or `edgetam`.
`sam2` (SAM 2.1 small) and `edgetam` need torch and live in pipeline/sam.py, the only
file that imports it; `stub` and `grabcut` run without torch installed.
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
    points: list of master-pixel points, each (x, y) or (x, y, label), or None.
            label 1 (the default) = on the subject, 0 = not on the subject.
    At least one of box and a label-1 point must be given.

    Returns a uint8 array of shape (height, width): 255 = subject, 0 = everything else.
    The mask is raw; callers run pipeline.masks.clean_mask on it.
    """
    points = _labelled(points)
    if box is None and not any(label == 1 for _, _, label in points):
        raise ValueError("segment needs a box or at least one point on the subject")
    name = os.environ.get("SEGMENTER") or "grabcut"
    if name not in _SEGMENTERS:
        raise ValueError(f"SEGMENTER must be one of {sorted(_SEGMENTERS)}, got {name!r}")
    return _SEGMENTERS[name](image, box, points)


def _labelled(points) -> list[tuple[float, float, int]]:
    """Every point as (x, y, label); a bare (x, y) is on the subject."""
    out = []
    for point in points or []:
        x, y, *rest = point
        out.append((float(x), float(y), int(rest[0]) if rest else 1))
    return out


def _box_or_point_box(image, box, points):
    if box is not None:
        return box
    height, width = image.shape[:2]
    x, y, _ = next(p for p in points if p[2] == 1)
    return point_box(x, y, width, height)


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
    """OpenCV GrabCut seeded by the box. Label-1 points are sure foreground, label-0 sure background."""
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
            for x, y, label in points:
                seed = cv2.GC_FGD if label == 1 else cv2.GC_BGD
                cv2.circle(labels, (round(x * scale), round(y * scale)), radius, int(seed), -1)
            cv2.grabCut(small, labels, None, background_model, foreground_model,
                        GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_MASK)
        else:
            cv2.grabCut(small, labels, (x0, y0, x1 - x0, y1 - y0), background_model, foreground_model,
                        GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return empty  # GrabCut refuses prompts with no background or no foreground to learn from
    seeded = int((labels == cv2.GC_FGD).sum())
    if points and int((labels == cv2.GC_PR_FGD).sum()) <= seeded:
        return empty  # little more than the seed discs is left: the click was on empty page

    subject = ((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD)).astype(np.uint8) * 255
    if scale == 1.0:
        return subject
    return cv2.resize(subject, (width, height), interpolation=cv2.INTER_NEAREST)


def _pytorch(name, image, box, points) -> np.ndarray:
    """Run a model from pipeline/sam.py. When the model's answer to a box looks wrong
    (low score, or the background inside the box), use GrabCut for that prompt instead:
    a rough cut-out of the right object beats a clean cut-out of the wrong one."""
    from pipeline import sam

    try:
        return sam.segment(name, image, box, points)
    except sam.LowConfidence as reason:
        sam.last_timing["fallback"] = str(reason)
        return _grabcut(image, box, points)


def _sam2(image, box, points) -> np.ndarray:
    """SAM 2.1 small (Meta), through transformers. See pipeline/sam.py."""
    return _pytorch("sam2", image, box, points)


def _edgetam(image, box, points) -> np.ndarray:
    """EdgeTAM, a faster SAM 2 variant, through transformers. See pipeline/sam.py."""
    return _pytorch("edgetam", image, box, points)


def _edgesam(image, box, points) -> np.ndarray:
    """EdgeSAM is not built: it has no pip package, only research-repo code. Use edgetam."""
    raise NotImplementedError("EdgeSAM has no installable package; set SEGMENTER=edgetam (its successor) or sam2")


_SEGMENTERS = {"stub": _stub, "grabcut": _grabcut, "sam2": _sam2, "edgetam": _edgetam, "edgesam": _edgesam}
