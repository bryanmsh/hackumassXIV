"""Image responses and the pictures built from a stored page."""
import io
import threading
from collections import OrderedDict

from fastapi import HTTPException, Response
from PIL import Image

from api import modules, versions
from contracts.types import Settings

CACHE_SIZE = 256
_cache: OrderedDict[tuple, bytes] = OrderedDict()
_cache_lock = threading.Lock()


def image(data: bytes) -> Response:
    """Every image is WebP and must never be cached: an approval can lapse at any time."""
    return Response(data, media_type="image/webp", headers={"Cache-Control": "no-store"})


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
                                  settings, level, page["text"], text_boxes=page.get("text_boxes"))


def cached_render(page: dict, profile: dict, level: int) -> bytes:
    """render_page for a saved profile, remembering the last 256 pictures by (page, version token).

    A page with no version yet is keyed by the token of its selected subject, so a preview of an
    unconfirmed page is cached too. That key equals the one the confirmed version will have, which is
    safe: the same subject, settings, level and render version always give the same bytes. Whether a
    version is approved is not decided here; the reader checks that itself before it renders."""
    version = versions.current_version(page, profile, level)
    if version is None:
        subject = selected(page)
        if subject is None:
            raise HTTPException(409, "This page has no subject yet.")
        version = versions.Version(subject["mask_hash"], profile["settings_hash"], level,
                                   modules.display.RENDER_VERSION)
    key = (page["_id"], version.token)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    data = render_page(page, Settings.model_validate(profile["settings"]), level)
    with _cache_lock:
        _cache[key] = data
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return data
