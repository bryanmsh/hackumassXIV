import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from render import RENDER_VERSION, SUBJECT_PALETTE, overlay, overlay_palette, render
from render.color import contrast_ratio, hex_to_rgb
from render.core import (CANVAS_LONG, compose, load_mask, load_rgb, resample,
                         subject_placement)

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
PAGES = [
    (SAMPLES / "1.png", SAMPLES / "1_view.png", SAMPLES / "1_mask.png"),
    (SAMPLES / "2.png", SAMPLES / "2_view.png", SAMPLES / "2_mask.png"),
]
TEXT = "The rabbit was hiding under the big tree."


def decode(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))


@pytest.mark.parametrize("page", PAGES, ids=["landscape", "portrait"])
@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_every_level_renders_at_canvas_size(page, level):
    master = load_rgb(page[0])
    out = decode(render(*page, {"text_mode": "below"}, level, TEXT))
    h, w = master.shape[:2]
    assert max(out.shape[:2]) == CANVAS_LONG
    assert abs(out.shape[1] / out.shape[0] - w / h) < 0.01


def test_webp_by_default_png_on_request():
    assert render(*PAGES[0], {}, 2)[:4] == b"RIFF"
    assert render(*PAGES[0], {}, 2, fmt="png")[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_is_repeatable():
    s = {"colors": ["#FDD835", "#1E88E5"], "outline": "thick", "text_mode": "below"}
    for level in (1, 2, 3, 4):
        assert render(*PAGES[1], s, level, TEXT) == render(*PAGES[1], s, level, TEXT)


@pytest.mark.parametrize("page", PAGES, ids=["landscape", "portrait"])
@pytest.mark.parametrize("size,position", [("medium", "center"), ("large", "left"), ("small", "lower")])
def test_source_fidelity_by_construction(page, size, position):
    """At level 2, every pixel in the mask core equals a resampled master pixel."""
    master, mask = load_rgb(page[0]), load_mask(page[2])
    settings = {"size": size, "position": position, "background": "#000000"}
    r = compose(*page, settings, 2)

    bx, by, bw, bh = cv2.boundingRect(mask)
    H, W = r.rgb.shape[:2]
    scale, nw, nh, left, top = subject_placement(bw, bh, W, H, size, position)
    expected = resample(master[by:by + bh, bx:bx + bw], nw, nh, scale)
    hard = r.subject[top:top + nh, left:left + nw]
    core = cv2.erode(hard.astype(np.uint8), np.ones((7, 7), np.uint8),
                     borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0
    assert core.sum() > 1000
    got = r.rgb[top:top + nh, left:left + nw]
    assert np.array_equal(got[core], expected[core])
    assert (r.rgb[~r.subject] == 0).all()


def test_size_and_position_follow_the_profile():
    W, H = 1600, 1200
    for size, frac in (("small", 0.4), ("medium", 0.6), ("large", 0.8)):
        scale, nw, nh, _, _ = subject_placement(500, 300, W, H, size, "center")
        assert max(nw, nh) == round(frac * H)
    _, nw, nh, left, top = subject_placement(500, 300, W, H, "medium", "left")
    assert abs((left + nw / 2) / W - 0.3) < 0.01
    _, nw, nh, left, top = subject_placement(500, 500, W, H, "large", "upper")
    assert top >= round(0.04 * H)


def test_tinted_uses_only_the_main_color():
    r = compose(*PAGES[0], {"colors": ["#1E88E5"]}, 1)
    core = cv2.erode(r.subject.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    px = r.rgb[core].astype(np.float32)
    main = np.asarray(hex_to_rgb("#1E88E5"), np.float32)
    k = px / main
    assert np.allclose(k, k[:, :1], atol=0.03)
    assert k.min() >= 0.33 and k.max() <= 1.01
    assert k.max() - k.min() > 0.3


def test_faded_page_keeps_subject_vivid_and_fades_the_rest():
    view = load_rgb(PAGES[0][1])
    r = compose(*PAGES[0], {"background": "#000000"}, 3)
    core = cv2.erode(r.subject.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    assert np.array_equal(r.rgb[core], view[core])
    outside = ~cv2.dilate(r.subject.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    sat_out = cv2.cvtColor(r.rgb, cv2.COLOR_RGB2HSV)[..., 1][outside].mean()
    assert sat_out < 0.35 * cv2.cvtColor(view, cv2.COLOR_RGB2HSV)[..., 1][outside].mean()


def test_outlined_keeps_page_and_draws_main_color_ring():
    view = load_rgb(PAGES[1][1])
    for outline, width in (("off", 8), ("thin", 4), ("thick", 8)):
        r = compose(*PAGES[1], {"colors": ["#E53935"], "outline": outline}, 4)
        assert r.outline_px == width
        assert (r.rgb[r.outline] == hex_to_rgb("#E53935")).all()
        untouched = ~r.outline
        assert np.array_equal(r.rgb[untouched], view[untouched])


def test_extra_outline_uses_second_color_at_cutout_and_faded():
    s = {"colors": ["#FDD835", "#1E88E5"], "outline": "thin"}
    for level in (2, 3):
        r = compose(*PAGES[0], s, level)
        assert r.outline.any()
        assert (r.rgb[r.outline] == hex_to_rgb("#1E88E5")).all()
    assert not compose(*PAGES[0], s, 1).outline.any()
    assert not compose(*PAGES[0], {"outline": "off"}, 2).outline.any()


def test_text_band_only_when_text_is_on():
    on = compose(*PAGES[0], {"text_mode": "below", "background": "#000080"}, 2, TEXT)
    assert on.picture_height == on.rgb.shape[0] - round(0.16 * on.rgb.shape[0])
    assert on.text_color == (255, 255, 255)
    assert contrast_ratio(on.text_color, on.background) >= 4.5
    band = on.rgb[on.picture_height:]
    assert (band == 255).all(axis=2).any()
    off = compose(*PAGES[0], {"text_mode": "off"}, 2, TEXT)
    assert off.picture_height == off.rgb.shape[0] and off.text_color is None
    empty = compose(*PAGES[0], {"text_mode": "below"}, 2, "  ")
    assert empty.text_color is None


def test_white_background_gets_black_text():
    r = compose(*PAGES[0], {"text_mode": "below", "background": "#FFFFFF"}, 1, TEXT)
    assert r.text_color == (0, 0, 0)


def test_overlay_matches_view_size():
    out = decode(overlay(PAGES[0][1], PAGES[0][2]))
    assert out.shape[:2] == load_rgb(PAGES[0][1]).shape[:2]


BLUE, ORANGE, PURPLE = SUBJECT_PALETTE[0], SUBJECT_PALETTE[1], SUBJECT_PALETTE[2]


@pytest.fixture
def two_masks(tmp_path):
    """Page 1's bird mask, plus a second subject: a block in a corner clear of the bird."""
    bird_path = PAGES[0][2]
    bird = load_mask(bird_path)
    h, w = bird.shape
    second = np.zeros_like(bird)
    second[int(h * 0.05):int(h * 0.25), int(w * 0.05):int(w * 0.25)] = 255
    assert not (second & bird).any()
    second_path = tmp_path / "second_mask.png"
    cv2.imwrite(str(second_path), second)
    return bird_path, second_path


def view_masks(view_path, *mask_paths):
    view = load_rgb(view_path)
    vh, vw = view.shape[:2]
    return view, [cv2.resize(load_mask(p), (vw, vh), interpolation=cv2.INTER_AREA) for p in mask_paths]


def tint_colour(out_px, view_px, tint):
    """The palette colour that produced this tinted pixel."""
    return (out_px.astype(np.float32) - view_px.astype(np.float32) * (1 - tint)) / tint


def closer(colour, a, b) -> bool:
    return np.linalg.norm(colour - np.float32(a)) < np.linalg.norm(colour - np.float32(b))


def inside(mask):
    ys, xs = np.nonzero(cv2.erode((mask == 255).astype(np.uint8), np.ones((9, 9), np.uint8)))
    return ys[len(ys) // 2], xs[len(xs) // 2]


def dimmed(view):
    return np.clip(np.rint(view.astype(np.float32) * 0.55), 0, 255).astype(np.uint8)


def test_overlay_palette_matches_view_size(two_masks):
    out = decode(overlay_palette(PAGES[0][1], list(two_masks), 0))
    assert out.shape[:2] == load_rgb(PAGES[0][1]).shape[:2]


def test_overlay_palette_colours_each_candidate(two_masks):
    view, (m0, m1) = view_masks(PAGES[0][1], *two_masks)
    out = decode(overlay_palette(PAGES[0][1], list(two_masks), None, fmt="png"))
    y, x = inside(m0)
    assert closer(tint_colour(out[y, x], view[y, x], 0.30), BLUE, ORANGE)
    y, x = inside(m1)
    assert closer(tint_colour(out[y, x], view[y, x], 0.30), ORANGE, BLUE)
    clear = cv2.dilate(((m0 > 0) | (m1 > 0)).astype(np.uint8), np.ones((15, 15), np.uint8)) == 0
    assert np.array_equal(out[clear], dimmed(view)[clear])


def test_overlay_palette_rings_the_selected_candidate_only(two_masks):
    from render.core import ring_around
    view, (m0, m1) = view_masks(PAGES[0][1], *two_masks)
    ring0, ring1 = ring_around(m0 >= 128, 3), ring_around(m1 >= 128, 3)
    out = decode(overlay_palette(PAGES[0][1], list(two_masks), 1, fmt="png"))
    assert (out[ring1] == ORANGE).all()
    assert (out[ring0] == BLUE).all(axis=1).mean() < 0.05
    none = decode(overlay_palette(PAGES[0][1], list(two_masks), None, fmt="png"))
    assert (none[ring0] == BLUE).all(axis=1).mean() < 0.05
    assert (none[ring1] == ORANGE).all(axis=1).mean() < 0.05


def test_overlay_palette_empty_list_is_the_dimmed_page():
    view = load_rgb(PAGES[0][1])
    out = decode(overlay_palette(PAGES[0][1], [], None, fmt="png"))
    assert np.array_equal(out, dimmed(view))


def test_overlay_palette_cycles_after_six(tmp_path):
    missing = [tmp_path / f"missing_{i}.png" for i in range(6)]
    seventh = decode(overlay_palette(PAGES[0][1], missing + [PAGES[0][2]], 6, fmt="png"))
    first = decode(overlay_palette(PAGES[0][1], [PAGES[0][2]], 0, fmt="png"))
    assert np.array_equal(seventh, first)


def test_overlay_palette_skips_a_bad_path(two_masks, tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a png")
    view, (m0, m1) = view_masks(PAGES[0][1], *two_masks)
    out = decode(overlay_palette(PAGES[0][1], [two_masks[0], broken, two_masks[1]], None, fmt="png"))
    y, x = inside(m0)
    assert closer(tint_colour(out[y, x], view[y, x], 0.30), BLUE, PURPLE)
    y, x = inside(m1)
    assert closer(tint_colour(out[y, x], view[y, x], 0.30), PURPLE, BLUE)


def test_settings_accept_model_or_dict_and_bad_level_raises():
    from render._types import LocalSettings
    assert render(*PAGES[0], LocalSettings(), 2) == render(*PAGES[0], {}, 2)
    with pytest.raises(ValueError):
        render(*PAGES[0], {}, 5)


def test_render_version_is_a_string():
    assert isinstance(RENDER_VERSION, str) and RENDER_VERSION
