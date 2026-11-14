"""Color parsing and WCAG contrast helpers."""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np

RGB = Tuple[int, int, int]

SWATCHES = {
    "red": "#E53935",
    "yellow": "#FDD835",
    "orange": "#FB8C00",
    "green": "#43A047",
    "blue": "#1E88E5",
    "purple": "#AB47BC",
    "pink": "#EC407A",
    "white": "#FFFFFF",
}


def hex_to_rgb(value: str) -> RGB:
    s = value.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"not a hex color: {value!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _linearize(c: np.ndarray) -> np.ndarray:
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def relative_luminance(rgb: Sequence[float]) -> float:
    lin = _linearize(np.asarray(rgb, dtype=np.float64))
    return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def luminance_map(img: np.ndarray) -> np.ndarray:
    """Per-pixel relative luminance of an RGB uint8 image."""
    lin = _linearize(img.astype(np.float64))
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def ratio_from_luminance(l1: float, l2: float) -> float:
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def contrast_ratio(a, b) -> float:
    """WCAG contrast ratio between two colors given as hex strings or RGB."""
    ra = hex_to_rgb(a) if isinstance(a, str) else a
    rb = hex_to_rgb(b) if isinstance(b, str) else b
    return ratio_from_luminance(relative_luminance(ra), relative_luminance(rb))


def text_color_for(background: RGB) -> RGB:
    white, black = (255, 255, 255), (0, 0, 0)
    if contrast_ratio(white, background) >= contrast_ratio(black, background):
        return white
    return black
