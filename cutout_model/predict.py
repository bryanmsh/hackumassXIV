"""predict(image, box): the trained U-Net's mask for one box, at page size.

The weights load once per path and stay loaded. One lock guards loading and the forward
pass, so up to 4 pages processed at once share one model, as in pipeline/sam.py.
"""
from __future__ import annotations

import os
import threading
from typing import Dict, Tuple

import cv2
import numpy as np
import torch

from cutout_model.model import UNet
from cutout_model.prompts import build_input, crop_window

_lock = threading.Lock()
_loaded: Dict[str, Tuple] = {}


def weights_path() -> str:
    return os.environ.get("CUTOUT_WEIGHTS") or os.path.join(os.environ.get("DATA_DIR") or "data", "models", "cutout.pt")


def _model(path: str):
    if path not in _loaded:
        if not os.path.exists(path):
            raise FileNotFoundError(f"cut-out model weights not found: {path}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        saved = torch.load(path, map_location=device, weights_only=True)
        model = UNet(widths=saved["widths"])
        model.load_state_dict(saved["model"])
        model.to(device).eval()
        _loaded[path] = (model, int(saved["input_size"]), float(saved["margin"]), device)
    return _loaded[path]


def predict(image: np.ndarray, box) -> np.ndarray:
    """uint8 (height, width) mask, 255 = subject. All zero for an empty or off-page box."""
    height, width = image.shape[:2]
    mask = np.zeros((height, width), np.uint8)
    if crop_window(box, width, height) is None:
        return mask
    with _lock:
        model, size, margin, device = _model(weights_path())
        built = build_input(image, box, margin=margin, size=size)
        if built is None:
            return mask
        x, (x0, y0, x1, y1) = built
        with torch.inference_mode():
            prob = torch.sigmoid(model(torch.from_numpy(x)[None].to(device)))[0, 0].float().cpu().numpy()
    prob = cv2.resize(prob, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
    mask[y0:y1, x0:x1] = np.where(prob > 0.5, 255, 0).astype(np.uint8)
    return mask
