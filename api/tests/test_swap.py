"""The swap check: runs whatever PIPELINE and RENDER select against the frozen contracts.

Swap commands (run from the repo root):
  hour 4, display only:   RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q
  pipeline only:          PIPELINE=real .venv/bin/python -m pytest api/tests/test_swap.py -q
  hour 7, both together:  PIPELINE=real RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q
Nothing here may depend on stand-in values (page count, colors, shapes). second_look is not
called: with real code it spends the Gemini key.
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from api import modules
from api.tests.helpers import make_pdf
from contracts.hashing import hash_bytes
from contracts.types import CheckResult, PageResult, Settings


@pytest.fixture(scope="module")
def book_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("books") / "b1"


@pytest.fixture(scope="module")
def assets(book_dir):
    book_dir.mkdir(parents=True)
    pdf = book_dir / "source.pdf"
    pdf.write_bytes(make_pdf(2))
    return modules.pipeline.rasterize(pdf, book_dir)


def SQUARE(a):
    w, h = a.width, a.height
    return [(0.2 * w, 0.2 * h), (0.6 * w, 0.2 * h), (0.6 * w, 0.6 * h), (0.2 * w, 0.6 * h)]


def check_mask(c, a, book_dir):
    master = Image.open(a.image_path)
    path = Path(c.mask_path)
    assert path.resolve() == (book_dir / "masks" / f"{a.page_number}_{c.mask_hash}.png").resolve(), \
        "masks are saved at out_dir/masks/{page_number}_{mask_hash}.png"
    mask = Image.open(path)
    assert mask.mode == "L", "masks are single-channel, mode L"
    assert mask.size == master.size, "masks are the size of the master"
    assert c.mask_hash == hash_bytes(path.read_bytes()), \
        "mask_hash must be contracts.hashing.hash_bytes of the file, or approvals will not match"
    x0, y0, x1, y1 = c.box
    assert 0 <= x0 < x1 <= a.width, "boxes are master pixels: x0 < x1 inside the page width"
    assert 0 <= y0 < y1 <= a.height, "boxes are master pixels: y0 < y1 inside the page height"


def test_rasterize_follows_contract_3(assets, book_dir):
    for a in assets:
        assert Path(a.image_path).resolve() == (book_dir / "pages" / f"{a.page_number}.png").resolve(), \
            "out_dir must be the book folder, with masters at pages/{n}.png"
        assert Path(a.view_path).resolve() == (book_dir / "pages" / f"{a.page_number}_view.png").resolve(), \
            "working copies are at pages/{n}_view.png"
        master, view = Image.open(a.image_path), Image.open(a.view_path)
        assert master.mode == "RGB", "the master must be RGB"
        assert master.size == (a.width, a.height), "width and height must be the master's pixel size"
        assert max(master.size) <= 3000, "the master's longer side must be at most 3000 px"
        assert max(view.size) == 1600, "the working copy's longer side must be 1600 px"
    assert [a.page_number for a in assets] == list(range(1, len(assets) + 1)), "pages are numbered from 1"


def test_process_page_never_raises_and_masks_follow_contract_3(assets, book_dir):
    found = 0
    for a in assets:
        result = modules.pipeline.process_page(a, book_dir)
        assert isinstance(result, PageResult), "process_page must return a PageResult and never raise"
        assert result.selected is None or result.selected >= 0, "selected is None or an index, never negative"
        assert result.selected is None or result.selected < len(result.candidates), \
            "selected must index into candidates"
        for c in result.candidates:
            check_mask(c, a, book_dir)
            found += 1
    if not found:
        pytest.skip("the pipeline returned no candidates for the test pages; auto-generated masks were not checked")


def test_outline_is_used_exactly_as_drawn(assets, book_dir):
    a = assets[0]
    w, h = a.width, a.height
    c = modules.pipeline.mask_from_outline(a.image_path, "duck", SQUARE(a), book_dir)
    check_mask(c, a, book_dir)
    mask = Image.open(c.mask_path)
    assert mask.getpixel((int(0.4 * w), int(0.4 * h))) == 255, "a point inside the drawn outline must be 255"
    assert mask.getpixel((int(0.9 * w), int(0.9 * h))) == 0, "a point outside the drawn outline must be 0"
    assert c.label == "duck", "the teacher's label is kept as given"
    assert c.source == "manual", "an outline candidate has source 'manual'"
    assert c.confidence == 1.0, "an outline candidate has confidence 1.0"


def test_click_returns_a_candidate(assets, book_dir):
    a = assets[0]
    c = modules.pipeline.segment_at_point(a.image_path, a.width / 2, a.height / 2, book_dir)
    check_mask(c, a, book_dir)
    assert c.source == "click", "a click candidate has source 'click'"


@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_display_functions_return_contract_types(assets, book_dir, level):
    a = assets[0]
    c = modules.pipeline.mask_from_outline(a.image_path, "duck", SQUARE(a), book_dir)
    out = modules.display.render(a.image_path, a.view_path, c.mask_path, Settings(), level, a.text)
    image = Image.open(io.BytesIO(out))
    assert image.format == "WEBP", "render returns WebP bytes by default"
    assert max(image.size) == 1600, "the rendered image's longer side must be 1600 px"
    png = modules.display.render(a.image_path, a.view_path, c.mask_path, Settings(), level, a.text, fmt="png")
    assert Image.open(io.BytesIO(png)).format == "PNG", "render with fmt='png' returns PNG bytes"
    checks = modules.display.run_checks(a.image_path, a.view_path, c.mask_path, Settings(), level, a.text)
    assert isinstance(checks, CheckResult), "run_checks must return a CheckResult"
    shown = Image.open(io.BytesIO(modules.display.overlay(a.view_path, c.mask_path)))
    assert shown.format == "WEBP", "overlay must return WebP bytes"
    assert isinstance(modules.display.RENDER_VERSION, str), "RENDER_VERSION must be a string"
    assert modules.display.RENDER_VERSION, "RENDER_VERSION must not be empty"
