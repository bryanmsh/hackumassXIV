"""Image folders to classifier examples, and the image loading that prediction shares."""
from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision.transforms import v2

INPUT_SIZE = 160
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def class_name(folder) -> str:
    """The folder name in lowercase, with `_` and `-` turned into spaces."""
    return str(folder).lower().replace("_", " ").replace("-", " ")


def find_images(roots) -> tuple[list[tuple[Path, int]], list[str]]:
    """Every image under {root}/{class folder}/, with its class index, and the sorted class names."""
    found = []
    for root in map(Path, roots):
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in IMAGE_SUFFIXES:
                    found.append((path, class_name(folder.name)))
    classes = sorted({name for _, name in found})
    index = {name: i for i, name in enumerate(classes)}
    return [(path, index[name]) for path, name in found], classes


def split(items, val_fraction=0.05, seed=0) -> tuple[list, list]:
    """(train, val), shuffled with the seed. The validation part is never empty."""
    shuffled = list(items)
    random.Random(seed).shuffle(shuffled)
    n_val = max(1, round(len(shuffled) * val_fraction))
    return shuffled[n_val:], shuffled[:n_val]


def load_image(path, at_least=None) -> np.ndarray | None:
    """RGB uint8 (height, width, 3), transparent pixels on white; None when the file cannot be read.

    With at_least=N a large JPEG may be decoded at a half, a quarter or an eighth of its size,
    never with a side under N."""
    try:
        with Image.open(path) as image:
            if at_least:
                image.draft("RGB", (at_least, at_least))
            image.load()
            if image.mode in ("RGBA", "LA", "PA") or (image.mode == "P" and "transparency" in image.info):
                rgba = image.convert("RGBA")
                white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                image = Image.alpha_composite(white, rgba)
            return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    except Exception:
        return None


def to_square(image: np.ndarray, size=INPUT_SIZE) -> np.ndarray:
    """Padded to a centred square with white, then resized: uint8 (size, size, 3)."""
    height, width = image.shape[:2]
    side = max(height, width)
    top, left = (side - height) // 2, (side - width) // 2
    square = np.full((side, side, 3), 255, np.uint8)
    square[top:top + height, left:left + width] = image
    interpolation = cv2.INTER_AREA if side > size else cv2.INTER_LINEAR
    return cv2.resize(square, (size, size), interpolation=interpolation)


def to_tensor(square: np.ndarray) -> torch.Tensor:
    """float32 (3, size, size), scaled to -1..1."""
    return torch.from_numpy(np.ascontiguousarray(square.transpose(2, 0, 1))).float() / 127.5 - 1.0


class NamerDataset(torch.utils.data.Dataset):
    """(image tensor, class index) pairs. A file that cannot be read is replaced by the next one."""

    def __init__(self, items, train, size=INPUT_SIZE):
        self.items, self.train, self.size = list(items), train, size
        self.augment = v2.Compose([
            v2.RandomResizedCrop(size, scale=(0.35, 1.0), ratio=(3 / 4, 4 / 3), antialias=True),
            v2.RandomHorizontalFlip(0.5),
            v2.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
            v2.RandomGrayscale(0.1),
        ])

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        for step in range(len(self.items)):
            path, label = self.items[(index + step) % len(self.items)]
            image = load_image(path, at_least=2 * self.size)
            if image is not None:
                break
        else:
            raise RuntimeError("no readable image in the dataset")
        if not self.train:
            return to_tensor(to_square(image, self.size)), int(label)
        square = to_square(image, self.size * 5 // 4)
        x = self.augment(torch.from_numpy(np.ascontiguousarray(square.transpose(2, 0, 1))))
        return x.float() / 127.5 - 1.0, int(label)
