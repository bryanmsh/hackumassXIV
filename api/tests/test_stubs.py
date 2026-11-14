import io
from pathlib import Path

import pytest
from PIL import Image

from api import stubs
from contracts.hashing import hash_bytes
from contracts.types import CheckResult, SecondLook, Settings


@pytest.fixture
def assets(tmp_path):
    return stubs.rasterize("ignored.pdf", tmp_path)


def test_rasterize_writes_three_pages(assets, tmp_path):
    assert [a.page_number for a in assets] == [1, 2, 3]
    assert Image.open(assets[0].image_path).size == (3000, 2250)
    assert Image.open(assets[0].view_path).size == (1600, 1200)
    assert assets[0].image_path == str(tmp_path / "pages" / "1.png")


def test_process_page_states(assets, tmp_path):
    r1, r2, r3 = (stubs.process_page(a, tmp_path) for a in assets)
    assert (r1.state, r1.selected, len(r1.candidates)) == ("ready", 0, 2)
    assert (r2.state, r2.selected, len(r2.candidates)) == ("needs_subject", None, 2)
    assert (r3.state, r3.candidates, r3.reason) == ("failed", [], "stub failure")


def test_mask_matches_contract_3(assets, tmp_path):
    c = stubs.process_page(assets[0], tmp_path).candidates[0]
    m = Image.open(c.mask_path)
    assert (m.mode, m.size) == ("L", (3000, 2250))
    assert c.mask_hash == hash_bytes(Path(c.mask_path).read_bytes())
    assert Path(c.mask_path).name == f"1_{c.mask_hash}.png"


def test_outline_fills_the_polygon(assets, tmp_path):
    c = stubs.mask_from_outline(assets[0].image_path, "duck",
        [(100, 100), (500, 100), (500, 400), (100, 400)], tmp_path)
    m = Image.open(c.mask_path)
    assert m.getpixel((300, 250)) == 255 and m.getpixel((800, 800)) == 0
    assert (c.label, c.source, c.confidence) == ("duck", "manual", 1.0)


def test_outline_needs_three_points(assets, tmp_path):
    with pytest.raises(ValueError):
        stubs.mask_from_outline(assets[0].image_path, "duck", [(1, 1), (2, 2)], tmp_path)


def test_click_in_the_corner_stays_on_the_page(assets, tmp_path):
    c = stubs.segment_at_point(assets[0].image_path, 2999, 2249, tmp_path)
    assert c.source == "click" and c.box[2] <= 3000 and c.box[3] <= 2250
    assert Image.open(c.mask_path).size == (3000, 2250)


def test_render_and_overlay_return_webp(assets, tmp_path):
    c = stubs.process_page(assets[0], tmp_path).candidates[0]
    out = stubs.render(assets[0].image_path, assets[0].view_path, c.mask_path, Settings(), 2, "")
    assert Image.open(io.BytesIO(out)).format == "WEBP"
    assert Image.open(io.BytesIO(stubs.overlay(assets[0].view_path, c.mask_path))).format == "WEBP"


def test_render_png_on_request(assets, tmp_path):
    c = stubs.process_page(assets[0], tmp_path).candidates[0]
    out = stubs.render(assets[0].image_path, assets[0].view_path, c.mask_path, Settings(), 2, "", fmt="png")
    assert Image.open(io.BytesIO(out)).format == "PNG"


def test_checks_and_second_look_return_contract_types(assets, tmp_path):
    c = stubs.process_page(assets[0], tmp_path).candidates[0]
    checks = stubs.run_checks(assets[0].image_path, assets[0].view_path, c.mask_path, Settings(), 2, "")
    assert isinstance(checks, CheckResult) and checks.fidelity.status == "pass"
    look = stubs.second_look(assets[0].image_path, c.mask_path, "rabbit", ["bunny"])
    assert isinstance(look, SecondLook) and (look.status, look.answer) == ("pass", "rabbit")


def test_read_credits_finds_none():
    assert stubs.read_credits("ignored.pdf") == dict.fromkeys(
        ("author", "illustrator", "publisher", "source", "license"))
