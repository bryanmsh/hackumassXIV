import cv2
import numpy as np
import torch
from cutout_model.paste import PasteDataset, compose


def red_circle():
    art = np.zeros((200, 200, 4), np.uint8)
    cv2.circle(art, (100, 100), 80, (255, 0, 0, 255), -1)
    return art


def test_compose_mask_matches_the_pasted_pixels():
    blue = np.zeros((600, 800, 3), np.uint8)
    blue[..., 2] = 255
    rng = np.random.default_rng(0)
    for _ in range(20):
        picture, mask = compose(blue, [red_circle()], rng)
        assert picture.shape == (512, 512, 3) and mask.shape == (512, 512) and mask.dtype == bool
        assert 0.02 < mask.mean() < 0.60
        assert (picture[mask][:, 0] > 200).mean() > 0.90      # masked pixels are red (edges blend)
        assert (picture[~mask][:, 2] > 200).mean() > 0.95     # the rest is still blue


def test_compose_mask_is_the_top_cutout_only():
    blue = np.zeros((600, 800, 3), np.uint8)
    blue[..., 2] = 255
    green = red_circle()
    green[..., :3] = (0, 255, 0)
    picture, mask = compose(blue, [red_circle(), green], np.random.default_rng(1))
    assert (picture[mask][:, 1] > 200).mean() > 0.90          # only the last one pasted


def test_paste_dataset_items_match_the_duts_items(art):
    fg, bg = art
    data = PasteDataset(sorted(fg.glob("*.png")), sorted(bg.glob("*.jpg")), length=10, size=64)
    assert len(data) == 10
    x, y = data[3]
    assert x.shape == (4, 64, 64) and x.dtype == torch.float32
    assert y.shape == (1, 64, 64) and 0.05 < float(y.mean()) < 0.8
