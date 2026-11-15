"""Model cascade for cut-outs: our own model first, SAM 2 only when ours is not sure.

SEGMENTER=mirai runs our model (cutout_model/, trained from random weights) alone.
SEGMENTER=cascade runs it, scores its own mask, and hands the box to CASCADE_FALLBACK
(sam2 by default, which itself falls back to GrabCut) when the score is under
CASCADE_MIN_CONFIDENCE. Our model only takes boxes, so a click always goes to the fallback.

Our model is imported only when it is used, so the app starts on a branch that does not
have cutout_model/. If it is missing, or its weights are, the cascade uses the fallback and
says why in the log. CUTOUT_MODEL=standin swaps in a rough GrabCut-based stand-in so the
cascade and the calibration can run before the real weights exist.

Every routing decision is logged on the "mirai.cascade" logger and counted in `route_counts`.
"""
import logging
import os
import threading
import time
from collections import Counter

import cv2
import numpy as np

log = logging.getLogger("mirai.cascade")

DEFAULT_MIN_CONFIDENCE = 0.65  # calibrate_cascade on Animal Homes, run B weights, mirror check on:
                               # 67% of boxes kept by our model at 0.919 agreement with SAM 2.1
DEFAULT_FALLBACK = "sam2"
WINDOW_MARGIN = 0.25  # the area scored around the box, as a share of the box: our model's own crop margin

# Mask checks. Each gives a score from 0 to 1; the mask's confidence is the lowest of them.
EDGE_BAND_FRACTION = 0.02  # width of the band around the mask's outline, as a share of the box's longer side
FILL_LOW, FILL_FLOOR = 0.15, 0.03  # a subject fills at least FILL_LOW of its box; under FILL_FLOOR scores 0
FILL_HIGH, FILL_CEILING = 0.92, 0.99  # a mask filling the whole box is the box, not the subject
BORDER_OK, BORDER_BAD = 0.5, 0.8  # share of the box's edge band filled: background inside the box (sam.py's rule)
FLIP_IOU_FLOOR = 0.5  # agreement with the mirrored page below this scores 0

_route_lock = threading.Lock()
route_counts: Counter = Counter()  # (model, reason) -> pages, for run summaries
_local = threading.local()


def last_route() -> dict:
    """The routing decision for the last cut-out made on this thread."""
    return dict(getattr(_local, "route", {}))


def min_confidence() -> float:
    return float(os.environ.get("CASCADE_MIN_CONFIDENCE") or DEFAULT_MIN_CONFIDENCE)


def fallback_name() -> str:
    return os.environ.get("CASCADE_FALLBACK") or DEFAULT_FALLBACK


# ---------- our model ----------

def ours_probability(image: np.ndarray, box) -> np.ndarray:
    """Page-sized float32 map, 0 to 1, of how sure our model is that each pixel is the subject."""
    if (os.environ.get("CUTOUT_MODEL") or "").strip().lower() == "standin":
        return _standin_probability(image, box)
    from cutout_model import predict as ours  # not on every branch; ImportError reaches the caller
    if hasattr(ours, "predict_prob"):
        return np.asarray(ours.predict_prob(image, box), np.float32)
    # Only the 0/255 mask is available: the edge-sureness check then always passes.
    return ours.predict(image, box).astype(np.float32) / 255.0


def _standin_probability(image, box) -> np.ndarray:
    """A stand-in for our model until its weights exist: GrabCut with blurred, unsure edges."""
    from pipeline.segment import _grabcut
    mask = _grabcut(image, box, []).astype(np.float32) / 255.0
    side = max(3, int(EDGE_BAND_FRACTION * max(image.shape[:2])) | 1)
    return cv2.GaussianBlur(mask, (side, side), 0)


# ---------- scoring ----------

def _window(box, width, height):
    """(x0, y0, x1, y1) integer area around the box that the checks look at, or None for an empty box."""
    x0, x1 = sorted((float(box[0]), float(box[2])))
    y0, y1 = sorted((float(box[1]), float(box[3])))
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(width), x1), min(float(height), y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    dx, dy = WINDOW_MARGIN * (x1 - x0), WINDOW_MARGIN * (y1 - y0)
    return (int(max(0, x0 - dx)), int(max(0, y0 - dy)), int(min(width, np.ceil(x1 + dx))),
            int(min(height, np.ceil(y1 + dy))))


def _ramp(value, bad, good) -> float:
    """0 at `bad`, 1 at `good`, straight in between (either order)."""
    if bad == good:
        return float(value >= good)
    return float(np.clip((value - bad) / (good - bad), 0.0, 1.0))


def mask_confidence(prob: np.ndarray, box, flipped_prob: np.ndarray | None = None) -> tuple[float, dict]:
    """(score, parts): how far the mask can be trusted, from checks on the mask alone.

    parts holds each check's score:
      sure    how decided the model is along the mask's outline (1 when only a 0/255 mask is known)
      fill    the mask fills a sensible share of its box: not a speck, not the whole box
      pieces  the share of the mask in its largest piece; a subject is mostly one piece
      border  the mask does not fill the box's edge band, which means background (sam.py's check)
      flip    agreement with the model's answer on the mirrored page (only when given)
    The score is the lowest part, so the reason for a low score is always one named check.
    """
    from pipeline.sam import box_border_cover

    height, width = prob.shape
    window = _window(box, width, height)
    if window is None:
        return 0.0, {"empty_box": 0.0}
    wx0, wy0, wx1, wy1 = window
    p = prob[wy0:wy1, wx0:wx1]
    mask = (p > 0.5).astype(np.uint8)
    area = int(mask.sum())
    if area == 0:
        return 0.0, {"empty_mask": 0.0}

    bx0, bx1 = sorted((box[0], box[2]))
    by0, by1 = sorted((box[1], box[3]))
    box_area = max(1.0, (min(bx1, width) - max(bx0, 0)) * (min(by1, height) - max(by0, 0)))
    parts = {}

    band = max(1, int(round(EDGE_BAND_FRACTION * max(bx1 - bx0, by1 - by0))))
    kernel = np.ones((2 * band + 1, 2 * band + 1), np.uint8)
    ring = cv2.dilate(mask, kernel).astype(bool) & ~cv2.erode(mask, kernel).astype(bool)
    parts["sure"] = float(np.abs(2 * p[ring] - 1).mean()) if ring.any() else 1.0

    fill = area / box_area
    parts["fill"] = min(_ramp(fill, FILL_FLOOR, FILL_LOW), _ramp(fill, FILL_CEILING, FILL_HIGH))

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    parts["pieces"] = float(stats[1:, cv2.CC_STAT_AREA].max() / area) if count > 1 else 1.0

    full = np.zeros((height, width), np.uint8)
    full[wy0:wy1, wx0:wx1] = mask * 255
    parts["border"] = _ramp(box_border_cover(full, box), BORDER_BAD, BORDER_OK)

    if flipped_prob is not None:
        other = flipped_prob[wy0:wy1, wx0:wx1] > 0.5
        union = int((mask.astype(bool) | other).sum())
        agreement = int((mask.astype(bool) & other).sum()) / union if union else 0.0
        parts["flip"] = _ramp(agreement, FLIP_IOU_FLOOR, 1.0)

    parts = {name: round(value, 3) for name, value in parts.items()}
    return min(parts.values()), parts


FLIP_CROP_MARGIN = 0.5  # crop this share of the box around it before mirroring; more than the model's own window (0.25)


def _flipped_probability(image, box) -> np.ndarray:
    """Our model's map for the mirrored page and mirrored box, mirrored back.

    Only the area around the box is mirrored, not the whole page: our model looks at the box
    grown by its own margin (0.25), so a crop grown by FLIP_CROP_MARGIN holds everything it
    sees and the answer is the same. On a 3,000 px page this saves most of the flip check's time.
    """
    height, width = image.shape[:2]
    x0, x1 = sorted((float(box[0]), float(box[2])))
    y0, y1 = sorted((float(box[1]), float(box[3])))
    bx0, by0, bx1, by1 = max(0.0, x0), max(0.0, y0), min(float(width), x1), min(float(height), y1)
    dx, dy = (bx1 - bx0) * FLIP_CROP_MARGIN, (by1 - by0) * FLIP_CROP_MARGIN
    cx0, cy0 = max(0, int(np.floor(bx0 - dx)) - 1), max(0, int(np.floor(by0 - dy)) - 1)
    cx1, cy1 = min(width, int(np.ceil(bx1 + dx)) + 1), min(height, int(np.ceil(by1 + dy)) + 1)
    if cx1 - cx0 < 2 or cy1 - cy0 < 2:  # empty or off-page box: let the model say so on the full page
        mirrored = (width - box[2], box[1], width - box[0], box[3])
        return ours_probability(np.ascontiguousarray(image[:, ::-1]), mirrored)[:, ::-1]
    crop = np.ascontiguousarray(image[cy0:cy1, cx0:cx1][:, ::-1])
    crop_width = cx1 - cx0
    mirrored = (crop_width - (x1 - cx0), y0 - cy0, crop_width - (x0 - cx0), y1 - cy0)
    page = np.zeros((height, width), np.float32)
    page[cy0:cy1, cx0:cx1] = ours_probability(crop, mirrored)[:, ::-1]
    return page


def use_flip() -> bool:
    return (os.environ.get("CASCADE_FLIP") or "1") != "0"


# ---------- routing ----------

def _record(model, reason, started, score=None, parts=None) -> None:
    route = {"model": model, "reason": reason, "seconds": round(time.perf_counter() - started, 3)}
    if score is not None:
        route["confidence"] = round(score, 3)
        route["parts"] = parts
    _local.route = route
    with _route_lock:
        route_counts[(model, reason)] += 1
    log.info("cut-out by %s (%s)%s", model, reason,
             f", confidence {score:.2f} {parts}" if score is not None else "")


def _fallback(image, box, points):
    from pipeline.segment import _SEGMENTERS
    name = fallback_name()
    if name in ("cascade", "mirai") or name not in _SEGMENTERS:
        raise ValueError(f"CASCADE_FALLBACK must be a segmenter other than cascade or mirai, got {name!r}")
    return name, _SEGMENTERS[name](image, box, points)


def segment_ours(image, box, points) -> np.ndarray:
    """SEGMENTER=mirai: our model alone. Clicks go to the fallback; a missing model raises."""
    started = time.perf_counter()
    if box is None or points:
        name, mask = _fallback(image, box, points)
        _record(name, "click", started)
        return mask
    mask = np.where(ours_probability(image, box) > 0.5, 255, 0).astype(np.uint8)
    _record("mirai", "alone", started)
    return mask


def segment_cascade(image, box, points) -> np.ndarray:
    """SEGMENTER=cascade: our model first, the fallback when it is unsure, missing or given a click."""
    started = time.perf_counter()
    if box is None or points:
        name, mask = _fallback(image, box, points)
        _record(name, "click", started)
        return mask
    try:
        prob = ours_probability(image, box)
        score, parts = mask_confidence(prob, box)
        # The score is the lowest check, so the mirror check can only lower it: when the first
        # pass is already under the bar the decision is made, and the second pass is skipped.
        if use_flip() and score >= min_confidence():
            score, parts = mask_confidence(prob, box, _flipped_probability(image, box))
    except Exception as error:  # no cutout_model on this branch, no weights, or the model failed
        name, mask = _fallback(image, box, points)
        _record(name, f"our model unavailable: {type(error).__name__}", started)
        return mask
    if score >= min_confidence():
        mask = np.where(prob > 0.5, 255, 0).astype(np.uint8)
        _record("mirai", "sure", started, score, parts)
        return mask
    weakest = min(parts, key=parts.get)
    name, mask = _fallback(image, box, points)
    _record(name, f"unsure: {weakest}", started, score, parts)
    return mask
