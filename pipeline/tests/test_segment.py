import cv2
import numpy as np
import pytest

from pipeline.masks import iou
from pipeline.segment import point_box, segment
from pipeline.tests.conftest import ELLIPSE_CENTER, ELLIPSE_RADII, PAGE_SIZE


@pytest.fixture
def image(page_image):
    return cv2.cvtColor(cv2.imread(page_image), cv2.COLOR_BGR2RGB)


@pytest.fixture
def ellipse():
    mask = np.zeros((PAGE_SIZE[1], PAGE_SIZE[0]), np.uint8)
    cv2.ellipse(mask, ELLIPSE_CENTER, ELLIPSE_RADII, 0, 0, 360, 255, -1)
    return mask


def test_stub_fills_box(image, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "stub")
    mask = segment(image, box=(100, 100, 300, 200))
    expected = np.zeros((900, 1200), np.uint8)
    expected[100:200, 100:300] = 255
    assert np.array_equal(mask, expected)


def test_stub_point_uses_point_box(image, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "stub")
    mask = segment(image, points=[(600, 450)])
    x0, y0, x1, y1 = (int(v) for v in point_box(600, 450, 1200, 900))
    expected = np.zeros((900, 1200), np.uint8)
    expected[y0:y1, x0:x1] = 255
    assert np.array_equal(mask, expected)


def test_point_box_is_20_percent_of_longer_side_and_clipped():
    assert point_box(600, 450, 1200, 900) == (360, 210, 840, 690)
    assert point_box(10, 10, 1200, 900) == (0, 0, 250, 250)
    assert point_box(1190, 890, 1200, 900) == (950, 650, 1200, 900)


def test_grabcut_finds_ellipse_from_box(image, ellipse, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "grabcut")
    mask = segment(image, box=(350, 250, 850, 650))
    assert iou(mask, ellipse) >= 0.9


def test_grabcut_from_point(image, ellipse, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "grabcut")
    mask = segment(image, points=[(600, 450)])
    assert mask[450, 600] == 255
    assert iou(mask, ellipse) >= 0.8


def test_grabcut_degenerate_box_returns_empty_mask(image, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "grabcut")
    mask = segment(image, box=(500, 500, 500, 500))
    assert mask.shape == (900, 1200)
    assert not mask.any()


def test_default_is_grabcut(image, ellipse, monkeypatch):
    monkeypatch.delenv("SEGMENTER", raising=False)
    assert iou(segment(image, box=(350, 250, 850, 650)), ellipse) >= 0.9
    monkeypatch.setenv("SEGMENTER", "")
    assert iou(segment(image, box=(350, 250, 850, 650)), ellipse) >= 0.9


def test_unknown_segmenter_raises(image, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "magic")
    with pytest.raises(ValueError):
        segment(image, box=(100, 100, 300, 200))


@pytest.mark.parametrize("name", ["edgesam", "sam2"])
def test_edgesam_and_sam2_raise_not_implemented(image, monkeypatch, name):
    monkeypatch.setenv("SEGMENTER", name)
    with pytest.raises(NotImplementedError) as error:
        segment(image, box=(100, 100, 300, 200))
    assert str(error.value) == "Bryan: PyTorch segmenter goes here"


def test_needs_a_box_or_points(image):
    with pytest.raises(ValueError):
        segment(image)


@pytest.mark.parametrize("name", ["stub", "grabcut"])
def test_output_shape_and_values(image, monkeypatch, name):
    monkeypatch.setenv("SEGMENTER", name)
    mask = segment(image, box=(350, 250, 850, 650))
    assert mask.shape == image.shape[:2]
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)) <= {0, 255}
