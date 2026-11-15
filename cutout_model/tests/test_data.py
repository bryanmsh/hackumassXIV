import cv2
import numpy as np
import pytest
import torch
from cutout_model.data import CutoutDataset, components, find_pairs, jitter_box, split


def test_find_pairs_matches_photos_to_masks(duts_root):
    pairs = find_pairs(duts_root)
    assert len(pairs) == 8
    assert all(photo.stem == mask.stem for photo, mask in pairs)


def test_find_pairs_raises_when_the_folder_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_pairs(tmp_path / "nowhere")


def test_split_is_disjoint_and_repeatable(duts_root):
    pairs = find_pairs(duts_root)
    train, val = split(pairs, val_fraction=0.25, seed=0)
    assert len(train) == 6 and len(val) == 2 and not set(train) & set(val)
    assert split(pairs, val_fraction=0.25, seed=0) == (train, val)


def test_components_splits_objects_and_drops_specks():
    mask = np.zeros((100, 100), np.uint8)
    mask[10:40, 10:40] = 255      # 900 px
    mask[60:80, 60:80] = 255      # 400 px
    mask[95:97, 95:97] = 255      # 4 px, under 1% of the image
    parts = components(mask)
    assert [int(p.sum()) for p in parts] == [900, 400]


def test_jitter_box_stays_on_the_page_and_within_ten_percent():
    rng = np.random.default_rng(0)
    for _ in range(200):
        x0, y0, x1, y1 = jitter_box((100, 100, 300, 200), 320, 240, rng)
        assert 80 <= x0 <= 120 and 280 <= x1 <= 320
        assert 90 <= y0 <= 110 and 190 <= y1 <= 210


def test_val_items_have_the_right_shape_and_repeat(duts_root):
    data = CutoutDataset(find_pairs(duts_root), train=False, size=64)
    x, y = data[0]
    assert x.shape == (4, 64, 64) and x.dtype == torch.float32
    assert y.shape == (1, 64, 64) and set(y.unique().tolist()) <= {0.0, 1.0}
    assert 0.2 < float(y.mean()) < 0.6                       # a tight box is mostly subject
    again_x, again_y = data[0]
    assert torch.equal(x, again_x) and torch.equal(y, again_y)


def test_train_items_vary(duts_root):
    data = CutoutDataset(find_pairs(duts_root), train=True, size=64)
    assert any(not torch.equal(data[0][0], data[0][0]) for _ in range(5))


def test_black_mask_and_wrong_size_mask_still_give_an_example(duts_root):
    pairs = find_pairs(duts_root)
    cv2.imwrite(str(pairs[0][1]), np.zeros((96, 128), np.uint8))               # nothing labelled
    cv2.imwrite(str(pairs[1][1]), cv2.resize(cv2.imread(str(pairs[1][1]), 0), (64, 48)))  # half size
    data = CutoutDataset(pairs, train=False, size=64)
    for index in (0, 1):
        x, y = data[index]
        assert x.shape == (4, 64, 64) and float(y.sum()) > 0
