"""Ingest: turn a PDF into master and working-copy page images plus each page's text."""
import threading
from pathlib import Path

import pymupdf
from PIL import Image

from contracts.types import PageAsset

DPI = 300
MASTER_MAX = 3000  # longer side of the master, in pixels
VIEW_MAX = 1600  # longer side of the working copy
SPREAD_RATIO = 1.9
LOW_QUALITY_MAX = 1000  # an only-image whose longer side is under this is low quality

_pymupdf_lock = threading.Lock()  # PyMuPDF is not safe on two threads at once; two uploads take turns


def _fit(image: Image.Image, longest: int) -> Image.Image:
    """Shrink so the longer side is at most `longest`. Never enlarges."""
    scale = longest / max(image.size)
    if scale >= 1:
        return image
    return image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)


def rasterize(pdf_path, out_dir) -> list[PageAsset]:
    """Write out_dir/pages/{n}.png and {n}_view.png for every page and return one PageAsset each."""
    pages_dir = Path(out_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    with _pymupdf_lock, pymupdf.open(pdf_path) as doc:
        for number, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(dpi=DPI, alpha=False)  # applies the page's rotation
            master = _fit(Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples), MASTER_MAX)
            image_path, view_path = pages_dir / f"{number}.png", pages_dir / f"{number}_view.png"
            master.save(image_path)
            _fit(master, VIEW_MAX).save(view_path)

            text = page.get_text().strip()
            text_boxes = _text_boxes(page)
            flags = []
            if master.width > SPREAD_RATIO * master.height:
                flags.append("spread")
            images = page.get_images(full=True)
            # One embedded image is the artwork itself, so its own size is the real resolution.
            if len(images) == 1 and max(images[0][2], images[0][3]) < LOW_QUALITY_MAX:
                flags.append("low_quality")

            assets.append(PageAsset(
                page_number=number, image_path=str(image_path), view_path=str(view_path),
                width=master.width, height=master.height,
                text=text, text_source="layer" if text else "none", flags=flags,
                text_boxes=text_boxes))
    return assets


def _text_boxes(page) -> list[tuple[float, float, float, float]]:
    """Each text block's box as fractions of the rendered (rotated) page, top-left origin."""
    rect = page.rect  # the page as rendered, rotation applied
    if rect.width <= 0 or rect.height <= 0:
        return []
    boxes = []
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, content, _, kind = block[:7]
        if kind != 0 or not str(content).strip():  # 0 = text, 1 = image
            continue
        r = pymupdf.Rect(x0, y0, x1, y1) * page.rotation_matrix
        fx0, fy0 = max(0.0, r.x0 / rect.width), max(0.0, r.y0 / rect.height)
        fx1, fy1 = min(1.0, r.x1 / rect.width), min(1.0, r.y1 / rect.height)
        if fx1 > fx0 and fy1 > fy0:
            boxes.append((round(fx0, 4), round(fy0, 4), round(fx1, 4), round(fy1, 4)))
    return boxes
