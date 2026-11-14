"""Name a crop of a page: five guesses from the namer, with probabilities."""
from __future__ import annotations

import os
import threading

import numpy as np
import torch

from subject_model.namer_data import to_square, to_tensor
from subject_model.namer_train import build_model

LOCK = threading.Lock()  # one lock for every local model, so the namer and the finder never run at once
WHITEN = True  # whiten everything outside the mask before naming
_loaded: dict[str, tuple] = {}


def weights_path() -> str:
    return os.environ.get("NAMER_WEIGHTS") or os.path.join(os.environ.get("DATA_DIR") or "data", "models", "namer.pt")


def subject_crop(image: np.ndarray, mask, pad=0.08, whiten=True) -> np.ndarray:
    """The rectangle around the mask, grown by `pad` of its longer side and clipped to the image.
    With `whiten`, every pixel outside the mask is white."""
    mask = np.asarray(mask) > 0
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    grow = round(pad * max(y1 - y0, x1 - x0))
    height, width = mask.shape
    y0, y1, x0, x1 = max(0, y0 - grow), min(height, y1 + grow), max(0, x0 - grow), min(width, x1 + grow)
    crop = image[y0:y1, x0:x1].copy()
    if whiten:
        crop[~mask[y0:y1, x0:x1]] = 255
    return crop


def _model(path: str):
    """(model, classes, input_size, device), loaded once per path. Call under LOCK."""
    if path not in _loaded:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"namer weights not found: {path}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        saved = torch.load(path, map_location=device, weights_only=True)
        model = build_model(len(saved["classes"]))
        model.load_state_dict(saved["model"])
        model.to(device).eval()
        _loaded[path] = (model, list(saved["classes"]), int(saved["input_size"]), device)
    return _loaded[path]


def name(image: np.ndarray, mask=None, top=5) -> list[tuple[str, float]]:
    """Class names with probabilities, most likely first. `image` is RGB uint8; `mask` is bool or 0/255."""
    if mask is not None and np.asarray(mask).any():
        image = subject_crop(image, mask, whiten=WHITEN)
    with LOCK:
        model, classes, size, device = _model(weights_path())
        x = to_tensor(to_square(image, size))[None].to(device)
        with torch.inference_mode():
            probs = torch.softmax(model(x).float(), dim=1)[0].cpu()
    values, indexes = probs.topk(min(top, len(classes)))
    return [(classes[i], float(p)) for p, i in zip(values.tolist(), indexes.tolist())]
