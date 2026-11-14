"""DUTS photo and mask pairs turned into (input, target) training examples."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch

from cutout_model.prompts import INPUT_SIZE, MARGIN, build_input

Pair = Tuple[Path, Path]


def find_pairs(root) -> List[Pair]:
    """(photo, mask) for every DUTS photo that has a mask, sorted by name."""
    root = Path(root)
    images, masks = root / "DUTS-TR-Image", root / "DUTS-TR-Mask"
    if not images.is_dir() or not masks.is_dir():
        raise FileNotFoundError(f"no DUTS-TR-Image and DUTS-TR-Mask folders under {root}")
    pairs = []
    for photo in sorted(images.glob("*.jpg")):
        mask = masks / f"{photo.stem}.png"
        if mask.exists():
            pairs.append((photo, mask))
    return pairs


def split(pairs, val_fraction=0.05, seed=0) -> Tuple[list, list]:
    """(train, val), shuffled with the seed. The validation part is never empty."""
    order = np.random.default_rng(seed).permutation(len(pairs))
    shuffled = [pairs[i] for i in order]
    n_val = max(1, round(len(pairs) * val_fraction))
    return shuffled[n_val:], shuffled[:n_val]


def components(mask: np.ndarray, min_fraction=0.01) -> List[np.ndarray]:
    """8-connected regions of mask > 127 covering at least `min_fraction` of the image, largest first."""
    on = (mask > 127).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(on, connectivity=8)
    floor = min_fraction * mask.size
    found = [(stats[i, cv2.CC_STAT_AREA], i) for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= floor]
    return [labels == i for _, i in sorted(found, reverse=True)]


def jitter_box(box, width, height, rng, amount=0.10) -> Tuple[float, float, float, float]:
    """Move each edge by up to `amount` of the box's width or height, kept on the page."""
    x0, y0, x1, y1 = box
    dx, dy = amount * (x1 - x0), amount * (y1 - y0)
    x0, x1 = x0 + rng.uniform(-dx, dx), x1 + rng.uniform(-dx, dx)
    y0, y1 = y0 + rng.uniform(-dy, dy), y1 + rng.uniform(-dy, dy)
    return (float(np.clip(x0, 0, width)), float(np.clip(y0, 0, height)),
            float(np.clip(x1, 0, width)), float(np.clip(y1, 0, height)))


def bounding_box(target: np.ndarray) -> Tuple[float, float, float, float]:
    ys, xs = np.nonzero(target)
    return float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)


def make_example(image, target, box, margin=MARGIN, size=INPUT_SIZE):
    """(input (4, size, size), target (1, size, size)) as float32, or None for an empty box."""
    built = build_input(image, box, margin, size)
    if built is None:
        return None
    x, (wx0, wy0, wx1, wy1) = built
    crop = target[wy0:wy1, wx0:wx1].astype(np.uint8)
    y = cv2.resize(crop, (size, size), interpolation=cv2.INTER_NEAREST).astype(np.float32)
    return x, (y > 0).astype(np.float32)[None]


def read_rgb(path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def read_grey(path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"cannot read {path}")
    return image


def augment_photo(image: np.ndarray, rng) -> np.ndarray:
    """Brightness, contrast and saturation, each scaled by a random factor."""
    out = image.astype(np.float32)
    mean = out.mean()
    out = (out - mean) * rng.uniform(0.7, 1.3) + mean
    out = out * rng.uniform(0.7, 1.3)
    out = np.clip(out, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(out, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * rng.uniform(0.6, 1.4), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def train_example(image, target, rng, size):
    """Box jitter and a random margin, shared by DUTS and pasted examples."""
    height, width = target.shape
    box = jitter_box(bounding_box(target), width, height, rng)
    return make_example(image, target, box, margin=rng.uniform(0.15, 0.40), size=size)


def _to_tensors(example):
    x, y = example
    return torch.from_numpy(x), torch.from_numpy(y)


class CutoutDataset(torch.utils.data.Dataset):
    """One subject per item: the largest region for validation, a random one for training."""

    def __init__(self, pairs, train: bool, size: int = INPUT_SIZE):
        self.pairs, self.train, self.size = list(pairs), train, size
        self._rng: Optional[np.random.Generator] = None

    def __len__(self):
        return len(self.pairs)

    @property
    def rng(self) -> np.random.Generator:
        if self._rng is None:  # made on first use, so each loader worker gets its own stream
            self._rng = np.random.default_rng()
        return self._rng

    def __getitem__(self, index):
        for step in range(len(self.pairs)):
            example = self._example((index + step) % len(self.pairs))
            if example is not None:
                return _to_tensors(example)
        raise ValueError("no usable example in the dataset")

    def _example(self, index):
        photo_path, mask_path = self.pairs[index]
        image, mask = read_rgb(photo_path), read_grey(mask_path)
        if mask.shape != image.shape[:2]:
            mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        parts = components(mask) or components(mask, min_fraction=0.0)[:1]
        if not parts:
            return None
        if not self.train:
            return make_example(image, parts[0], bounding_box(parts[0]), MARGIN, self.size)
        rng = self.rng
        target = parts[rng.integers(len(parts))]
        if rng.random() < 0.5:
            image, target = image[:, ::-1].copy(), target[:, ::-1].copy()
        return train_example(augment_photo(image, rng), target, rng, self.size)
