from pathlib import Path

from PIL import Image

from pipeline import rasterize

LETTER = (612, 792)


def test_paths_and_sizes(make_pdf, tmp_path):
    out = tmp_path / "book"
    assets = rasterize(make_pdf([{"size": LETTER, "text": "Hi"}]), out)
    assert len(assets) == 1
    asset = assets[0]
    assert asset.page_number == 1
    assert Path(asset.image_path) == out / "pages" / "1.png"
    assert Path(asset.view_path) == out / "pages" / "1_view.png"
    master = Image.open(asset.image_path)
    assert master.mode == "RGB"
    assert max(master.size) == 3000  # 300 DPI gives 3300, capped
    assert (asset.width, asset.height) == master.size
    assert max(Image.open(asset.view_path).size) == 1600


def test_pages_are_numbered_from_one_in_order(make_pdf, tmp_path):
    assets = rasterize(make_pdf([{"size": LETTER}, {"size": LETTER}, {"size": LETTER}]), tmp_path / "b")
    assert [a.page_number for a in assets] == [1, 2, 3]
    assert Path(assets[2].image_path).name == "3.png"


def test_small_page_is_not_upscaled(make_pdf, tmp_path):
    asset = rasterize(make_pdf([{"size": (360, 360)}]), tmp_path / "b")[0]
    assert (asset.width, asset.height) == (1500, 1500)
    assert Image.open(asset.view_path).size == (1500, 1500)


def test_text_layer(make_pdf, tmp_path):
    pdf = make_pdf([{"size": LETTER, "text": "The rabbit sat."}, {"size": LETTER}])
    with_text, without = rasterize(pdf, tmp_path / "b")
    assert with_text.text == "The rabbit sat."
    assert with_text.text_source == "layer"
    assert without.text == ""
    assert without.text_source == "none"


def test_rotation_applied(make_pdf, tmp_path):
    asset = rasterize(make_pdf([{"size": LETTER, "rotate": 90}]), tmp_path / "b")[0]
    assert asset.width > asset.height
    assert Image.open(asset.image_path).size == (asset.width, asset.height)


def test_spread_flag(make_pdf, tmp_path):
    spread, not_spread = rasterize(make_pdf([{"size": (1600, 800)}, {"size": (1500, 800)}]), tmp_path / "b")
    assert "spread" in spread.flags
    assert "spread" not in not_spread.flags  # 1.875 is under 1.9


def test_low_quality_flag(make_pdf, tmp_path):
    pdf = make_pdf([
        {"size": LETTER, "image_px": (800, 600)},
        {"size": LETTER, "image_px": (1200, 900)},
        {"size": LETTER, "text": "words only"},
    ])
    small, large, text_only = rasterize(pdf, tmp_path / "b")
    assert "low_quality" in small.flags
    assert "low_quality" not in large.flags
    assert "low_quality" not in text_only.flags
