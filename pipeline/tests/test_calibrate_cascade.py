import json

import cv2
import numpy as np
import pytest

from pipeline import calibrate_cascade as cal


def row(confidence, iou_ours, iou_fallback, seconds_ours=0.1, seconds_fallback=1.0):
    return {"confidence": confidence, "iou_ours": iou_ours, "iou_fallback": iou_fallback,
            "seconds_ours": seconds_ours, "seconds_fallback": seconds_fallback}


ROWS = [row(0.9, 0.95, 0.95), row(0.8, 0.90, 0.93), row(0.3, 0.40, 0.90), row(0.1, 0.10, 0.85)]


def test_sweep_ends_all_ours_and_all_fallback():
    swept = {s["threshold"]: s for s in cal.sweep(ROWS)}
    assert swept[0.0]["share_ours"] == 1.0 and swept[0.0]["mean_iou"] == pytest.approx(0.5875)
    assert swept[1.0]["share_ours"] == 0.0 and swept[1.0]["mean_iou"] == pytest.approx(0.9075)
    assert swept[0.5] == {"threshold": 0.5, "share_ours": 0.5, "mean_iou": pytest.approx(0.9),
                          "mean_seconds": pytest.approx(0.6)}  # every page pays ours; two also pay the fallback


def test_recommend_keeps_the_most_pages_within_the_margin():
    swept = cal.sweep(ROWS)
    assert cal.recommend(ROWS, swept, margin=0.02)["share_ours"] == 0.5  # 0.900 >= 0.9075 - 0.02
    assert cal.recommend(ROWS, swept, margin=0.0)["share_ours"] == 0.25  # only the page where ours ties SAM


def test_recommend_breaks_ties_with_the_stricter_threshold():
    chosen = cal.recommend(ROWS, cal.sweep(ROWS), margin=0.02)
    assert chosen["threshold"] == 0.8  # 0.35 to 0.80 all keep the same two pages


def make_testset(folder, pages=4):
    folder.mkdir()
    for i in range(pages):
        image = np.full((480, 640, 3), 255, np.uint8)
        mask = np.zeros((480, 640), np.uint8)
        cv2.ellipse(mask, (320, 240), (90 + 20 * i, 70), 0, 0, 360, 255, -1)
        image[mask > 0] = (40, 160, 90)
        cv2.imwrite(str(folder / f"page_{i}.png"), image)
        cv2.imwrite(str(folder / f"page_{i}_mask.png"), mask)
    cv2.imwrite(str(folder / "lonely.png"), image)  # no mask: skipped, not fatal


def test_calibrate_end_to_end_with_the_standin(tmp_path, monkeypatch):
    monkeypatch.setenv("CUTOUT_MODEL", "standin")
    make_testset(tmp_path / "set")
    result = cal.calibrate(tmp_path / "set", tmp_path / "out", fallback="stub")
    assert result["pages"] == 4 and len(result["sweep"]) == len(cal.THRESHOLDS)
    assert result["ours_alone"]["mean_iou"] > 0.9 > result["fallback_alone"]["mean_iou"]  # a box vs an ellipse
    assert result["chosen"]["share_ours"] == 1.0
    saved = json.loads((tmp_path / "out" / "calibration.json").read_text())
    assert saved["chosen"] == result["chosen"]
    assert (tmp_path / "out" / "calibration.csv").read_text().startswith("threshold,share_ours,mean_iou,mean_seconds")
    assert (tmp_path / "out" / "calibration.svg").read_text(encoding="utf-8").startswith("<svg")


def test_an_empty_testset_is_an_error(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="no test pages"):
        cal.load_testset(tmp_path / "empty")
