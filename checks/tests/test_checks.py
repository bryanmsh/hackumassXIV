from pathlib import Path

import cv2
import numpy as np
import pytest

from checks import run_checks, second_look, swatch_contrast
from checks.second_look import matches, singular

SAMPLES = Path(__file__).resolve().parents[2] / "render" / "samples"
P1 = (SAMPLES / "1.png", SAMPLES / "1_view.png", SAMPLES / "1_mask.png")
P2 = (SAMPLES / "2.png", SAMPLES / "2_view.png", SAMPLES / "2_mask.png")
TEXT = "A little red bird sat on the branch and sang."


def write_png(path: Path, img):
    ok, buf = cv2.imencode(".png", img)
    assert ok
    buf.tofile(str(path))
    return path


@pytest.mark.parametrize("page", [P1, P2], ids=["bird", "rabbit"])
@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_good_masks_pass(page, level):
    r = run_checks(*page, {"colors": ["#FDD835"], "background": "#000000", "text_mode": "below"}, level, TEXT)
    assert r.fidelity.status == "pass"
    assert r.page_edge.status == "pass"
    if level == 4:
        assert r.background is None
    else:
        assert r.background.status == "pass", r.background.detail
    assert r.text_contrast.status == "pass"
    assert r.size.status == "pass", r.size.detail


def test_scattered_mask_fails_fidelity():
    r = run_checks(P1[0], P1[1], SAMPLES / "bad_scattered_mask.png", {}, 2, None)
    assert r.fidelity.status == "fail"
    assert "pieces" in r.fidelity.detail


def test_huge_mask_fails_fidelity_and_touches_edge():
    r = run_checks(P1[0], P1[1], SAMPLES / "bad_huge_mask.png", {}, 2, None)
    assert r.fidelity.status == "fail"
    assert r.page_edge.status == "warn"
    assert "top" in r.page_edge.detail and "left" in r.page_edge.detail


def test_small_subject_passes_fidelity_but_warns_on_enlargement(tmp_path):
    mask = np.zeros((1800, 2400), np.uint8)
    cv2.circle(mask, (1200, 900), 60, 255, -1)  # about 0.26% of the page, like a frog in Animal Homes
    path = write_png(tmp_path / "small.png", mask)
    r = run_checks(P1[0], P1[1], path, {"size": "large"}, 2, None)
    assert r.fidelity.status == "pass"
    assert r.size.status == "warn" and r.size.value > 2.5
    r3 = run_checks(P1[0], P1[1], path, {}, 3, None)
    assert r3.size.status == "warn" and r3.size.value < 0.15


def test_speck_fails_fidelity(tmp_path):
    mask = np.zeros((1800, 2400), np.uint8)
    cv2.circle(mask, (1200, 900), 20, 255, -1)  # about 0.03% of the page
    path = write_png(tmp_path / "speck.png", mask)
    r = run_checks(P1[0], P1[1], path, {}, 2, None)
    assert r.fidelity.status == "fail" and "at least 0.1%" in r.fidelity.detail


def test_low_contrast_subject_warns():
    dark = run_checks(*P2, {"background": "#000000"}, 2, None)
    light = run_checks(*P2, {"background": "#8D6E63"}, 2, None)
    assert light.contrast.value < dark.contrast.value
    assert light.contrast.status == "warn"


def test_tinted_contrast_follows_the_swatch():
    yellow = run_checks(*P1, {"colors": ["#FDD835"], "background": "#000000"}, 1, None)
    navy = run_checks(*P1, {"colors": ["#1E88E5"], "background": "#001F3F"}, 1, None)
    assert yellow.contrast.status == "pass"
    assert navy.contrast.value < yellow.contrast.value


def test_faded_page_meets_half_target_and_outlined_is_not_checked():
    r3 = run_checks(*P1, {}, 3, None)
    assert r3.background.status == "pass" and "of the original" in r3.background.detail
    r4 = run_checks(*P1, {}, 4, None)
    assert r4.background is None


def test_text_contrast_is_absent_when_text_is_off():
    assert run_checks(*P1, {"text_mode": "off"}, 2, TEXT).text_contrast is None
    assert run_checks(*P1, {"text_mode": "below"}, 2, "").text_contrast is None


def test_results_are_the_shared_contract_types():
    from contracts.types import CheckResult, SecondLook
    assert isinstance(run_checks(*P1, {}, 2, None), CheckResult)
    assert isinstance(second_look(P1[0], P1[2], "bird", [], ask=lambda png: "bird"), SecondLook)


def test_accepts_contract_settings():
    from contracts.types import Settings
    r = run_checks(*P1, Settings(colors=["#fdd835"], text_mode="below"), 2, TEXT)
    assert r.text_contrast.status == "pass"


def test_never_raises_on_missing_files(tmp_path):
    r = run_checks(tmp_path / "nope.png", tmp_path / "nope.png", tmp_path / "nope_mask.png", {}, 2, None)
    for name in ("fidelity", "page_edge", "background", "contrast", "size", "text_contrast"):
        assert getattr(r, name).status == "fail"
    r = run_checks(tmp_path / "nope.png", tmp_path / "nope.png", P1[2], {}, 2, None)
    assert r.fidelity.status == "pass" and r.background.status == "fail"


def test_swatch_contrast():
    assert swatch_contrast("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert swatch_contrast("#E53935", "#000000") > 3
    assert swatch_contrast("#FDD835", "#FFFFFF") < 3


def test_singular_and_matching():
    assert singular("birds") == "bird" and singular("bunnies") == "bunny"
    assert singular("foxes") == "fox" and singular("grass") == "grass"
    assert matches("Bird", "hornbill", ["bird", "animal"])
    assert matches("two rabbits", "rabbit", [])
    assert not matches("tree", "rabbit", ["bunny"])


def test_second_look_pass_warn_and_failure():
    seen = []

    def ask(png):
        seen.append(png[:8])
        return "Red birds"

    ok = second_look(P1[0], P1[2], "robin", ["bird"], ask=ask)
    assert ok.status == "pass" and ok.answer == "Red birds"
    assert seen == [b"\x89PNG\r\n\x1a\n"]
    miss = second_look(P1[0], P1[2], "rabbit", ["bunny"], ask=lambda png: "tomato")
    assert miss.status == "warn" and "tomato" in miss.detail

    def boom(png):
        raise TimeoutError("20 s")

    failed = second_look(P1[0], P1[2], "bird", [], ask=boom)
    assert failed.status == "warn" and "TimeoutError" in failed.detail


def test_second_look_without_key_is_a_warning(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = second_look(P1[0], P1[2], "bird", [])
    assert r.status == "warn" and "GEMINI_API_KEY" in r.detail
