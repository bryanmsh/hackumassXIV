"""Subject choosing for one page: ask Gemini, cut a mask per candidate, set the page state.

process_page never raises. Anything that goes wrong becomes a Failed page with a reason,
so one bad page cannot stop the rest of the book.
"""
import os
import re
import time

import cv2

from contracts.types import Candidate, PageResult
from pipeline import segment as segmenter
from pipeline.gemini import GeminiError, RateLimited, choose_subjects
from pipeline.masks import clean_mask, save_mask

READY_MIN_CONFIDENCE = 0.7  # tuned on the six test pages only, never the evaluation pages
READY_MIN_LEAD = 0.2  # how far the top candidate must be ahead of the next
RATE_LIMIT_WAIT_S = 10
GEMINI_SCALE = 1000  # Gemini boxes are [ymin, xmin, ymax, xmax] on a 0 to 1000 scale
MAX_REASON_LENGTH = 200


def gemini_box_to_pixels(box_2d, width, height) -> tuple[float, float, float, float]:
    """The only place the 0 to 1000 scale is converted. Returns (x0, y0, x1, y1) in master pixels."""
    ymin, xmin, ymax, xmax = (min(GEMINI_SCALE, max(0, value)) for value in box_2d)
    x0, x1 = sorted((xmin / GEMINI_SCALE * width, xmax / GEMINI_SCALE * width))
    y0, y1 = sorted((ymin / GEMINI_SCALE * height, ymax / GEMINI_SCALE * height))
    return (x0, y0, x1, y1)


def _in_text(term: str, text: str) -> bool:
    """Whole-word match, ignoring case and a plural ending."""
    return bool(term) and re.search(rf"\b{re.escape(term)}(s|es)?\b", text, re.IGNORECASE) is not None


def decide_state(page_kind, candidates: list[Candidate], text: str) -> tuple[str, int | None, str | None]:
    """(state, selected, reason), by the spec's rules in the spec's order.

    The page kind and the text match decide first. Confidence is the model's own
    estimate and runs high, so it only breaks ties.
    """
    if page_kind == "scene":
        return "no_clear_subject", None, "The page is a scene with no single subject"
    if not candidates:
        return "no_clear_subject", None, "No subject was found on this page"
    if page_kind == "several":
        return "needs_subject", None, "The page has several subjects"
    top = candidates[0]
    if text.strip() and not any(_in_text(term, text) for term in [top.label, *top.synonyms]):
        return "needs_subject", None, f'The page text does not mention "{top.label}"'
    lead = top.confidence - candidates[1].confidence if len(candidates) > 1 else 1.0
    if top.confidence >= READY_MIN_CONFIDENCE and round(lead, 6) >= READY_MIN_LEAD:
        return "ready", 0, None
    return "needs_subject", None, "The app is not sure which object is the subject"


def call_with_retry(fn):
    """Run one AI call with one retry. A rate limit waits first; a second failure is raised."""
    try:
        return fn()
    except RateLimited:
        time.sleep(RATE_LIMIT_WAIT_S)
    except GeminiError:
        pass
    return fn()


def _reason(error: Exception) -> str:
    """A short reason a teacher can read. Never contains the key."""
    message = str(error) if isinstance(error, GeminiError) else f"{type(error).__name__}: {error}"
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        message = message.replace(key, "***")
    return message[:MAX_REASON_LENGTH] or type(error).__name__


def _result(state, page_kind=None, candidates=(), selected=None, reason=None) -> PageResult:
    return PageResult(state=state, page_kind=page_kind, candidates=list(candidates),
                      selected=selected, reason=reason)


def process_page(asset, out_dir, force=False) -> PageResult:
    """Choose the subject of one page and cut a mask for each candidate. Never raises."""
    try:
        if "spread" in asset.flags and not force:
            return _result("unsupported", reason="Two-page spread")

        image = cv2.imread(str(asset.image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError("the page image could not be read")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]

        answer = call_with_retry(lambda: choose_subjects(asset.view_path, asset.text))

        candidates = []
        for found in answer.candidates:  # highest confidence first
            box = gemini_box_to_pixels(found.box_2d, width, height)
            mask = clean_mask(segmenter.segment(image, box=box))
            if not mask.any():
                continue  # nothing was cut out, so there is nothing to show the teacher
            mask_path, mask_hash = save_mask(mask, asset.image_path, out_dir)
            candidates.append(Candidate(
                label=found.label, synonyms=found.synonyms, box=box, confidence=found.confidence,
                mask_path=mask_path, mask_hash=mask_hash, source="auto"))

        if answer.candidates and not candidates:
            return _result("no_clear_subject", answer.page_kind, reason="No usable cut-out could be made")
        state, selected, reason = decide_state(answer.page_kind, candidates, asset.text)
        return _result(state, answer.page_kind, candidates, selected, reason)
    except Exception as error:
        return _result("failed", reason=_reason(error))
