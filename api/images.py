"""Image responses and the stand-in page used while the routes still answer with examples."""
from functools import lru_cache

from fastapi import Response

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
