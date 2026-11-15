"""Find what stands out on a whole page: the finder's map, cut into separate blobs with rectangles."""
from __future__ import annotations

import os

import cv2
import numpy as np
import torch

from cutout_model.model import UNet
from cutout_model.prompts import build_input
from subject_model.namer import LOCK

MAX_COVER = 0.60  # a map marking more of the page than this found nothing in particular
MIN_BLOB = 0.005  # a blob smaller than this share of the page is a speck
MAX_BLOBS = 5
WIDE = 1.5  # a page wider than this times its height is searched as two halves (a two-page spread)
_loaded: dict[str, tuple] = {}


def weights_path() -> str:
    return os.environ.get("FINDER_WEIGHTS") or os.path.join(os.environ.get("DATA_DIR") or "data", "models", "finder.pt")


def blobs_from_map(prob: np.ndarray, width: int, height: int) -> list:
    """(rectangle (x0, y0, x1, y1), bool mask) for each separate region of the map, largest first,
    for an image `width` by `height`. Right and bottom edges are exclusive."""
    marked = cv2.resize(np.asarray(prob, np.float32), (width, height), interpolation=cv2.INTER_LINEAR) > 0.5
    if marked.mean() > MAX_COVER:
        return []
    count, labels, stats, _ = cv2.connectedComponentsWithStats(marked.astype(np.uint8), connectivity=8)
    min_area = MIN_BLOB * width * height
    regions = sorted((i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= min_area),
                     key=lambda i: stats[i, cv2.CC_STAT_AREA], reverse=True)
    blobs = []
    for i in regions[:MAX_BLOBS]:
        x, y, w, h = (int(v) for v in stats[i, :4])
        blobs.append(((x, y, x + w, y + h), labels == i))
    return blobs


def _model(path: str):
    """(model, input_size, margin, device), loaded once per path. Call under LOCK."""
    if path not in _loaded:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"finder weights not found: {path}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        saved = torch.load(path, map_location=device, weights_only=True)
        model = UNet(widths=saved["widths"])
        model.load_state_dict(saved["model"])
        model.to(device).eval()
        _loaded[path] = (model, int(saved["input_size"]), float(saved["margin"]), device)
    return _loaded[path]


def _probability(image: np.ndarray) -> np.ndarray:
    """The model's map for one RGB image, values 0 to 1, at the checkpoint's input size."""
    height, width = image.shape[:2]
    with LOCK:
        model, size, margin, device = _model(weights_path())
        x, _ = build_input(np.ascontiguousarray(image), (0, 0, width, height), margin=margin, size=size)
        with torch.inference_mode():
            logits = model(torch.from_numpy(x)[None].to(device))
        return torch.sigmoid(logits.float())[0, 0].cpu().numpy()


def find_blobs(image: np.ndarray) -> list:
    """Blobs on a whole RGB page, largest first. A two-page spread is searched as two halves."""
    height, width = image.shape[:2]
    if width <= WIDE * height:
        return blobs_from_map(_probability(image), width, height)
    middle = width // 2
    found = []
    for left, half in ((0, image[:, :middle]), (middle, image[:, middle:])):
        for (x0, y0, x1, y1), mask in blobs_from_map(_probability(half), half.shape[1], height):
            page_mask = np.zeros((height, width), bool)
            page_mask[:, left:left + half.shape[1]] = mask
            found.append(((x0 + left, y0, x1 + left, y1), page_mask))
    found.sort(key=lambda blob: int(blob[1].sum()), reverse=True)
    return found[:MAX_BLOBS]
