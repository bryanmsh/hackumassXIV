"""Second look: a separate AI pass names the subject from the adapted page alone.

It shares the AI service with subject choosing, so it is a weak signal and is
only ever a warning. It never raises and never blocks approval.
"""
from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Set

from render._types import LocalSecondLook, to_contract_second_look
from render.core import compose, encode

DEFAULT_MODEL = "gemini-flash-latest"
TIMEOUT_MS = 20_000
PROMPT = ("Name the main object in this picture in one to three words. "
          "Reply with only those words, no punctuation.")
LEVEL2_ON_BLACK = {"colors": ["#FFFFFF"], "background": "#000000", "size": "medium",
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


def _ask_model(png: bytes, model: str, api_key: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=png, mime_type="image/png"), PROMPT],
        config=types.GenerateContentConfig(temperature=0),
    )
    return (resp.text or "").strip()


def second_look(image_path, mask_path, label: str, synonyms: Optional[List[str]] = None,
                ask=None):
    """Contract 2: one AI call. `ask` replaces the model call in tests."""
    synonyms = list(synonyms or [])
    try:
        png = encode(compose(image_path, image_path, mask_path, LEVEL2_ON_BLACK, 2).rgb, "png")
    except Exception as e:  # noqa: BLE001
        return to_contract_second_look(LocalSecondLook(
            status="warn", answer="", detail=f"Could not render the subject for a second look: {e}"))

    try:
        if ask is None:
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                return to_contract_second_look(LocalSecondLook(
                    status="warn", answer="", detail="Second look skipped: no GEMINI_API_KEY is set."))
            model = os.environ.get("SECOND_LOOK_MODEL") or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
            answer = _ask_model(png, model, api_key)
        else:
            answer = ask(png)
    except Exception as e:  # noqa: BLE001
        return to_contract_second_look(LocalSecondLook(
            status="warn", answer="", detail=f"Second look unavailable: {type(e).__name__}: {e}"[:300]))

    answer = " ".join(answer.split())[:80]
    if matches(answer, label, synonyms):
        return to_contract_second_look(LocalSecondLook(
            status="pass", answer=answer, detail=f'Shown only the adapted page, the AI saw "{answer}".'))
    return to_contract_second_look(LocalSecondLook(
        status="warn", answer=answer,
        detail=f'Shown only the adapted page, the AI saw "{answer}", not "{label}". '
               f"This is a weak signal; the teacher's confirmation decides."))
