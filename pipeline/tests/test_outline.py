import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from contracts.hashing import hash_bytes
from pipeline import mask_from_outline
from pipeline.masks import polygon_mask

TRIANGLE = [(300, 200), (900, 250), (600, 700)]


def read_mask(candidate):
    return cv2.imread(candidate.mask_path, cv2.IMREAD_UNCHANGED)


def test_polygon_used_exactly(page_image, tmp_path):
    candidate = mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path)
    assert np.array_equal(read_mask(candidate), polygon_mask(TRIANGLE, 1200, 900))
    assert candidate.source == "manual"
    assert candidate.confidence == 1.0
    assert candidate.label == "rabbit"
    assert candidate.synonyms == []
    assert candidate.box == (300, 200, 900, 700)
    assert Path(candidate.mask_path).parent == tmp_path / "masks"
    assert candidate.mask_hash == hash_bytes(Path(candidate.mask_path).read_bytes())


def test_points_may_be_lists(page_image, tmp_path):
    candidate = mask_from_outline(page_image, "rabbit", [list(p) for p in TRIANGLE], tmp_path)
    assert np.array_equal(read_mask(candidate), polygon_mask(TRIANGLE, 1200, 900))


def test_box_is_clipped_to_the_page(page_image, tmp_path):
    points = [(-100, -50), (400, -50), (400, 1000), (-100, 1000)]
    candidate = mask_from_outline(page_image, "tree", points, tmp_path)
    assert candidate.box == (0, 0, 400, 900)
    assert read_mask(candidate).shape == (900, 1200)


def test_fewer_than_three_points_raises_value_error(page_image, tmp_path):
    with pytest.raises(ValueError):
        mask_from_outline(page_image, "rabbit", [(1, 1), (5, 5)], tmp_path)


def test_works_with_gemini_and_segmenter_off(page_image, tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("SEGMENTER", "edgesam")
    import pipeline.segment

    def no_model(*args, **kwargs):
        raise AssertionError("the raw outline must not call the segmenter")

    monkeypatch.setattr(pipeline.segment, "segment", no_model)
    candidate = mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path)
    assert np.array_equal(read_mask(candidate), polygon_mask(TRIANGLE, 1200, 900))


def test_importing_the_pipeline_does_not_load_the_gemini_sdk():
    code = "import sys, pipeline, pipeline.outline; sys.exit(1 if 'google.genai' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parents[2])
    assert result.returncode == 0


def test_outline_entirely_off_the_page_raises_value_error(page_image, tmp_path):
    with pytest.raises(ValueError):
        mask_from_outline(page_image, "rabbit", [(2000, 2000), (2100, 2000), (2050, 2100)], tmp_path)
    assert not (tmp_path / "masks").exists()


# --- tidy=True (P1): the segmenter may tighten the outline ---

def patch_segmenter(monkeypatch, result, calls=None):
    import pipeline.segment

    def fake(image, box=None, points=None):
        if calls is not None:
            calls.append({"shape": image.shape, "box": box, "points": points})
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(pipeline.segment, "segment", fake)


def test_tidy_uses_segmenter_when_iou_high(page_image, tmp_path, monkeypatch):
    from pipeline.masks import clean_mask

    polygon = polygon_mask(TRIANGLE, 1200, 900)
    shifted = polygon_mask([(x + 5, y + 5) for x, y in TRIANGLE], 1200, 900)
    patch_segmenter(monkeypatch, shifted)
    candidate = mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True)
    grown = np.zeros_like(polygon)
    grown[125:775, 210:990] = 255
    expected = clean_mask(cv2.bitwise_and(shifted, grown))
    result = read_mask(candidate)
    assert np.array_equal(result, expected)
    assert not np.array_equal(result, polygon)
    assert (candidate.source, candidate.confidence, candidate.label) == ("manual", 1.0, "rabbit")


def test_tidy_result_never_leaves_the_grown_box(page_image, tmp_path, monkeypatch):
    polygon = polygon_mask(TRIANGLE, 1200, 900)
    spilled = polygon.copy()
    spilled[200:700, 300:1000] = 255  # still overlaps well, but spills far to the right
    spilled[0:40, 0:40] = 255
    patch_segmenter(monkeypatch, spilled)
    result = read_mask(mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True))
    grown = np.zeros_like(polygon)
    grown[125:775, 210:990] = 255
    assert not (result & ~grown).any()


@pytest.mark.parametrize("overlap, used", [(0.2, False), (0.4, True)])
def test_tidy_keeps_polygon_when_iou_low(page_image, tmp_path, monkeypatch, overlap, used):
    from pipeline.masks import iou

    square = [(300, 200), (799, 200), (799, 699), (300, 699)]
    polygon = polygon_mask(square, 1200, 900)
    found = np.zeros_like(polygon)
    found[200:700, 300:300 + int(500 * overlap)] = 255
    assert iou(found, polygon) == pytest.approx(overlap)
    patch_segmenter(monkeypatch, found)
    candidate = mask_from_outline(page_image, "rabbit", square, tmp_path, tidy=True)
    assert np.array_equal(read_mask(candidate), found if used else polygon)


def test_tidy_keeps_region_ten_percent_outside_outline(page_image, tmp_path, monkeypatch):
    square = [(300, 200), (900, 200), (900, 700), (300, 700)]
    found = polygon_mask(square, 1200, 900)
    found[200:701, 901:961] = 255
    patch_segmenter(monkeypatch, found)
    result = read_mask(mask_from_outline(page_image, "rabbit", square, tmp_path, tidy=True))
    assert np.array_equal(result, found)
    assert result[400, 960] == 255


def test_tidy_keeps_polygon_when_segmenter_raises(page_image, tmp_path, monkeypatch):
    patch_segmenter(monkeypatch, NotImplementedError("Bryan: PyTorch segmenter goes here"))
    candidate = mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True)
    assert np.array_equal(read_mask(candidate), polygon_mask(TRIANGLE, 1200, 900))


def test_tidy_box_is_polygon_bounding_box(page_image, tmp_path, monkeypatch):
    calls = []
    patch_segmenter(monkeypatch, polygon_mask(TRIANGLE, 1200, 900), calls)
    candidate = mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True)
    assert len(calls) == 1
    assert calls[0]["shape"] == (900, 1200, 3)
    assert calls[0]["box"] == (300, 200, 900, 700)
    assert candidate.box == (300, 200, 901, 701)  # the tidied mask's own box; edge pixels are inclusive


def test_tidy_prompts_with_box_and_interior_positive_points(page_image, tmp_path, monkeypatch):
    calls = []
    polygon = polygon_mask(TRIANGLE, 1200, 900)
    patch_segmenter(monkeypatch, polygon, calls)
    mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True)
    assert len(calls) == 1
    assert calls[0]["box"] == (300, 200, 900, 700)
    points = calls[0]["points"]
    assert 2 <= len(points) <= 5
    moments = cv2.moments(polygon, binaryImage=True)
    assert points[0] == (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"], 1)
    distance = cv2.distanceTransform(polygon, cv2.DIST_L2, 5)
    for x, y, label in points:
        assert label == 1
        assert distance[round(y), round(x)] > 1


def test_tidy_box_follows_the_tightened_mask(page_image, tmp_path, monkeypatch):
    square = [(300, 200), (900, 200), (900, 700), (300, 700)]
    tight = polygon_mask(square, 1200, 900)
    tight[:, 850:] = 0  # the segmenter trims the right edge
    patch_segmenter(monkeypatch, tight)
    candidate = mask_from_outline(page_image, "rabbit", square, tmp_path, tidy=True)
    assert candidate.box == (300, 200, 850, 701)  # fillPoly includes the bottom edge row


def test_tidy_keeps_polygon_when_cleanup_raises(page_image, tmp_path, monkeypatch):
    import pipeline.outline

    polygon = polygon_mask(TRIANGLE, 1200, 900)
    patch_segmenter(monkeypatch, polygon)

    def broken_cleanup(mask):
        raise ValueError("cleanup failed")

    monkeypatch.setattr(pipeline.outline, "clean_mask", broken_cleanup)
    result = read_mask(mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True))
    assert np.array_equal(result, polygon)


def test_tidy_keeps_polygon_when_cleanup_empty(page_image, tmp_path, monkeypatch):
    import pipeline.outline

    polygon = polygon_mask(TRIANGLE, 1200, 900)
    patch_segmenter(monkeypatch, polygon)
    monkeypatch.setattr(pipeline.outline, "clean_mask", lambda mask: np.zeros_like(mask))
    result = read_mask(mask_from_outline(page_image, "rabbit", TRIANGLE, tmp_path, tidy=True))
    assert np.array_equal(result, polygon)
