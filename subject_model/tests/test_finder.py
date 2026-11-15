import numpy as np
import pytest
import torch
from cutout_model.model import UNet
from cutout_model.train import save_checkpoint
from subject_model import finder


@pytest.fixture
def flat_finder(tmp_path, monkeypatch):
    def make(bias):
        model = UNet()
        with torch.no_grad():
            model.head.weight.zero_()
            model.head.bias.fill_(bias)
        path = tmp_path / "finder.pt"
        save_checkpoint(path, model, input_size=64, margin=0.25, epoch=0, val_iou=0.0)
        monkeypatch.setenv("FINDER_WEIGHTS", str(path))
        finder._loaded.clear()
        return path
    return make


def two_rectangles():
    prob = np.zeros((100, 200), np.float32)
    prob[10:40, 10:60] = 1.0          # 1,500 px
    prob[60:90, 120:190] = 1.0        # 2,100 px
    prob[0:2, 198:200] = 1.0          # a speck
    return prob


def test_blobs_are_scaled_sorted_and_specks_dropped():
    blobs = finder.blobs_from_map(two_rectangles(), width=400, height=200)
    assert [box for box, _ in blobs] == [(240, 120, 380, 180), (20, 20, 120, 80)]
    assert all(mask.shape == (200, 400) and mask.dtype == bool for _, mask in blobs)
    assert int(blobs[0][1].sum()) == 8400


def test_a_map_that_covers_the_page_gives_nothing():
    assert finder.blobs_from_map(np.ones((50, 50), np.float32), 400, 200) == []
    assert finder.blobs_from_map(np.zeros((50, 50), np.float32), 400, 200) == []


def test_at_most_five_blobs():
    prob = np.zeros((100, 200), np.float32)
    for i in range(7):
        prob[10:30, i * 25 + 5: i * 25 + 20] = 1.0
    assert len(finder.blobs_from_map(prob, 400, 200)) == 5


@pytest.mark.parametrize("bias", [10.0, -10.0])
def test_find_blobs_on_all_or_nothing_weights_is_empty(flat_finder, bias):
    flat_finder(bias)
    page = np.random.default_rng(0).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    assert finder.find_blobs(page) == []


def test_a_wide_page_is_searched_as_two_halves(monkeypatch):
    def one_square(image):                                 # the same blob in whatever it is shown
        prob = np.zeros((100, 100), np.float32)
        prob[40:60, 40:60] = 1.0
        return prob
    monkeypatch.setattr(finder, "_probability", one_square)
    blobs = finder.find_blobs(np.zeros((200, 600, 3), np.uint8))
    assert sorted(box for box, _ in blobs) == [(120, 80, 180, 120), (420, 80, 480, 120)]
    assert all(mask.shape == (200, 600) for _, mask in blobs)


def test_missing_weights_raise_with_the_path(tmp_path, monkeypatch):
    monkeypatch.setenv("FINDER_WEIGHTS", str(tmp_path / "none.pt"))
    finder._loaded.clear()
    with pytest.raises(FileNotFoundError, match="none.pt"):
        finder.find_blobs(np.zeros((300, 400, 3), np.uint8))
