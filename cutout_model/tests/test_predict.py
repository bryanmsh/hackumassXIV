import threading
from pathlib import Path

import numpy as np
import pytest
import torch
from cutout_model import predict
from cutout_model.model import UNet
from cutout_model.train import save_checkpoint


@pytest.fixture
def all_subject(tmp_path, monkeypatch):
    model = UNet()
    with torch.no_grad():
        model.head.weight.zero_()
        model.head.bias.fill_(10.0)       # every pixel predicted as subject
    path = tmp_path / "all.pt"
    save_checkpoint(path, model, input_size=64, margin=0.25, epoch=0, val_iou=0.0)
    monkeypatch.setenv("CUTOUT_WEIGHTS", str(path))
    predict._loaded.clear()
    return path


def page():
    return np.random.default_rng(0).integers(0, 255, (300, 400, 3), dtype=np.uint8)


def test_mask_is_page_sized_and_covers_exactly_the_window(all_subject):
    mask = predict.predict(page(), (100, 100, 200, 180))
    assert mask.shape == (300, 400) and mask.dtype == np.uint8
    assert set(np.unique(mask).tolist()) <= {0, 255}
    expected = np.zeros((300, 400), np.uint8)
    expected[80:200, 75:225] = 255          # the box grown by the checkpoint's 0.25 margin
    assert np.array_equal(mask, expected)


def test_empty_or_offpage_box_gives_an_empty_mask(all_subject):
    assert not predict.predict(page(), (50, 50, 50, 50)).any()
    assert not predict.predict(page(), (900, 900, 950, 950)).any()


def test_missing_weights_raise_with_the_path(tmp_path, monkeypatch):
    missing = tmp_path / "none.pt"
    monkeypatch.setenv("CUTOUT_WEIGHTS", str(missing))
    predict._loaded.clear()
    with pytest.raises(FileNotFoundError, match="none.pt"):
        predict.predict(page(), (100, 100, 200, 180))


def test_default_path_follows_data_dir(monkeypatch):
    monkeypatch.delenv("CUTOUT_WEIGHTS", raising=False)
    monkeypatch.setenv("DATA_DIR", "/srv/data")
    assert Path(predict.weights_path()) == Path("/srv/data/models/cutout.pt")   # "\" on Windows


def test_four_threads_load_once_and_agree(all_subject):
    image, box = page(), (100, 100, 200, 180)
    results = [None] * 4

    def work(i):
        results[i] = predict.predict(image, box)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(predict._loaded) == 1
    assert all(np.array_equal(results[0], other) for other in results[1:])


def test_probability_map_matches_the_mask(all_subject):
    image, box = page(), (100, 100, 200, 180)
    prob = predict.predict_prob(image, box)
    assert prob.shape == (300, 400) and prob.dtype == np.float32
    assert prob[80:200, 75:225].min() > 0.99 and prob[:80].max() == 0.0   # sure inside the window, 0 outside
    assert np.array_equal(predict.predict(image, box), np.where(prob > 0.5, 255, 0).astype(np.uint8))
    assert not predict.predict_prob(image, (50, 50, 50, 50)).any()
