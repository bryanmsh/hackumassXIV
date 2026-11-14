import json
import os

import cv2
import numpy as np
import pytest
from cutout_model.evaluate import grow_box, load_testset, score


@pytest.fixture
def testset(tmp_path):
    rng = np.random.default_rng(0)
    page = rng.integers(200, 256, (300, 400, 3), dtype=np.uint8)
    cv2.ellipse(page, (200, 150), (80, 50), 0, 0, 360, (40, 40, 40), -1)
    mask = np.zeros((300, 400), np.uint8)
    cv2.ellipse(mask, (200, 150), (80, 50), 0, 0, 360, 255, -1)
    cv2.imwrite(str(tmp_path / "ball.png"), page)
    cv2.imwrite(str(tmp_path / "ball_mask.png"), mask)
    return tmp_path


def test_grow_box_adds_five_percent_each_side_and_clips():
    assert grow_box((100, 100, 300, 200), 400, 300) == (90, 95, 310, 205)
    assert grow_box((0, 0, 400, 300), 400, 300) == (0, 0, 400, 300)


def test_score_ranks_grabcut_above_the_rectangle(testset, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "sam2")
    result = score(testset, names=("stub", "grabcut"))
    assert result["mean_iou"]["grabcut"] >= 0.9 > result["mean_iou"]["stub"]
    assert result["pages"][0]["name"] == "ball"
    assert set(result["pages"][0]["seconds"]) == {"stub", "grabcut"}
    assert json.load(open(testset / "results.json"))["mean_iou"] == result["mean_iou"]
    assert os.environ["SEGMENTER"] == "sam2"            # the caller's setting is put back


def test_score_saves_masks_when_asked(testset, tmp_path):
    out = tmp_path / "masks"
    score(testset, names=("grabcut",), save_masks=out)
    saved = cv2.imread(str(out / "ball_grabcut.png"), cv2.IMREAD_GRAYSCALE)
    assert saved.shape == (300, 400)


@pytest.mark.parametrize("damage", ["missing", "empty", "wrong_size"])
def test_bad_hand_mask_is_reported_by_page_name(testset, damage):
    path = testset / "ball_mask.png"
    if damage == "missing":
        path.unlink()
    elif damage == "empty":
        cv2.imwrite(str(path), np.zeros((300, 400), np.uint8))
    else:
        cv2.imwrite(str(path), np.full((30, 40), 255, np.uint8))
    with pytest.raises(ValueError, match="ball"):
        load_testset(testset)
