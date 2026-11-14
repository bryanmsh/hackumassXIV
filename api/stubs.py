"""Stand-ins for the pipeline (Bryan) and the display and checks (Kevin).

Same names and signatures as Contract 2, fixed output, no AI and no network.
Chosen by the PIPELINE and RENDER settings; see api/modules.py.
`out_dir` is the book folder: files go in out_dir/pages and out_dir/masks.
"""
import io
from pathlib import Path

from PIL import Image, ImageDraw

from contracts.hashing import hash_bytes
from contracts.types import Candidate, CheckItem, CheckResult, PageAsset, PageResult, SecondLook

RENDER_VERSION = "stub-1"

MASTER_SIZE = (3000, 2250)
VIEW_SIZE = (1600, 1200)
PAGE_COLOR = (225, 225, 225)
PAGE_TEXT = "The rabbit sat under the tree."


def _save_mask(mask: Image.Image, image_path, out_dir) -> tuple[str, str]:
    """Save a mask under its own hash. Returns (path, hash). Never overwrites."""
    buffer = io.BytesIO()
    mask.save(buffer, "PNG")
    data = buffer.getvalue()
    mask_hash = hash_bytes(data)
    page_number = Path(image_path).stem  # masters are named {n}.png
    path = Path(out_dir) / "masks" / f"{page_number}_{mask_hash}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return str(path), mask_hash


def _rect_candidate(image_path, out_dir, size, box, label, synonyms, confidence, source) -> Candidate:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    mask_path, mask_hash = _save_mask(mask, image_path, out_dir)
    return Candidate(label=label, synonyms=synonyms, box=box, confidence=confidence,
                     mask_path=mask_path, mask_hash=mask_hash, source=source)


def _encode(path, fmt) -> bytes:
    buffer = io.BytesIO()
    Image.open(path).convert("RGB").save(buffer, fmt.upper(), quality=90)
    return buffer.getvalue()


# --- pipeline ---

def rasterize(pdf_path, out_dir) -> list[PageAsset]:
    """Ignores the PDF and writes three flat gray pages."""
    pages = Path(out_dir) / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    assets = []
    for n in (1, 2, 3):
        image_path, view_path = pages / f"{n}.png", pages / f"{n}_view.png"
        Image.new("RGB", MASTER_SIZE, PAGE_COLOR).save(image_path)
        Image.new("RGB", VIEW_SIZE, PAGE_COLOR).save(view_path)
        assets.append(PageAsset(page_number=n, image_path=str(image_path), view_path=str(view_path),
                                width=MASTER_SIZE[0], height=MASTER_SIZE[1],
                                text=PAGE_TEXT, text_source="layer"))
    return assets


def process_page(asset, out_dir, force=False) -> PageResult:
    """Page 1 is ready, page 2 needs a subject, page 3 fails, then the cycle repeats."""
    kind = asset.page_number % 3
    if kind == 0:
        return PageResult(state="failed", page_kind=None, candidates=[], selected=None,
                          reason="stub failure")
    w, h = asset.width, asset.height
    size = (w, h)
    candidates = [
        _rect_candidate(asset.image_path, out_dir, size, (0.30 * w, 0.40 * h, 0.60 * w, 0.80 * h),
                        "rabbit", ["bunny", "animal"], 0.84, "auto"),
        _rect_candidate(asset.image_path, out_dir, size, (0.60 * w, 0.05 * h, 0.95 * w, 0.90 * h),
                        "tree", [], 0.41, "auto"),
    ]
    if kind == 1:
        return PageResult(state="ready", page_kind="single", candidates=candidates,
                          selected=0, reason=None)
    return PageResult(state="needs_subject", page_kind="several", candidates=candidates,
                      selected=None, reason=None)


def segment_at_point(image_path, x, y, out_dir) -> Candidate:
    """A rectangle 20% of the page, centered on the click and clipped to the page."""
    w, h = Image.open(image_path).size
    box = (max(0, x - 0.1 * w), max(0, y - 0.1 * h), min(w, x + 0.1 * w), min(h, y + 0.1 * h))
    return _rect_candidate(image_path, out_dir, (w, h), box, "object", [], 0.9, "click")


def refine_mask(image_path, mask_path, x, y, out_dir) -> Candidate:
    """The old mask plus a rectangle 10% of the page around the click. No label, like the real one."""
    old = Image.open(mask_path).convert("L")
    w, h = old.size
    added = (max(0, x - 0.05 * w), max(0, y - 0.05 * h), min(w, x + 0.05 * w), min(h, y + 0.05 * h))
    mask = old.copy()
    ImageDraw.Draw(mask).rectangle(added, fill=255)
    mask_path, mask_hash = _save_mask(mask, image_path, out_dir)
    return Candidate(label="", synonyms=[], box=mask.getbbox(), confidence=1.0,
                     mask_path=mask_path, mask_hash=mask_hash, source="click")


def mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate:
    """Fills the teacher's polygon exactly as drawn."""
    points = [tuple(p) for p in points]
    if len(points) < 3:
        raise ValueError("an outline needs at least 3 points")
    mask = Image.new("L", Image.open(image_path).size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    mask_path, mask_hash = _save_mask(mask, image_path, out_dir)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return Candidate(label=label, synonyms=[], box=(min(xs), min(ys), max(xs), max(ys)),
                     confidence=1.0, mask_path=mask_path, mask_hash=mask_hash, source="manual")


# --- display and checks ---

def render(image_path, view_path, mask_path, settings, level, text, fmt="webp") -> bytes:
    """Returns the page unchanged."""
    return _encode(view_path, fmt)


def overlay(view_path, mask_path) -> bytes:
    """Returns the page unchanged."""
    return _encode(view_path, "webp")


def run_checks(image_path, view_path, mask_path, settings, level, text) -> CheckResult:
    ok = CheckItem(status="pass", value=None, detail="stub")
    return CheckResult(fidelity=ok, page_edge=ok, background=ok, contrast=ok, size=ok)


def second_look(image_path, mask_path, label, synonyms) -> SecondLook:
    return SecondLook(status="pass", answer=label, detail="stub")
