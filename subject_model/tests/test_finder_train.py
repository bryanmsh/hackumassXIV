import cv2
import numpy as np
import torch
from cutout_model.data import find_pairs
from subject_model import finder_train
from subject_model.finder_train import WholeImageDataset, on_paper


def test_item_is_the_whole_picture_with_every_object(duts_root):
    pairs = find_pairs(duts_root)
    mask = cv2.imread(str(pairs[0][1]), 0)
    mask[5:15, 5:25] = 255                                 # a second object
    cv2.imwrite(str(pairs[0][1]), mask)
    x, y = WholeImageDataset(pairs, train=False, size=64)[0]
    assert x.shape == (4, 64, 64) and y.shape == (1, 64, 64)
    assert float(x[3].min()) == 1.0                        # the box is the whole image
    assert abs(float(y.mean()) - (mask > 127).mean()) < 0.02     # both objects are in the target


def test_on_paper_moves_the_mask_with_the_photo():
    photo = np.zeros((96, 128, 3), np.uint8)               # all black, all subject
    mask = np.ones((96, 128), bool)
    for seed in range(5):
        image, moved = on_paper(photo, mask, np.random.default_rng(seed))
        assert image.shape == photo.shape and moved.shape == mask.shape and moved.dtype == bool
        assert np.array_equal(moved, image.max(axis=2) < 128)    # the mask is exactly where the photo went
        assert 0.4 < moved.mean() < 0.95                         # the rest is light paper


def test_training_pages_get_words_that_are_not_in_the_target(duts_root, monkeypatch):
    calls = []

    def blackout(image, rng, fonts):
        calls.append(1)
        return np.zeros_like(image)

    monkeypatch.setattr(finder_train, "draw_lines", blackout)
    monkeypatch.setattr(finder_train, "PAGE_SHARE", 1.0)
    pairs = find_pairs(duts_root)
    x, y = WholeImageDataset(pairs, train=True, size=64)[0]
    assert calls and float(x[:3].abs().max()) == 0.0       # the picture was drawn on
    assert float(y.mean()) > 0.03                          # the target still marks the object
    WholeImageDataset(pairs, train=False, size=64)[0]
    assert len(calls) == 1                                 # never when scoring


def test_main_writes_a_cutout_format_checkpoint(duts_root, tmp_path):
    best = finder_train.main(["--duts", str(duts_root), "--out", str(tmp_path / "run"), "--epochs", "2",
                              "--batch", "4", "--size", "64", "--widths", "8", "16", "32", "64", "128",
                              "--workers", "0", "--device", "cpu"])
    saved = torch.load(best, map_location="cpu", weights_only=True)
    assert set(saved) == {"model", "widths", "input_size", "margin", "epoch", "val_iou"}
    assert saved["margin"] == 0.0 and saved["input_size"] == 64 and saved["widths"] == [8, 16, 32, 64, 128]
