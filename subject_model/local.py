"""The Gemini-shaped answer from the local models: blobs from the finder, names from the namer, ranked by page text.

`choose_subjects` returns the JSON that `pipeline.gemini.SubjectAnswer` accepts; `local_answer` is exactly what the
pipeline's hook returns; `label_crop` names a teacher's click.
"""
from __future__ import annotations

import cv2
import numpy as np

from pipeline import gemini
from pipeline.gemini import DUPLICATE_IOU, GROUP_HOLDS, INSIDE_FRACTION, SubjectAnswer, _drop_non_subjects
from subject_model.words import GENERAL, NEVER_A_LABEL, NOT_A_SUBJECT, SYNONYMS, match

TEXT_BASE = 0.6  # a guess the text confirms starts here...
TEXT_GAIN = 0.4  # ...and gains this much times the namer's probability
NO_TEXT_SCALE = 0.8  # an unconfirmed guess gets this much times the namer's probability
MIN_TEXT_GUESS = 0.10  # the text confirms only a guess the namer gives at least this
DROP_AT = 0.5  # a blob is dropped when its not-a-subject guesses hold this much probability
LABEL_MIN = 0.5  # a teacher's click is named only when the namer is at least this sure
CONFIDENCE_CAP = 1.0
MAX_CANDIDATES = 5
MAX_THINGS = 10
CONFIRMED = "Stands out on the page and the text names it."
UNCONFIRMED = "Stands out on the page."


def _names(label: str) -> list[str]:
    return [label] + SYNONYMS.get(label, [])


def _box_2d(box, width, height) -> list[int]:
    x0, y0, x1, y1 = box
    return [round(y0 / height * 1000), round(x0 / width * 1000), round(y1 / height * 1000), round(x1 / width * 1000)]


def _corners(box_2d):
    ymin, xmin, ymax, xmax = box_2d
    return min(xmin, xmax), min(ymin, ymax), max(xmin, xmax), max(ymin, ymax)


def _area(box) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def _shared(a, b) -> int:
    return _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def _settle(candidates: list[dict]) -> list[dict]:
    """Remove repeats and group boxes the way the pipeline's guard would, so the guard has nothing left to do.
    `candidates` are most confident first."""
    kept = []
    for candidate in candidates:
        a = _corners(candidate["box_2d"])
        repeat = False
        for other in kept:
            b = _corners(other["box_2d"])
            shared = _shared(a, b)
            union = _area(a) + _area(b) - shared
            repeat = repeat or (union > 0 and shared / union >= DUPLICATE_IOU)
        if not repeat:
            kept.append(candidate)

    def holds(outer, inner) -> bool:
        a, b = _corners(outer["box_2d"]), _corners(inner["box_2d"])
        return _area(b) > 0 and _shared(a, b) / _area(b) >= INSIDE_FRACTION

    while True:
        for candidate in kept:
            held = [other for other in kept if other is not candidate and holds(candidate, other)]
            if len(held) >= GROUP_HOLDS:
                group = [c for c in kept if c is candidate or any(c is h for h in held)]
                kept.remove(group[-1])  # `kept` is most confident first, so the last one is the least sure
                break
        else:
            return kept


def _read_rgb(view_path) -> np.ndarray:
    image = cv2.imread(str(view_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"cannot read the page picture: {view_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def choose_subjects(view_path, text, *, find=None, name=None) -> dict:
    """Up to five subjects of the page, in the JSON shape Gemini returns."""
    if find is None:
        from subject_model.finder import find_blobs as find
    if name is None:
        from subject_model.namer import name
    image = _read_rgb(view_path)
    height, width = image.shape[:2]
    text = text or ""

    # 1. Name each blob; drop blobs that are printed words, marks or settings, or have nothing to call them.
    blobs = []  # (box, kept guesses)
    for box, mask in find(image):
        guesses = name(image, mask)
        if not guesses or sum(p for label, p in guesses if label in NOT_A_SUBJECT) >= DROP_AT:
            continue
        kept = [(label, p) for label, p in guesses if label not in NOT_A_SUBJECT and label not in NEVER_A_LABEL]
        if kept:
            blobs.append((box, kept))
    things = []
    for _, kept in blobs:
        if kept[0][0] not in things:
            things.append(kept[0][0])

    # 2. What the text confirms: first guesses by any of their names; other guesses by a specific name, once.
    confirmed = {}  # blob index -> (label, matched name, probability)
    for i, (_, kept) in enumerate(blobs):
        label, p = kept[0]
        found = match(text, _names(label)) if p >= MIN_TEXT_GUESS else None
        if found:
            confirmed[i] = (label, found, p)
    others = []
    for i, (_, kept) in enumerate(blobs):
        if i in confirmed:
            continue
        for label, p in kept[1:]:
            if p < MIN_TEXT_GUESS:
                continue
            found = match(text, [n for n in _names(label) if n not in GENERAL])
            if found:
                others.append((-p, i, label, found, p))
    used = {found for _, found, _ in confirmed.values()}
    for _, i, label, found, p in sorted(others, key=lambda m: (m[0], m[1])):
        if i not in confirmed and found not in used:
            confirmed[i] = (label, found, p)
            used.add(found)

    # 3 to 6. One candidate per blob.
    candidates = []
    for i, (box, kept) in enumerate(blobs):
        if i in confirmed:
            label, found, p = confirmed[i]
            candidate = {"label": found, "synonyms": [n for n in _names(label) if n != found],
                         "confidence": min(1.0, TEXT_BASE + TEXT_GAIN * p), "reason": CONFIRMED}
        else:
            label, p = kept[0]
            candidate = {"label": label, "synonyms": list(SYNONYMS.get(label, [])),
                         "confidence": NO_TEXT_SCALE * p, "reason": UNCONFIRMED}
        candidate["box_2d"] = _box_2d(box, width, height)
        candidate["confidence"] = round(min(candidate["confidence"], CONFIDENCE_CAP), 2)
        candidates.append({k: candidate[k] for k in ("label", "synonyms", "box_2d", "confidence", "reason")})
    candidates.sort(key=lambda c: c["confidence"], reverse=True)  # stable: blob order on a tie

    # 7 and 8. Settle the rectangles, keep at most five, and say what kind of page it is.
    candidates = _settle(candidates)[:MAX_CANDIDATES]
    kind = "scene" if not candidates else "single" if len(candidates) == 1 else "several"
    return {"things_on_page": things[:MAX_THINGS], "page_kind": kind, "candidates": candidates}


def local_answer(view_path, text):
    """Exactly what the pipeline's hook returns: the answer, checked, with the pipeline's own guard applied."""
    answer = SubjectAnswer.model_validate(choose_subjects(view_path, text))
    answer.candidates = _drop_non_subjects(answer.candidates)[:gemini.MAX_CANDIDATES]
    return answer


def label_crop(png_bytes: bytes, *, name=None) -> str:
    """The namer's first usable guess for a cropped picture, or "" when it is not sure enough."""
    if name is None:
        from subject_model.namer import name
    image = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    for label, p in name(image, None):
        if label not in NOT_A_SUBJECT and label not in NEVER_A_LABEL:
            return label if p >= LABEL_MIN else ""
    return ""
