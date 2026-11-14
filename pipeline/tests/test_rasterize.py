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


# --- found in the whole-branch review ---

def test_rotated_pages_come_out_upright(make_pdf, tmp_path):
    """A red mark drawn at the page's own top-left corner lands where the rotation puts it."""
    pdf = make_pdf([{"size": LETTER, "mark": True, "rotate": rotate} for rotate in (0, 90, 180, 270)])
    assets = rasterize(pdf, tmp_path / "b")
    corners = {}
    for asset, rotate in zip(assets, (0, 90, 180, 270)):
        image = Image.open(asset.image_path)
        width, height = image.size
        assert (width > height) == (rotate in (90, 270))
        points = {"top-left": (20, 20), "top-right": (width - 20, 20),
                  "bottom-right": (width - 20, height - 20), "bottom-left": (20, height - 20)}
        red = [name for name, point in points.items() if image.getpixel(point)[0] > 200 and image.getpixel(point)[1] < 80]
        corners[rotate] = red
    assert corners == {0: ["top-left"], 90: ["top-right"], 180: ["bottom-right"], 270: ["bottom-left"]}


def test_only_one_pdf_is_rasterized_at_a_time(make_pdf, tmp_path, monkeypatch):
    """PyMuPDF is not safe to use from two threads at once; two uploads must take turns."""
    import threading
    import time

    import pipeline.ingest

    real_open = pipeline.ingest.pymupdf.open
    inside, peak, lock = [0], [0], threading.Lock()

    class Tracked:
        def __init__(self, path):
            self.doc = real_open(path)

        def __enter__(self):
            with lock:
                inside[0] += 1
                peak[0] = max(peak[0], inside[0])
            time.sleep(0.1)
            return self.doc

        def __exit__(self, *args):
            with lock:
                inside[0] -= 1
            self.doc.close()

    pdf = make_pdf([{"size": (200, 200)}])
    monkeypatch.setattr(pipeline.ingest.pymupdf, "open", Tracked)
    threads = [threading.Thread(target=rasterize, args=(pdf, tmp_path / f"b{i}")) for i in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert peak[0] == 1
