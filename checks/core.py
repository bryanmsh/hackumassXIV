"""Technical checks on an adapted page. No network, no stored state, never raises."""
from __future__ import annotations

from typing import Callable, Optional

import cv2
import numpy as np

from render._types import LocalCheck, LocalCheckResult, coerce_settings, to_contract_check_result
from render.color import contrast_ratio, luminance_map, ratio_from_luminance
from render.core import Rendered, compose, load_mask, original_layout, ring_around, shows_text

COVERAGE_MIN = 0.01
COVERAGE_MAX = 0.60
LARGEST_REGION_MIN = 0.90
CANNY_LOW, CANNY_HIGH = 100, 200
BACKGROUND_GROW_PX = 6
PLAIN_BACKGROUND_MAX = 0.005
FADED_BACKGROUND_RATIO = 0.5
CONTRAST_BAND_PX = 6
CONTRAST_MIN = 3.0
ENLARGEMENT_MAX = 2.5
SUBJECT_LENGTH_MIN = 0.15
TEXT_CONTRAST_MIN = 4.5


def _check(status: str, value: Optional[float], detail: str) -> LocalCheck:
    return LocalCheck(status=status, value=None if value is None else round(float(value), 4), detail=detail)


def _guard(fn: Callable[[], LocalCheck], name: str) -> LocalCheck:
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - a check must never raise
        return _check("fail", None, f"The {name} check could not run: {e}")


def check_fidelity(mask: np.ndarray) -> LocalCheck:
    total = mask.size
    on = mask > 0
    count = int(on.sum())
    coverage = count / total
    if count == 0:
        return _check("fail", 0.0, "The cut-out is empty.")
    n, _, stats, _ = cv2.connectedComponentsWithStats(on.astype(np.uint8), connectivity=8)
    largest = stats[1:, cv2.CC_STAT_AREA].max() / count
    pieces = n - 1
    problems = []
    if coverage < COVERAGE_MIN:
        problems.append(f"covers only {coverage:.1%} of the page (at least {COVERAGE_MIN:.0%} expected)")
    if coverage > COVERAGE_MAX:
        problems.append(f"covers {coverage:.1%} of the page (at most {COVERAGE_MAX:.0%} expected)")
    if largest < LARGEST_REGION_MIN:
        problems.append(f"is in {pieces} pieces; the largest holds only {largest:.0%} of it")
    if problems:
        return _check("fail", coverage, "The cut-out " + " and ".join(problems) + ".")
    return _check("pass", coverage, f"The cut-out covers {coverage:.1%} of the page, "
                                    f"{largest:.0%} of it in one piece.")


def check_page_edge(mask: np.ndarray) -> LocalCheck:
    on = mask > 0
    sides = {"top": on[0, :].any(), "bottom": on[-1, :].any(), "left": on[:, 0].any(), "right": on[:, -1].any()}
    touched = [k for k, v in sides.items() if v]
    if touched:
        return _check("warn", len(touched), "The cut-out touches the " + ", ".join(touched) +
                      " edge of the page; the artwork may cut the object off.")
    return _check("pass", 0, "The cut-out does not touch the page edge.")


def _edge_fraction(rgb: np.ndarray, region: np.ndarray) -> float:
    area = int(region.sum())
    if area == 0:
        return 0.0
    edges = cv2.Canny(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), CANNY_LOW, CANNY_HIGH) > 0
    return float((edges & region).sum()) / area


def _background_region(r: Rendered) -> np.ndarray:
    grow = BACKGROUND_GROW_PX + r.outline_px
    near = cv2.dilate(r.subject.astype(np.uint8), cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))) > 0
    region = ~near
    region[r.picture_height:, :] = False
    return region


def check_background(r: Rendered, view_path) -> LocalCheck:
    if r.level == 4:
        return _check("pass", None, "Not checked at Outlined: the original page is shown on purpose.")
    region = _background_region(r)
    value = _edge_fraction(r.rgb, region)
    if r.level in (1, 2):
        if value > PLAIN_BACKGROUND_MAX:
            return _check("fail", value, f"The background around the subject is not plain: "
                                         f"{value:.2%} of it is edges (at most {PLAIN_BACKGROUND_MAX:.1%}).")
        return _check("pass", value, f"The background is plain ({value:.2%} edges).")
    h, w = r.rgb.shape[:2]
    original = original_layout(view_path, w, h, r.picture_height, r.background)
    base = _edge_fraction(original, region)
    limit = FADED_BACKGROUND_RATIO * base
    if base == 0:
        return _check("pass", value, "The original page has no background detail to fade.")
    if value > limit:
        return _check("fail", value, f"The faded background keeps {value:.2%} edges against "
                                     f"{base:.2%} on the original (target at most half).")
    return _check("pass", value, f"Background detail went from {base:.2%} to {value:.2%} "
                                 f"edges ({value / base:.0%} of the original).")


def check_contrast(r: Rendered) -> LocalCheck:
    if not r.subject.any():
        return _check("fail", None, "There is no subject on the page to measure.")
    lum = luminance_map(r.rgb)
    picture = np.zeros_like(r.subject)
    picture[:r.picture_height, :] = True
    if r.outline.any():
        inner = r.outline
        what = "The outline"
        outer = ring_around(r.subject | r.outline, CONTRAST_BAND_PX) & picture
    else:
        inner = r.subject & ~(cv2.erode(r.subject.astype(np.uint8), cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * CONTRAST_BAND_PX + 1,) * 2)) > 0)
        what = "The subject's edge"
        outer = ring_around(r.subject, CONTRAST_BAND_PX) & picture
    if not inner.any() or not outer.any():
        return _check("warn", None, "The subject fills the picture; there is no background next to it to measure.")
    ratio = ratio_from_luminance(float(np.median(lum[inner])), float(np.median(lum[outer])))
    if ratio < CONTRAST_MIN:
        return _check("warn", ratio, f"{what} has a contrast of {ratio:.1f} to 1 against the background "
                                     f"next to it (at least {CONTRAST_MIN:.0f} to 1 suggested).")
    return _check("pass", ratio, f"{what} has a contrast of {ratio:.1f} to 1 against the background next to it.")


def check_size(r: Rendered) -> LocalCheck:
    bx, by, bw, bh = r.subject_box
    if bw == 0:
        return _check("fail", None, "There is no subject to measure.")
    if r.level in (1, 2):
        if r.scale > ENLARGEMENT_MAX:
            return _check("warn", r.scale, f"The subject is enlarged {r.scale:.1f} times and may look soft "
                                           f"(more than {ENLARGEMENT_MAX} times).")
        return _check("pass", r.scale, f"The subject is shown at {r.scale:.2f} times its size in the master page.")
    mw, mh = r.master_size
    share = max(bw, bh) / max(mw, mh)
    if share < SUBJECT_LENGTH_MIN:
        return _check("warn", share, f"The subject is only {share:.0%} of the page's length and may be "
                                     f"hard to find (at least {SUBJECT_LENGTH_MIN:.0%} suggested).")
    return _check("pass", share, f"The subject is {share:.0%} of the page's length.")


def check_text_contrast(r: Rendered) -> LocalCheck:
    if r.text_color is None:
        return _check("pass", None, "Text is not shown.")
    ratio = contrast_ratio(r.text_color, r.background)
    if ratio < TEXT_CONTRAST_MIN:
        return _check("fail", ratio, f"Text contrast is {ratio:.1f} to 1 (at least {TEXT_CONTRAST_MIN} to 1).")
    return _check("pass", ratio, f"Text contrast is {ratio:.1f} to 1.")


def run_checks(image_path, view_path, mask_path, settings, level, text=None):
    """Contract 2: every check returns status, value and detail. Never raises."""
    try:
        mask = load_mask(mask_path)
    except Exception as e:  # noqa: BLE001
        mask, mask_error = None, str(e)
    rendered = None
    render_error = "mask unreadable" if mask is None else ""
    if mask is not None:
        try:
            rendered = compose(image_path, view_path, mask_path, coerce_settings(settings), int(level), text)
        except Exception as e:  # noqa: BLE001
            render_error = str(e)

    def needs_mask(fn):
        return (lambda: fn(mask)) if mask is not None else (lambda: _raise(mask_error))

    def needs_render(fn, *extra):
        return (lambda: fn(rendered, *extra)) if rendered is not None else (lambda: _raise(render_error))

    result = LocalCheckResult(
        fidelity=_guard(needs_mask(check_fidelity), "source fidelity"),
        page_edge=_guard(needs_mask(check_page_edge), "page edge"),
        background=_guard(needs_render(check_background, view_path), "background detail"),
        contrast=_guard(needs_render(check_contrast), "contrast"),
        size=_guard(needs_render(check_size), "size"),
        text_contrast=_guard(needs_render(check_text_contrast), "text contrast"),
    )
    return to_contract_check_result(result)


def _raise(message: str):
    raise RuntimeError(message)


def swatch_contrast(main_color: str, background: str) -> float:
    """Main color against background, for the profile screen's 3 to 1 warning."""
    return contrast_ratio(main_color, background)
