"""PyTorch segmenter tests. The click-choice rule runs everywhere; the real models run
only with RUN_TORCH=1, because they need torch and download about 200 MB of weights."""
import cv2
import numpy as np
import pytest

from pipeline.masks import iou
from pipeline.sam import MAX_CLICK_COVER, box_border_cover, pick_click_mask
from pipeline.tests.conftest import ELLIPSE_CENTER, ELLIPSE_RADII, PAGE_SIZE


def _masks(*covers, size=100):
    out = np.zeros((len(covers), size, size), bool)
    for i, cover in enumerate(covers):
        out[i].flat[: int(cover * size * size)] = True
    return out


def test_click_picks_the_largest_mask():
    masks = _masks(0.01, 0.05, 0.03)  # part, whole, sub-part
    assert pick_click_mask(masks).mean() == pytest.approx(0.05)


def test_click_skips_masks_that_are_mostly_page():
    masks = _masks(0.02, 0.04, MAX_CLICK_COVER + 0.1)
    assert pick_click_mask(masks).mean() == pytest.approx(0.04)


def test_click_falls_back_to_smallest_when_all_are_background():
    masks = _masks(0.7, 0.8, 0.9)
    assert pick_click_mask(masks).mean() == pytest.approx(0.7)


def test_border_cover_is_low_for_a_subject_and_high_for_background(ellipse):
    box = (350, 250, 850, 650)  # the ellipse's own box, padded
    assert box_border_cover(ellipse, box) < 0.1
    background = np.zeros_like(ellipse)
    background[250:650, 350:850] = 255
    background[ellipse > 0] = 0
    assert box_border_cover(background, box) > 0.9


def test_low_confidence_falls_back_to_grabcut(image, ellipse, monkeypatch):
    import pipeline.sam as sam
    from pipeline.segment import segment

    def refuses(*args):
        raise sam.LowConfidence("scored its mask 0.19")

    monkeypatch.setattr(sam, "segment", refuses)
    monkeypatch.setenv("SEGMENTER", "sam2")
    mask = segment(image, box=(350, 250, 850, 650))
    assert iou(mask, ellipse) > 0.9  # GrabCut finds the ellipse
    assert sam.last_timing["fallback"] == "scored its mask 0.19"


@pytest.fixture
def image(page_image):
    return cv2.cvtColor(cv2.imread(page_image), cv2.COLOR_BGR2RGB)


@pytest.fixture
def ellipse():
    mask = np.zeros((PAGE_SIZE[1], PAGE_SIZE[0]), np.uint8)
    cv2.ellipse(mask, ELLIPSE_CENTER, ELLIPSE_RADII, 0, 0, 360, 255, -1)
    return mask


@pytest.mark.torch
@pytest.mark.parametrize("name", ["sam2", "edgetam"])
def test_real_model_box_and_click(image, ellipse, monkeypatch, tmp_path, name):
    from pipeline import sam
    from pipeline.segment import segment

    monkeypatch.setenv("SEGMENTER", name)
    box_mask = segment(image, box=(350, 250, 850, 650))
    assert box_mask.shape == image.shape[:2] and box_mask.dtype == np.uint8
    assert set(np.unique(box_mask)) <= {0, 255}
    assert iou(box_mask, ellipse) > 0.9

    click_mask = segment(image, points=[(600, 450)])
    assert sam.last_timing["encode"] == 0.0  # same page: the embedding came from the cache
    assert click_mask.shape == image.shape[:2] and click_mask.any()
    # A flat synthetic ellipse is a known weak spot for SAM, so click accuracy is measured on
    # real artwork in the trial (pipeline/README.md), not here.
