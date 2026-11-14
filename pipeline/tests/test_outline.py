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
