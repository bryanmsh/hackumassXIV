"""Choosing the subject of a page, with our own subject model (subject_model/). No outside AI service.

choose_subjects and label_crop are the only doors to the subject model. subject_model is imported
only when it is first used, because subject_model.local imports this module.

Our model finds things that stand out on the page well, but names them poorly and misses second
subjects. So every answer is checked against the page text (local_is_enough): only a page whose one
pre-selected subject the text names, and whose text is about nothing else, is marked `trusted`.
process_page asks the teacher on every other page, with our guesses still offered.

SUBJECT_MODEL=standin swaps in a placeholder that never finds anything (for a machine without the
weights). Every decision is logged on the "mirai.subjects" logger and kept per thread in
last_subject_route(). Every failure leaves this module as SubjectError, with a sentence a teacher can read.
"""
import logging
import os
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

MAX_CANDIDATES = 5  # every main subject of the page, not only the first choice

# Guards on the answer.
SETTING_WORDS = frozenset({"background", "scene", "scenery", "landscape", "forest", "jungle",
                           "woods", "sky", "ground", "grass"})  # where things are, never a subject
INSIDE_FRACTION = 0.8  # one box is "inside" another when this much of it is
GROUP_HOLDS = 2  # a box holding this many other candidates is a group or the setting
DUPLICATE_IOU = 0.8  # two boxes overlapping this much are the same object

# subject_model.local.CONFIRMED: the reason our model gives a subject the page text names.
# Copied, not imported, because subject_model.local imports this module; a test keeps them equal.
LOCAL_CONFIRMED = "Stands out on the page and the text names it."
NOT_SET_UP = "The subject finder is not set up on this server"

log = logging.getLogger("mirai.subjects")
_route = threading.local()
_warned = []


class SubjectError(Exception):
    """The subject model could not answer: it is missing, its weights are missing, or it failed."""


class SubjectCandidate(BaseModel):
    label: str
    synonyms: list[str] = []
    box_2d: list[int]  # [ymin, xmin, ymax, xmax] on a 0 to 1000 scale
    confidence: float
    reason: str = ""


class SubjectAnswer(BaseModel):
    things_on_page: list[str] = []
    page_kind: Literal["single", "several", "scene"]
    candidates: list[SubjectCandidate] = []
    # False when the page text does not back up the one subject the page rules would pre-select.
    # process_page then asks the teacher instead of pre-selecting it.
    trusted: bool = True


# ---------- guards: settings, repeats and group boxes are not subjects ----------

def _corners(box_2d) -> tuple[int, int, int, int]:
    """[ymin, xmin, ymax, xmax] in any order of corners, as (x0, y0, x1, y1)."""
    ya, xa, yb, xb = box_2d
    return min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)


def _area(box) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def _shared_area(a, b) -> int:
    return _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def _is_setting(label: str) -> bool:
    """The forest, the sky, the background: where things are, not what the page is about."""
    return any(word in SETTING_WORDS for word in label.split())


def _drop_non_subjects(candidates: list[SubjectCandidate]) -> list[SubjectCandidate]:
    """Remove settings, repeats of the same object, and boxes drawn around a group of other candidates."""
    candidates = [c for c in candidates if not _is_setting(c.label)]
    box = {id(c): _corners(c.box_2d) for c in candidates}

    kept = []  # the same object boxed twice: the more confident one stays
    for candidate in sorted(candidates, key=lambda c: c.confidence, reverse=True):
        a = box[id(candidate)]
        repeats = False
        for other in kept:
            b = box[id(other)]
            shared = _shared_area(a, b)
            union = _area(a) + _area(b) - shared
            repeats = repeats or (union > 0 and shared / union >= DUPLICATE_IOU)
        if not repeats:
            kept.append(candidate)

    def holds(outer, inner) -> bool:
        return _area(inner) > 0 and _shared_area(outer, inner) / _area(inner) >= INSIDE_FRACTION

    # One thing inside another is fine (a bird in its nest). Two or more is a group or the setting.
    return [c for c in kept
            if sum(holds(box[id(c)], box[id(other)]) for other in kept if other is not c) < GROUP_HOLDS]


# ---------- the trust rule ----------

def local_is_enough(answer: SubjectAnswer, text: str = "") -> tuple[bool, str]:
    """(trusted, reason): whether the page's one pre-selected subject can be pre-selected without asking.

    True only when process_page's own rule (decide_state) would pre-select exactly one subject,
    the page text names it, and the text is not about anything else. Without the text check our
    model was wrong on 4 of 7 Ready pages of Animal Homes.
    """
    if not answer.candidates:
        return False, "found nothing"
    from pipeline.process import decide_state  # here, not at the top: process imports this module
    state, members, _ = decide_state(answer.page_kind, answer.candidates)
    if state != "ready" or len(members) != 1:
        return False, f"would not pre-select one subject ({state}, {len(members)} selected)"
    chosen = answer.candidates[members[0]]
    if chosen.reason != LOCAL_CONFIRMED:
        return False, f'the page text does not name "{chosen.label}"'
    try:
        other = _text_names_more(text, chosen)
    except Exception as error:  # the word lists are part of subject_model; any problem means ask the teacher
        return False, f"could not check the page text: {type(error).__name__}"
    if other:
        return False, f"the page text is about more than one thing ({other})"
    return True, f'the page text names "{chosen.label}"'


LINKING_WORDS = frozenset({"and", "or", "with"})  # "bears and wolves", "and so do tigers", "a cat with kittens"


def _text_names_more(text: str, chosen) -> str | None:
    """Why the page text may be about more than the chosen subject, or None.

    Errs towards asking: the text links things ("and", "&", "or", "with"), or names any other
    thing our model knows. Our model misses second subjects it has no name for (the deer next
    to the tiger), so the text is the safer judge of whether a page is about one thing.
    """
    from subject_model.words import NOT_A_SUBJECT, _words, match
    tokens = _words(text or "")
    if "&" in (text or "") or LINKING_WORDS & set(tokens):
        return "it links things"
    own = {name.lower() for name in [chosen.label, *chosen.synonyms]}
    others = [name for name in _known_names() if name not in own and name not in NOT_A_SUBJECT]
    named = match(text or "", others)
    return f'it also names "{named}"' if named else None


_known = []


def _known_names() -> list[str]:
    """Every name our subject model can give, from subject_model/classes.txt."""
    if not _known:
        import subject_model
        path = Path(subject_model.__file__).with_name("classes.txt")
        _known.extend(line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return _known


# ---------- the two doors ----------

def last_subject_route() -> dict:
    """Why the last choose_subjects or label_crop on this thread answered as it did."""
    return dict(getattr(_route, "value", {}))


def _record(trusted: bool, reason: str) -> None:
    _route.value = {"trusted": trusted, "reason": reason}
    log.info("subjects %s (%s)", "trusted" if trusted else "for the teacher to check", reason)


def _warn_old_setting() -> None:
    """SUBJECT_FINDER chose between Gemini and our model until 2026-11-15. Say once that it is ignored."""
    finder = (os.environ.get("SUBJECT_FINDER") or "").strip().lower()
    if finder and finder != "local" and not _warned:
        _warned.append(finder)
        log.warning("SUBJECT_FINDER=%s is ignored: subjects always come from our own model", finder)


def _standin() -> bool:
    return (os.environ.get("SUBJECT_MODEL") or "").strip().lower() == "standin"


def _local_subjects(view_path, text: str) -> SubjectAnswer:
    if _standin():
        return SubjectAnswer(things_on_page=[], page_kind="scene", candidates=[])
    from subject_model.local import local_answer
    return local_answer(view_path, text)


def _local_label(png_bytes: bytes) -> str:
    if _standin():
        return ""
    from subject_model.local import label_crop as local_label
    return local_label(png_bytes)


def choose_subjects(view_path, text: str) -> SubjectAnswer:
    """Every main subject of the page, at most five, most confident first, with `trusted` set."""
    _warn_old_setting()
    try:
        answer = _local_subjects(view_path, text)
    except Exception:  # no weights, or the model failed
        log.exception("the subject model could not answer")
        # A plain sentence: the web app hides any reason that contains "Error:".
        raise SubjectError(NOT_SET_UP) from None
    answer.trusted, reason = local_is_enough(answer, text)
    _record(answer.trusted, reason)
    return answer


def label_crop(png_bytes: bytes) -> str:
    """Name the object in a cropped picture, in lowercase. "" means the model was not sure: the teacher types it."""
    _warn_old_setting()
    try:
        label = _local_label(png_bytes)
    except Exception:
        log.exception("the subject model could not name a crop")
        raise SubjectError(NOT_SET_UP) from None
    _record(bool(label), "named it" if label else "not sure of a name")
    return label
