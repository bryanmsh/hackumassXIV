import cv2
import numpy as np
import pytest

from pipeline import cascade
from pipeline.masks import iou
from pipeline.segment import segment
from pipeline.tests.conftest import ELLIPSE_CENTER, ELLIPSE_RADII, PAGE_SIZE

W, H = PAGE_SIZE
BOX = (400, 300, 800, 600)  # tight around the conftest ellipse


@pytest.fixture
def image(page_image):
    return cv2.cvtColor(cv2.imread(page_image), cv2.COLOR_BGR2RGB)


@pytest.fixture
def ellipse():
    mask = np.zeros((H, W), np.uint8)
    cv2.ellipse(mask, ELLIPSE_CENTER, ELLIPSE_RADII, 0, 0, 360, 255, -1)
    return mask


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("SEGMENTER", "cascade")
    monkeypatch.setenv("CASCADE_FALLBACK", "stub")  # a filled rectangle: easy to tell apart from ours
    monkeypatch.setenv("CASCADE_FLIP", "0")
    monkeypatch.delenv("CASCADE_MIN_CONFIDENCE", raising=False)
    monkeypatch.delenv("CUTOUT_MODEL", raising=False)
    cascade.route_counts.clear()


def fake_model(monkeypatch, prob):
    monkeypatch.setattr(cascade, "ours_probability", lambda image, box: prob.copy())


def box_model(monkeypatch, shift_x, radii):
    """A fake model that, like a real one, answers relative to the box on whatever image it is
    given: an ellipse at the box centre moved `shift_x` box widths right, radii in box sizes."""
    def predict(image, box):
        x0, x1 = sorted((box[0], box[2]))
        y0, y1 = sorted((box[1], box[3]))
        w, h = x1 - x0, y1 - y0
        prob = np.zeros(image.shape[:2], np.uint8)
        centre = (int(round((x0 + x1) / 2 + shift_x * w)), int(round((y0 + y1) / 2)))
        cv2.ellipse(prob, centre, (int(round(radii[0] * w)), int(round(radii[1] * h))), 0, 0, 360, 255, -1)
        return as_prob(prob)
    monkeypatch.setattr(cascade, "ours_probability", predict)


def as_prob(mask, sure=1.0):
    """A probability map from a 0/255 mask: `sure` inside, 1 - `sure` outside."""
    return np.where(mask > 0, sure, 1 - sure).astype(np.float32)


def stub_mask():
    mask = np.zeros((H, W), np.uint8)
    mask[300:600, 400:800] = 255
    return mask


def test_a_sure_answer_is_ours(image, ellipse, monkeypatch):
    fake_model(monkeypatch, as_prob(ellipse, 0.98))
    mask = segment(image, box=BOX)
    assert np.array_equal(mask, ellipse)
    route = cascade.last_route()
    assert route["model"] == "mirai" and route["reason"] == "sure" and route["confidence"] >= 0.9
    assert cascade.route_counts[("mirai", "sure")] == 1


def test_an_undecided_outline_goes_to_the_fallback(image, ellipse, monkeypatch):
    fake_model(monkeypatch, as_prob(ellipse, 0.6))  # right shape, but barely over a coin toss
    assert np.array_equal(segment(image, box=BOX), stub_mask())
    assert cascade.last_route()["model"] == "stub" and cascade.last_route()["reason"] == "unsure: sure"


def test_a_speck_goes_to_the_fallback(image, monkeypatch):
    speck = np.zeros((H, W), np.uint8)
    cv2.circle(speck, (600, 450), 8, 255, -1)
    fake_model(monkeypatch, as_prob(speck))
    segment(image, box=BOX)
    assert cascade.last_route()["reason"] == "unsure: fill"


def test_the_whole_box_goes_to_the_fallback(image, monkeypatch):
    fake_model(monkeypatch, as_prob(stub_mask()))
    segment(image, box=BOX)
    route = cascade.last_route()
    assert route["model"] == "stub" and route["parts"]["border"] == 0.0 and route["parts"]["fill"] == 0.0


def test_two_equal_pieces_go_to_the_fallback(image, monkeypatch):
    halves = np.zeros((H, W), np.uint8)
    cv2.circle(halves, (500, 450), 80, 255, -1)
    cv2.circle(halves, (700, 450), 80, 255, -1)
    fake_model(monkeypatch, as_prob(halves))
    segment(image, box=BOX)
    route = cascade.last_route()
    assert route["reason"] == "unsure: pieces" and route["parts"]["pieces"] == 0.5


def test_disagreeing_with_the_mirrored_page_goes_to_the_fallback(image, monkeypatch):
    monkeypatch.setenv("CASCADE_FLIP", "1")
    # left of centre on the page and, mirrored, left of centre again: back on the page it lands on the right
    box_model(monkeypatch, -0.2, (0.275, 0.4667))
    segment(image, box=BOX)
    route = cascade.last_route()
    assert route["reason"] == "unsure: flip" and route["parts"]["flip"] == 0.0


def test_a_symmetric_answer_passes_the_flip_check(image, ellipse, monkeypatch):
    monkeypatch.setenv("CASCADE_FLIP", "1")
    box_model(monkeypatch, 0.0, (0.5, 0.5))  # the conftest ellipse: centred, filling the box
    segment(image, box=BOX)
    assert cascade.last_route()["parts"]["flip"] > 0.95  # an ellipse on pixel 600 mirrors to pixel 599


def test_the_threshold_is_a_setting(image, ellipse, monkeypatch):
    fake_model(monkeypatch, as_prob(ellipse, 0.8))
    score = cascade.mask_confidence(as_prob(ellipse, 0.8), BOX)[0]
    monkeypatch.setenv("CASCADE_MIN_CONFIDENCE", str(score - 0.01))
    segment(image, box=BOX)
    assert cascade.last_route()["model"] == "mirai"
    monkeypatch.setenv("CASCADE_MIN_CONFIDENCE", str(score + 0.01))
    segment(image, box=BOX)
    assert cascade.last_route()["model"] == "stub"


@pytest.mark.parametrize("error", [ImportError("no cutout_model"), FileNotFoundError("cutout.pt")])
def test_a_missing_model_uses_the_fallback(image, monkeypatch, error):
    def broken(image, box):
        raise error
    monkeypatch.setattr(cascade, "ours_probability", broken)
    assert np.array_equal(segment(image, box=BOX), stub_mask())
    assert cascade.last_route()["reason"] == f"our model unavailable: {type(error).__name__}"


def test_this_branch_has_no_cutout_model_and_still_cuts(image, monkeypatch):
    # With no stand-in set, the real import runs. Where cutout_model/ exists this needs its weights.
    monkeypatch.setenv("CUTOUT_WEIGHTS", "does-not-exist.pt")
    mask = segment(image, box=BOX)
    assert mask.shape == (H, W) and cascade.last_route()["model"] == "stub"


def test_a_click_always_goes_to_the_fallback(image, ellipse, monkeypatch):
    fake_model(monkeypatch, as_prob(ellipse))
    segment(image, points=[(600, 450)])
    assert cascade.last_route() | {"seconds": 0} == {"model": "stub", "reason": "click", "seconds": 0}


def test_mirai_alone_uses_ours_and_raises_when_missing(image, ellipse, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "mirai")
    fake_model(monkeypatch, as_prob(ellipse, 0.55))  # unsure, but there is nothing behind it
    assert np.array_equal(segment(image, box=BOX), ellipse)

    def missing(image, box):
        raise FileNotFoundError("cut-out model weights not found: cutout.pt")
    monkeypatch.setattr(cascade, "ours_probability", missing)
    with pytest.raises(FileNotFoundError):
        segment(image, box=BOX)


@pytest.mark.parametrize("name", ["cascade", "mirai", "nonsense"])
def test_the_fallback_cannot_be_the_cascade_itself(image, ellipse, monkeypatch, name):
    monkeypatch.setenv("CASCADE_FALLBACK", name)
    fake_model(monkeypatch, as_prob(ellipse, 0.55))
    with pytest.raises(ValueError):
        segment(image, box=BOX)


def test_a_zero_or_255_mask_counts_as_sure_on_the_outline(ellipse):
    score, parts = cascade.mask_confidence(ellipse.astype(np.float32) / 255, BOX)
    assert parts["sure"] == 1.0 and score > 0.9


@pytest.mark.parametrize("box", [(500, 500, 500, 500), (2000, 2000, 2100, 2100)])
def test_an_empty_or_offpage_box_scores_zero(ellipse, box):
    assert cascade.mask_confidence(ellipse.astype(np.float32) / 255, box)[0] == 0.0


def test_the_standin_cuts_the_ellipse_and_is_sure(image, ellipse, monkeypatch):
    monkeypatch.setenv("CUTOUT_MODEL", "standin")
    monkeypatch.setenv("CASCADE_FLIP", "1")
    mask = segment(image, box=(390, 290, 810, 610))
    assert iou(mask, ellipse) > 0.9
    assert cascade.last_route()["model"] == "mirai"


def test_the_real_cutout_model_package_plugs_in(image, tmp_path, monkeypatch):
    """Runs only where cutout_model/ is present: its predict_prob reaches the cascade."""
    torch = pytest.importorskip("torch")
    pytest.importorskip("cutout_model.predict")
    from cutout_model import predict
    from cutout_model.model import UNet
    from cutout_model.train import save_checkpoint

    model = UNet()
    with torch.no_grad():
        model.head.weight.zero_()
        model.head.bias.fill_(10.0)  # every pixel in the crop window is subject
    save_checkpoint(tmp_path / "all.pt", model, input_size=64, margin=0.25, epoch=0, val_iou=0.0)
    monkeypatch.setenv("CUTOUT_WEIGHTS", str(tmp_path / "all.pt"))
    predict._loaded.clear()
    prob = cascade.ours_probability(image, BOX)
    assert prob.dtype == np.float32 and prob.shape == (H, W) and 0.0 < prob.mean() < 1.0
    segment(image, box=BOX)
    # The whole crop window is "subject", which is the background inside the box: SAM's job.
    assert cascade.last_route()["model"] == "stub" and cascade.last_route()["parts"]["border"] == 0.0


def _window_only_model(image, box):
    """A stand-in that, like our model, looks only at the box grown by 0.25 on each side."""
    height, width = image.shape[:2]
    x0, x1 = sorted((float(box[0]), float(box[2])))
    y0, y1 = sorted((float(box[1]), float(box[3])))
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(width), x1), min(float(height), y1)
    prob = np.zeros((height, width), np.float32)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return prob
    dx, dy = (x1 - x0) * 0.25, (y1 - y0) * 0.25
    wx0, wy0 = max(0, int(round(x0 - dx))), max(0, int(round(y0 - dy)))
    wx1, wy1 = min(width, int(round(x1 + dx))), min(height, int(round(y1 + dy)))
    window = image[wy0:wy1, wx0:wx1].astype(np.float32)
    # depends on position inside the window, so a wrong offset or a missing mirror shows up
    ramp = np.linspace(0.0, 1.0, wx1 - wx0, dtype=np.float32)[None, :]
    prob[wy0:wy1, wx0:wx1] = (window[..., 0] / 255.0) * ramp
    return prob


def _flipped_whole_page(image, box):
    width = image.shape[1]
    mirrored = (width - box[2], box[1], width - box[0], box[3])
    return cascade.ours_probability(np.ascontiguousarray(image[:, ::-1]), mirrored)[:, ::-1]


@pytest.mark.parametrize("box", [BOX, (0, 0, 300, 200), (W - 250, H - 180, W, H), (-40, 100, 200, 400),
                                 (W - 100, 50, W + 60, 260), (500, 500, 500, 500)])
def test_flip_check_on_a_crop_matches_mirroring_the_whole_page(image, monkeypatch, box):
    rng = np.random.default_rng(0)
    noisy = rng.integers(0, 256, image.shape, dtype=np.uint8)  # every pixel different, so offsets matter
    monkeypatch.setattr(cascade, "ours_probability", _window_only_model)
    np.testing.assert_allclose(cascade._flipped_probability(noisy, box), _flipped_whole_page(noisy, box), atol=1e-6)


def test_flip_check_on_a_crop_matches_with_the_real_model(image, monkeypatch):
    pytest.importorskip("torch")
    predict = pytest.importorskip("cutout_model.predict")
    import os
    if not os.path.exists(predict.weights_path()):
        pytest.skip("no cutout_model weights here")
    for box in (BOX, (0, 0, 300, 200), (W - 250, H - 180, W, H)):
        crop = cascade._flipped_probability(image, box) > 0.5
        whole = _flipped_whole_page(image, box) > 0.5
        assert iou(crop.astype(np.uint8) * 255, whole.astype(np.uint8) * 255) > 0.999
