from pathlib import Path

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


def book(path, pages):
    """A PDF of `pages` 400 by 300 pages; page N carries the words "Page N."."""
    import pymupdf
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for number in range(1, pages + 1):
        doc.new_page(width=400, height=300).insert_text((50, 150), f"Page {number}.", fontsize=24)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def testset(tmp_path):
    """One hand-labelled page (a ball on a 400 by 300 page) and a two-page book."""
    folder = tmp_path / "testset"
    folder.mkdir()
    Image.new("RGB", (400, 300), "white").save(folder / "ball.png")
    mask = np.zeros((300, 400), np.uint8)
    mask[100:200, 100:300] = 255
    Image.fromarray(mask).save(folder / "ball_mask.png")
    (folder / "labels.csv").write_text("name,label,text\nball,ball,The ball rolled.\n")
    book(folder / "books" / "tale.pdf", pages=2)
    return folder
