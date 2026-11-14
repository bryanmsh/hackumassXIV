"""Fractions of the page and master pixels. The only place the two are converted."""
import math
from collections.abc import Sequence


def to_pixels(point: Sequence[float], width: int, height: int) -> tuple[float, float]:
    """A position from the API (fractions 0 to 1, top-left origin) in master pixels.

    Raises ValueError for a position outside the page or not a number.
    """
    x, y = point
    for value in (x, y):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("a position must be a fraction from 0 to 1")
    return (x * width, y * height)


def box_to_fractions(box: Sequence[float], width: int, height: int) -> list[float]:
    """A box in master pixels (x0, y0, x1, y1) as fractions of the page, rounded to 4 places."""
    x0, y0, x1, y1 = box
    return [round(x0 / width, 4), round(y0 / height, 4), round(x1 / width, 4), round(y1 / height, 4)]
