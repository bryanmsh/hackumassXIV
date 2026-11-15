import threading
from pathlib import Path
import numpy as np
import pytest
import torch
from subject_model import namer
from subject_model.namer_train import build_model, save_namer


@pytest.fixture
def always_dog(tmp_path, monkeypatch):
    model = build_model(3)
    with torch.no_grad():
        model.fc.weight.zero_()
        model.fc.bias.copy_(torch.tensor([0.0, 5.0, 0.0]))
    path = tmp_path / "namer.pt"
    save_namer(path, model, classes=["cat", "dog", "person"], input_size=32, epoch=0, val_top1=0.0)
    monkeypatch.setenv("NAMER_WEIGHTS", str(path))
    namer._loaded.clear()
    return path


def page():
    return np.random.default_rng(0).integers(0, 255, (120, 200, 3), dtype=np.uint8)


def green_page_with_a_red_subject():
    image = np.zeros((100, 100, 3), np.uint8)
    image[..., 1] = 255                                   # green everywhere
    image[40:60, 40:60] = (255, 0, 0)                     # the subject is red
    mask = np.zeros((100, 100), bool)
    mask[40:60, 40:60] = True
    return image, mask


def test_name_returns_sorted_guesses(always_dog):
    guesses = namer.name(page())
    assert guesses[0][0] == "dog" and len(guesses) == 3
    assert abs(guesses[0][1] - 0.9867) < 0.001
    assert abs(sum(p for _, p in guesses) - 1.0) < 1e-4
    assert namer.name(page(), top=1) == guesses[:1]


def test_subject_crop_whitens_everything_outside_the_mask():
    crop = namer.subject_crop(*green_page_with_a_red_subject())
    assert crop.shape[0] > 20 and crop.shape[1] > 20      # padding was added
    assert not ((crop[..., 1] == 255) & (crop[..., 0] == 0)).any()      # no green left
    assert crop[0, 0].tolist() == [255, 255, 255]


def test_subject_crop_can_keep_the_surroundings():
    crop = namer.subject_crop(*green_page_with_a_red_subject(), whiten=False)
    assert crop[0, 0].tolist() == [0, 255, 0]


def test_empty_mask_falls_back_to_the_whole_image(always_dog):
    assert namer.name(page(), np.zeros((120, 200), bool)) == namer.name(page())


def test_missing_weights_raise_with_the_path(tmp_path, monkeypatch):
    monkeypatch.setenv("NAMER_WEIGHTS", str(tmp_path / "none.pt"))
    namer._loaded.clear()
    with pytest.raises(FileNotFoundError, match="none.pt"):
        namer.name(page())


def test_default_path_follows_data_dir(monkeypatch):
    monkeypatch.delenv("NAMER_WEIGHTS", raising=False)
    monkeypatch.setenv("DATA_DIR", "/srv/data")
    assert Path(namer.weights_path()) == Path("/srv/data/models/namer.pt")


def test_four_threads_load_once_and_agree(always_dog):
    image, results = page(), [None] * 4
    def work(i):
        results[i] = namer.name(image)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(namer._loaded) == 1 and all(r == results[0] for r in results[1:])
