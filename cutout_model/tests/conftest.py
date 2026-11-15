import cv2
import numpy as np
import pytest


@pytest.fixture
def art(tmp_path):
    """3 drawn cut-outs (a red disc on transparency) and 2 plain blue backgrounds."""
    fg, bg = tmp_path / "fg", tmp_path / "bg"
    fg.mkdir()
    bg.mkdir()
    for i in range(3):
        cutout = np.zeros((200, 200, 4), np.uint8)
        cv2.circle(cutout, (100, 100), 80, (0, 0, 255, 255), -1)  # BGRA: opaque red
        cv2.imwrite(str(fg / f"{i}.png"), cutout)
    for i in range(2):
        cv2.imwrite(str(bg / f"{i}.jpg"), np.full((800, 600, 3), (255, 0, 0), np.uint8))  # BGR blue
    return fg, bg


@pytest.fixture
def duts_root(tmp_path):
    """8 DUTS-style pairs: a noise photo with one solid ellipse, and its 0/255 mask."""
    root = tmp_path / "DUTS-TR"
    images, masks = root / "DUTS-TR-Image", root / "DUTS-TR-Mask"
    images.mkdir(parents=True)
    masks.mkdir(parents=True)
    for i in range(8):
        rng = np.random.default_rng(i)
        photo = rng.integers(0, 255, (96, 128, 3), dtype=np.uint8)
        color = tuple(int(c) for c in rng.integers(0, 255, 3))
        cv2.ellipse(photo, (64, 48), (30, 20), 0, 0, 360, color, -1)
        mask = np.zeros((96, 128), np.uint8)
        cv2.ellipse(mask, (64, 48), (30, 20), 0, 0, 360, 255, -1)
        cv2.imwrite(str(images / f"{i}.jpg"), photo)
        cv2.imwrite(str(masks / f"{i}.png"), mask)
    return root
