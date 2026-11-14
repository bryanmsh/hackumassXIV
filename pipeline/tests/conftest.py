"""Shared test helpers: synthetic PDFs, one synthetic page image, and the `live` marker."""
import io
import os
from pathlib import Path

import pymupdf
import pytest
from PIL import Image, ImageDraw

PAGE_SIZE = (1200, 900)
ELLIPSE_CENTER = (600, 450)
ELLIPSE_RADII = (200, 150)


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real Gemini API; runs only with RUN_LIVE=1")
    config.addinivalue_line("markers", "torch: runs a real PyTorch segmenter (downloads weights); runs only with RUN_TORCH=1")


def pytest_collection_modifyitems(config, items):
    for marker, variable in (("live", "RUN_LIVE"), ("torch", "RUN_TORCH")):
        if os.environ.get(variable) == "1":
            continue
        skip = pytest.mark.skip(reason=f"{marker} test; set {variable}=1 to run")
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def make_pdf(tmp_path):
    """make_pdf([{size, text?, rotate?, image_px?}, ...]) -> Path of a PDF with those pages."""

    def build(pages, name="book.pdf") -> Path:
        doc = pymupdf.open()
        for spec in pages:
            width, height = spec["size"]
            page = doc.new_page(width=width, height=height)
            if "image_px" in spec:
                buffer = io.BytesIO()
                Image.new("RGB", spec["image_px"], (40, 120, 200)).save(buffer, "PNG")
                page.insert_image(page.rect, stream=buffer.getvalue())
            if spec.get("mark"):  # a red square at the page's own top-left corner
                page.draw_rect(pymupdf.Rect(0, 0, 60, 60), color=(1, 0, 0), fill=(1, 0, 0))
            if spec.get("text"):
                page.insert_text((72, 72), spec["text"])
            if spec.get("rotate"):
                page.set_rotation(spec["rotate"])
        path = tmp_path / name
        doc.save(path)
        doc.close()
        return path

    return build


@pytest.fixture
def page_image(tmp_path) -> str:
    """A 1200x900 white master with one red ellipse, at tmp_path/pages/1.png."""
    image = Image.new("RGB", PAGE_SIZE, (255, 255, 255))
    cx, cy = ELLIPSE_CENTER
    rx, ry = ELLIPSE_RADII
    ImageDraw.Draw(image).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(200, 30, 30))
    path = tmp_path / "pages" / "1.png"
    path.parent.mkdir(parents=True)
    image.save(path)
    return str(path)
