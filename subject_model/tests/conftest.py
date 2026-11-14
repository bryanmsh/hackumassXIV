import numpy as np
import pytest
from PIL import Image

from cutout_model.tests.conftest import duts_root  # noqa: F401


def _solid(path, colour, size=(64, 48)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)


@pytest.fixture
def image_roots(tmp_path):
    """Two class roots: clipart with cat, dog (plus one unreadable file) and Sea_Turtle; extra with person and cat."""
    clipart, extra = tmp_path / "clipart", tmp_path / "extra"
    for i in range(4):
        _solid(clipart / "cat" / f"{i}.jpg", (255, 0, 0))
        _solid(clipart / "dog" / f"{i}.jpg", (0, 255, 0))
    (clipart / "dog" / "bad.jpg").write_bytes(b"not an image")
    _solid(clipart / "Sea_Turtle" / "0.jpg", (255, 255, 0))
    (extra / "person").mkdir(parents=True)
    for i in range(3):
        rgba = np.zeros((48, 48, 4), np.uint8)
        rgba[16:33, 16:33] = (0, 0, 255, 255)
        Image.fromarray(rgba, "RGBA").save(extra / "person" / f"{i}.png")
    (extra / "cat").mkdir(parents=True)
    Image.fromarray(np.full((48, 48), 128, np.uint8), "L").save(extra / "cat" / "grey.png")
    return [clipart, extra]
