import json

import cv2
import numpy as np
import pytest

from cutout_model.evaluate import load_testset, score
from cutout_model.make_testset import make_testset


def test_pages_and_masks_load_as_a_testset(art, tmp_path):
    fg, bg = art
    out = tmp_path / "testset"
    rows = make_testset(fg, bg, out, count=6, canvas=256)
    assert len(rows) == 6
    pages = load_testset(out)
    assert [name for name, _, _ in pages] == [f"anime_{i:03d}" for i in range(6)]
    for _, image, mask in pages:
        assert image.shape == (256, 256, 3) and mask.shape == (256, 256)
        assert 0.02 <= (mask > 0).mean() <= 0.6


def test_mask_is_the_pasted_subject(art, tmp_path):
    fg, bg = art
    out = tmp_path / "testset"
    make_testset(fg, bg, out, count=4, canvas=256)
    for _, image, mask in load_testset(out):
        inside = image[mask > 0]
        assert (inside[:, 0] > 200).mean() > 0.9          # red disc under the mask
        assert (image[mask == 0][:, 2] > 200).mean() > 0.5  # mostly blue background elsewhere


def test_same_seed_same_pages(art, tmp_path):
    fg, bg = art
    make_testset(fg, bg, tmp_path / "a", count=3, seed=7, canvas=256)
    make_testset(fg, bg, tmp_path / "b", count=3, seed=7, canvas=256)
    for name in ("anime_000.png", "anime_002_mask.png"):
        a = cv2.imread(str(tmp_path / "a" / name))
        b = cv2.imread(str(tmp_path / "b" / name))
        assert np.array_equal(a, b)


def test_manifest_names_the_sources(art, tmp_path):
    fg, bg = art
    out = tmp_path / "testset"
    make_testset(fg, bg, out, count=2, canvas=256)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["count"] == 2 and len(manifest["pages"]) == 2
    assert manifest["pages"][0]["subject"] == manifest["pages"][0]["cutouts"][-1]


def test_grabcut_scores_on_it(art, tmp_path):
    fg, bg = art
    out = tmp_path / "testset"
    make_testset(fg, bg, out, count=2, canvas=256)
    result = score(out, names=("grabcut",))
    assert result["mean_iou"]["grabcut"] > 0.5


def test_missing_folder_or_no_images_is_an_error(art, tmp_path):
    fg, bg = art
    with pytest.raises(FileNotFoundError):
        make_testset(tmp_path / "nowhere", bg, tmp_path / "out", count=1)
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        make_testset(fg, tmp_path / "empty", tmp_path / "out", count=1)
