"""Pasted-drawing examples: transparent drawn cut-outs placed on scene backgrounds.

The label is the cut-out's own transparency, so no model makes any label.
"""
from __future__ import annotations

from typing import List, Optional

import cv2
import numpy as np
import torch

from cutout_model.data import read_rgb, train_example
from cutout_model.prompts import INPUT_SIZE


def _paste(canvas_rgb: np.ndarray, cutout: np.ndarray, rng) -> np.ndarray:
    """Alpha-blend one RGBA cut-out onto the canvas in place. Returns its alpha on the canvas (0..1)."""
    side = canvas_rgb.shape[0]
    alpha = cutout[..., 3]
    ys, xs = np.nonzero(alpha)
    placed = np.zeros((side, side), np.float32)
    if xs.size == 0:
        return placed
    art = cutout[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if rng.random() < 0.5:
        art = art[:, ::-1]
    scale = rng.uniform(0.2, 0.7) * side / max(art.shape[:2])
    w, h = max(1, int(round(art.shape[1] * scale))), max(1, int(round(art.shape[0] * scale)))
    art = cv2.resize(np.ascontiguousarray(art), (w, h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    cx, cy = rng.uniform(0.2, 0.8) * side, rng.uniform(0.2, 0.8) * side
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(side, x0 + w), min(side, y0 + h)
    if cx1 <= cx0 or cy1 <= cy0:
        return placed
    piece = art[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0].astype(np.float32)
    a = piece[..., 3:4] / 255.0
    region = canvas_rgb[cy0:cy1, cx0:cx1].astype(np.float32)
    canvas_rgb[cy0:cy1, cx0:cx1] = np.clip(piece[..., :3] * a + region * (1 - a), 0, 255).astype(np.uint8)
    placed[cy0:cy1, cx0:cx1] = a[..., 0]
    return placed


def compose(background: np.ndarray, cutouts: List[np.ndarray], rng, canvas: int = 512):
    """(RGB picture (canvas, canvas, 3), bool mask of the last cut-out pasted)."""
    h, w = background.shape[:2]
    scale = canvas / min(h, w)
    if scale > 1 or min(h, w) > 2 * canvas:
        background = cv2.resize(background, (max(canvas, int(round(w * scale))), max(canvas, int(round(h * scale)))),
                                interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        h, w = background.shape[:2]
    top, left = int(rng.integers(0, h - canvas + 1)), int(rng.integers(0, w - canvas + 1))
    picture = background[top:top + canvas, left:left + canvas].copy()
    alpha = np.zeros((canvas, canvas), np.float32)
    for cutout in cutouts:
        alpha = _paste(picture, cutout, rng)
    return picture, alpha > 0.5


def read_rgba(path) -> Optional[np.ndarray]:
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[2] != 4:
        return None
    return cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)


class PasteDataset(torch.utils.data.Dataset):
    """`length` random pasted pictures; files are read on demand."""

    def __init__(self, cutout_paths, background_paths, length, size: int = INPUT_SIZE):
        self.cutouts, self.backgrounds = list(cutout_paths), list(background_paths)
        self.length, self.size = int(length), size
        self._rng = None

    def __len__(self):
        return self.length

    @property
    def rng(self):
        if self._rng is None:
            self._rng = np.random.default_rng()
        return self._rng

    def __getitem__(self, index):
        rng = self.rng
        for _ in range(20):
            background = read_rgb(self.backgrounds[rng.integers(len(self.backgrounds))])
            chosen = [read_rgba(self.cutouts[rng.integers(len(self.cutouts))]) for _ in range(rng.integers(1, 4))]
            chosen = [c for c in chosen if c is not None]
            if not chosen:
                continue
            picture, mask = compose(background, chosen, rng)
            if mask.sum() < 16:
                continue
            example = train_example(picture, mask, rng, self.size)
            if example is not None:
                x, y = example
                return torch.from_numpy(x), torch.from_numpy(y)
        raise ValueError("could not make a pasted example: check the cut-out PNGs have transparency")
