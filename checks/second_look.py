"""Second look: our namer (subject_model/) names the subject from the adapted page alone.

It is the same namer that suggests labels when subjects are chosen, so on a page
whose label it suggested it mostly agrees with itself. It is most useful when the
teacher typed or changed the label. A weak signal, so only ever a warning. It
never raises and never blocks approval. No outside AI service is called.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set

from render._types import LocalSecondLook, to_contract_second_look
from render.core import compose, encode

# The Cut-out look on white: the namer was trained on cut-outs on white.
LEVEL2_ON_WHITE = {"colors": ["#000000"], "background": "#FFFFFF", "size": "medium",
                   "position": "center", "text_mode": "off", "outline": "off"}

_IRREGULAR = {"mice": "mouse", "geese": "goose", "children": "child", "people": "person",
              "teeth": "tooth", "feet": "foot", "men": "man", "women": "woman", "oxen": "ox",
              "leaves": "leaf", "wolves": "wolf", "calves": "calf", "sheep": "sheep", "fish": "fish"}


def singular(word: str) -> str:
    w = word.lower()
    if w in _IRREGULAR:
        return _IRREGULAR[w]
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and re.search(r"(ches|shes|sses|xes|zes)$", w):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def words(text: str) -> Set[str]:
    return {singular(w) for w in re.findall(r"[a-zA-Z]+", text or "")}


def matches(answer: str, label: str, synonyms: Iterable[str]) -> bool:
    targets: Set[str] = words(label)
    for s in synonyms or []:
        targets |= words(s)
    return bool(words(answer) & targets)


def _ask_namer(png: bytes) -> str:
    """The namer's first guess that is a thing, for the whole picture. "" when it has none."""
    import cv2
    import numpy as np

    from subject_model.namer import name
    from subject_model.words import NEVER_A_LABEL, NOT_A_SUBJECT

    image = cv2.cvtColor(cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    for label, _ in name(image, None):
        if label not in NOT_A_SUBJECT and label not in NEVER_A_LABEL:
            return label
    return ""


def second_look(image_path, mask_path, label: str, synonyms: Optional[List[str]] = None,
                ask=None):
    """Contract 2: one pass of our namer. `ask` replaces it in tests."""
    synonyms = list(synonyms or [])
    try:
        png = encode(compose(image_path, image_path, mask_path, LEVEL2_ON_WHITE, 2).rgb, "png")
    except Exception as e:  # noqa: BLE001
        return to_contract_second_look(LocalSecondLook(
            status="warn", answer="", detail=f"Could not render the subject for a second look: {e}"))

    try:
        answer = (ask or _ask_namer)(png)
    except Exception as e:  # noqa: BLE001
        return to_contract_second_look(LocalSecondLook(
            status="warn", answer="", detail=f"Second look unavailable: {type(e).__name__}: {e}"[:300]))

    answer = " ".join(answer.split())[:80]
    if not answer:
        return to_contract_second_look(LocalSecondLook(
            status="warn", answer="", detail="Shown only the adapted page, our model could not name anything."))
    if matches(answer, label, synonyms):
        return to_contract_second_look(LocalSecondLook(
            status="pass", answer=answer, detail=f'Shown only the adapted page, our model saw "{answer}".'))
    return to_contract_second_look(LocalSecondLook(
        status="warn", answer=answer,
        detail=f'Shown only the adapted page, our model saw "{answer}", not "{label}". '
               f"This is a weak signal; the teacher's confirmation decides."))
