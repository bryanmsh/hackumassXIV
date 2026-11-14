import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

import pipeline.click
import pipeline.segment
from contracts.hashing import hash_bytes
from pipeline import refine_mask, segment_at_point
from pipeline.gemini import GeminiError
from pipeline.masks import save_mask
from pipeline.segment import point_box


@pytest.fixture
def labeller(monkeypatch):
    """labeller(outcome): label_crop returns or raises `outcome`. labeller.crops holds what was sent."""
    crops = []

    def set_outcome(outcome):
        def fake(png_bytes):
            crops.append(png_bytes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        monkeypatch.setattr(pipeline.click, "label_crop", fake)

    set_outcome.crops = crops
    monkeypatch.setattr(pipeline.process.time, "sleep", lambda seconds: None)
    return set_outcome


def read_mask(candidate):
    return cv2.imread(candidate.mask_path, cv2.IMREAD_UNCHANGED)


def patch_segmenter(monkeypatch, result, calls=None):
    def fake(image, box=None, points=None):
        if calls is not None:
            calls.append({"box": box, "points": points})
        return result
    monkeypatch.setattr(pipeline.segment, "segment", fake)


# --- segment_at_point ---

def test_click_returns_mask_and_label(page_image, tmp_path, labeller, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "grabcut")
    labeller("ball")
    candidate = segment_at_point(page_image, 600, 450, tmp_path)
    assert (candidate.source, candidate.label, candidate.confidence, candidate.synonyms) == ("click", "ball", 1.0, [])
    mask = read_mask(candidate)
    assert mask.shape == (900, 1200)
    assert mask[450, 600] == 255
    assert mask[20, 20] == 0
    x0, y0, x1, y1 = candidate.box
    assert 380 <= x0 <= 420 and 780 <= x1 <= 820 and 280 <= y0 <= 320 and 580 <= y1 <= 620  # the ellipse
    path = Path(candidate.mask_path)
    assert path.parent == tmp_path / "masks" and path.name == f"1_{candidate.mask_hash}.png"
    assert candidate.mask_hash == hash_bytes(path.read_bytes())


def test_click_label_empty_when_gemini_fails(page_image, tmp_path, labeller, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "grabcut")
    labeller(GeminiError("down"))
    candidate = segment_at_point(page_image, 600, 450, tmp_path)
    assert candidate.label == ""
    assert candidate.source == "click"
    assert read_mask(candidate)[450, 600] == 255
    assert len(labeller.crops) == 2  # one retry, then give up


def test_click_label_empty_on_any_labelling_error(page_image, tmp_path, labeller, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "stub")
    labeller(RuntimeError("unexpected"))
    assert segment_at_point(page_image, 600, 450, tmp_path).label == ""


def test_click_on_background_falls_back_to_rectangle(page_image, tmp_path, labeller, monkeypatch):
    labeller("sky")
    patch_segmenter(monkeypatch, np.zeros((900, 1200), np.uint8))
    candidate = segment_at_point(page_image, 100, 100, tmp_path)
    x0, y0, x1, y1 = (int(v) for v in point_box(100, 100, 1200, 900))
    expected = np.zeros((900, 1200), np.uint8)
    expected[y0:y1, x0:x1] = 255
    assert np.array_equal(read_mask(candidate), expected)
    assert candidate.box == (x0, y0, x1, y1)


def test_segmenter_is_prompted_with_the_click_only(page_image, tmp_path, labeller, monkeypatch):
    labeller("ball")
    calls = []
    square = np.zeros((900, 1200), np.uint8)
    square[400:500, 550:650] = 255
    patch_segmenter(monkeypatch, square, calls)
    segment_at_point(page_image, 600, 450, tmp_path)
    assert calls == [{"box": None, "points": [(600, 450)]}]


def test_crop_sent_to_gemini_is_the_mask_box(page_image, tmp_path, labeller, monkeypatch):
    labeller("ball")
    square = np.zeros((900, 1200), np.uint8)
    square[300:500, 500:800] = 255  # box 300 wide, 200 tall: padding is 8% of 300 = 24 px
    patch_segmenter(monkeypatch, square)
    segment_at_point(page_image, 600, 400, tmp_path)
    crop = Image.open(io.BytesIO(labeller.crops[0]))
    assert crop.format == "PNG"
    assert crop.size == (348, 248)
    expected = Image.open(page_image).convert("RGB").crop((476, 276, 824, 524))
    assert np.array_equal(np.array(crop.convert("RGB")), np.array(expected))


def test_crop_padding_is_clipped_to_the_page(page_image, tmp_path, labeller, monkeypatch):
    labeller("corner")
    square = np.zeros((900, 1200), np.uint8)
    square[0:200, 0:300] = 255
    patch_segmenter(monkeypatch, square)
    segment_at_point(page_image, 50, 50, tmp_path)
    assert Image.open(io.BytesIO(labeller.crops[0])).size == (324, 224)


# --- refine_mask (P1) ---

@pytest.fixture
def left_half(page_image, tmp_path):
    """A saved mask of only the left half of the ellipse."""
    mask = np.zeros((900, 1200), np.uint8)
    cv2.ellipse(mask, (600, 450), (200, 150), 0, 0, 360, 255, -1)
    mask[:, 600:] = 0
    path, _ = save_mask(mask, page_image, tmp_path)
    return path


def test_refine_adds_region_and_keeps_old_file(page_image, tmp_path, left_half, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "grabcut")
    before = Path(left_half).read_bytes()
    candidate = refine_mask(page_image, left_half, 700, 450, tmp_path)
    assert candidate.mask_path != left_half
    assert Path(left_half).read_bytes() == before
    new, old = read_mask(candidate), cv2.imread(left_half, cv2.IMREAD_UNCHANGED)
    assert new[450, 700] == 255
    assert not (old & ~new).any()  # a refine click only adds
    assert (candidate.source, candidate.label, candidate.confidence) == ("click", "", 1.0)
    assert candidate.mask_hash == hash_bytes(Path(candidate.mask_path).read_bytes())


def test_refine_prompt_is_old_box_grown_to_the_point(page_image, tmp_path, left_half, monkeypatch):
    calls = []
    patch_segmenter(monkeypatch, np.zeros((900, 1200), np.uint8), calls)
    refine_mask(page_image, left_half, 700, 450, tmp_path)
    # old mask box is (400, 300, 600, 601); the click's 5% box is (640, 390, 760, 510)
    assert calls == [{"box": (400, 300, 760, 601), "points": [(700, 450)]}]


def test_refine_box_matches_the_new_mask(page_image, tmp_path, left_half, monkeypatch):
    added = np.zeros((900, 1200), np.uint8)
    added[400:500, 590:720] = 255
    patch_segmenter(monkeypatch, added)
    candidate = refine_mask(page_image, left_half, 700, 450, tmp_path)
    assert candidate.box == (400, 300, 720, 601)
    assert read_mask(candidate)[450, 700] == 255
