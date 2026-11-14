from pathlib import Path

import numpy as np
from PIL import Image

from contracts.hashing import hash_bytes
from pipeline.masks import clean_mask, iou, mask_box, polygon_mask, save_mask


def blank(width=1000, height=1000):
    return np.zeros((height, width), np.uint8)


def test_clean_keeps_largest_and_big_regions():
    mask = blank()
    mask[100:200, 100:200] = 255  # 10000 px
    mask[500:520, 500:530] = 255  # 600 px: at least 5% of the largest
    mask[800:820, 800:820] = 255  # 400 px: under 5%
    cleaned = clean_mask(mask)
    assert cleaned[150, 150] == 255
    assert cleaned[510, 510] == 255
    assert cleaned[810, 810] == 0
    assert int((cleaned == 255).sum()) == 10600


def test_clean_fills_small_holes_only():
    mask = blank()
    mask[100:500, 100:500] = 255
    mask[150:170, 150:170] = 0  # 400 px hole: under 0.1% of the page (1000 px)
    mask[300:350, 300:350] = 0  # 2500 px hole: stays
    cleaned = clean_mask(mask)
    assert cleaned[160, 160] == 255
    assert cleaned[325, 325] == 0


def test_clean_does_not_fill_background_touching_the_border():
    mask = blank(100, 100)
    mask[10:90, 10:90] = 255
    cleaned = clean_mask(mask)
    assert cleaned[2, 2] == 0


def test_clean_empty_mask_stays_empty():
    cleaned = clean_mask(blank())
    assert cleaned.shape == (1000, 1000)
    assert not cleaned.any()


def test_clean_returns_only_0_and_255():
    mask = blank()
    mask[100:200, 100:200] = 255
    cleaned = clean_mask(mask)
    assert cleaned.dtype == np.uint8
    assert set(np.unique(cleaned)) <= {0, 255}


def test_save_mask_format_and_name(tmp_path):
    mask = blank(1200, 900)
    mask[100:300, 200:500] = 255
    path, mask_hash = save_mask(mask, tmp_path / "pages" / "1.png", tmp_path)
    assert Path(path) == tmp_path / "masks" / f"1_{mask_hash}.png"
    assert len(mask_hash) == 12 and all(c in "0123456789abcdef" for c in mask_hash)
    assert mask_hash == hash_bytes(Path(path).read_bytes())
    saved = Image.open(path)
    assert saved.mode == "L"
    assert saved.size == (1200, 900)
    assert np.array_equal(np.array(saved), mask)


def test_save_mask_never_overwrites(tmp_path):
    mask = blank(120, 90)
    mask[10:30, 20:50] = 255
    first, _ = save_mask(mask, "pages/7.png", tmp_path)
    before = Path(first).stat().st_mtime_ns
    second, _ = save_mask(mask.copy(), "pages/7.png", tmp_path)
    assert second == first
    assert Path(second).stat().st_mtime_ns == before
    assert len(list((tmp_path / "masks").iterdir())) == 1


def test_polygon_mask_fills_the_shape():
    mask = polygon_mask([(10, 10), (50, 10), (50, 50), (10, 50)], 100, 80)
    assert mask.shape == (80, 100)
    assert mask[30, 30] == 255
    assert mask[70, 70] == 0


def test_polygon_mask_clips_to_page():
    mask = polygon_mask([(-50, -50), (60, -50), (60, 60), (-50, 60)], 100, 80)
    assert mask.shape == (80, 100)
    assert mask[0, 0] == 255
    assert mask[70, 90] == 0


def test_mask_box():
    mask = blank(100, 80)
    mask[10:30, 20:60] = 255
    assert mask_box(mask) == (20, 10, 60, 30)
    assert mask_box(blank(100, 80)) is None


def test_iou():
    a = blank(100, 100)
    a[0:50, 0:50] = 255
    b = blank(100, 100)
    b[50:100, 50:100] = 255
    half = blank(100, 100)
    half[0:50, 0:25] = 255
    assert iou(a, a) == 1.0
    assert iou(a, b) == 0.0
    assert iou(a, half) == 0.5
    assert iou(blank(), blank()) == 0.0
