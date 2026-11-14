"""Image responses and the pictures built from a stored page."""
import io
from functools import lru_cache

from fastapi import HTTPException, Response
from PIL import Image

from api import modules, settings
from contracts.types import Settings


def image(data: bytes) -> Response:
    """Every image is WebP and must never be cached: an approval can lapse at any time."""
    return Response(data, media_type="image/webp", headers={"Cache-Control": "no-store"})


@lru_cache
def stub_page():
    """One stand-in page and its selected cut-out, built on first use."""
    out_dir = settings.DATA_DIR / "books" / "stub"
    asset = modules.pipeline.rasterize("", out_dir)[0]
    result = modules.pipeline.process_page(asset, out_dir)
    return asset, result.candidates[result.selected]


def stub_render() -> Response:
    asset, subject = stub_page()
    return image(modules.display.render(
        asset.image_path, asset.view_path, subject.mask_path, Settings(), 2, asset.text))


def selected(page: dict) -> dict | None:
    """The selected candidate document, or None."""
    index = page.get("selected")
    return page["candidates"][index] if index is not None else None


def view_bytes(page: dict) -> bytes:
    """The working copy as WebP."""
    buffer = io.BytesIO()
    Image.open(page["view_path"]).convert("RGB").save(buffer, "WEBP", quality=90)
    return buffer.getvalue()


def render_page(page: dict, settings: Settings, level: int) -> bytes:
    """The page as a child would see it. Nothing is stored."""
    subject = selected(page)
    if subject is None:
        raise HTTPException(409, "This page has no subject yet.")
    return modules.display.render(page["image_path"], page["view_path"], subject["mask_path"],
                                  settings, level, page["text"])
