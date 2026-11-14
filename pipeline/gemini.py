"""The one door to Gemini. Nothing else in the pipeline imports the SDK.

Reads GEMINI_API_KEY and GEMINI_MODEL from the environment on every call.
The key is never printed, logged or put in an error message.
Every failure leaves this module as GeminiError, or RateLimited for a 429.
"""
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

TIMEOUT_S = 20
DEFAULT_MODEL = "gemini-3.8-flash"  # used when GEMINI_MODEL is empty; newest Flash in the live model list on 2026-11-14
MAX_CANDIDATES = 5  # every main subject of the page, not only the first choice
MAX_SYNONYMS = 5
SEED = 0  # the same seed on every call, so the same page is likelier to get the same answer

# Guards on the answer. They hold even when the model ignores the prompt.
SETTING_WORDS = frozenset({"background", "scene", "scenery", "landscape", "forest", "jungle",
                           "woods", "sky", "ground", "grass"})  # where things are, never a subject
INSIDE_FRACTION = 0.8  # one box is "inside" another when this much of it is
GROUP_HOLDS = 2  # a box holding this many other candidates is a group or the setting
DUPLICATE_IOU = 0.8  # two boxes overlapping this much are the same object

# Limits on one call, so a call that goes wrong cannot run up a bill. They sit far above
# normal use (a real answer is a few hundred tokens, a picture-book page a few hundred
# characters) and should never trip in ordinary running.
MAX_OUTPUT_TOKENS = 16384  # thinking plus answer; a cut-off answer becomes a GeminiError
MAX_THINKING_TOKENS = 8192  # thinking counts against the output cap, so this leaves room for the answer
MAX_TEXT_CHARS = 8000  # page text sent with the picture; anything longer is cut

PROMPT = """You are helping adapt a picture-book page for a child with cortical visual impairment.
Find every main subject of this page: each person, animal or object the page is about.
A page can have one main subject or several. Use the page text to decide what matters,
not size. If the text says "The rabbit was hiding under the tree", the rabbit is a main
subject and the tree is not.

things_on_page: first, name every separate person, animal and object you can see, up to 10.

page_kind: "single" if the page is about one thing, "several" if it is about two or
more things of equal importance, "scene" if it is a landscape, a crowd, or has no
one thing the story is about.

candidates: up to 5, most important first. Include every main subject. Do not leave a
main subject out to make room for a minor one. Rules for each candidate:
- It is exactly ONE thing: one person, one animal or one object. The only group allowed
  is things of the same kind that touch or sit together, such as two children playing
  together; give that one candidate. Things that are apart on the page are always
  separate candidates. Never join different kinds of thing in one candidate.
- People count as subjects, the same as animals.
- Never the setting or background: not the forest, sky, ground, grass or scenery.
- label: one or two lowercase words, using the word from the page text when there is one.
- synonyms: up to 5 other names, always including the general kind of thing
  (hornbill: bird).
- box_2d: [ymin, xmin, ymax, xmax], integers from 0 to 1000, tight around that one thing
  and nothing else.
- confidence: 0 to 1, how sure you are this is a main subject of the page.
- reason: one short sentence.

Page text: <<<{text}>>>"""

CROP_PROMPT = ("This is one object cut from a picture-book page. "
               "Name it in one or two lowercase words, as a young child would say it.")


class GeminiError(Exception):
    """Any failed Gemini call: no key, a timeout, a server error, an answer that does not parse."""


class RateLimited(GeminiError):
    """Gemini answered 429. Worth waiting before the retry."""


class GeminiCandidate(BaseModel):
    label: str
    synonyms: list[str] = []
    box_2d: list[int]  # [ymin, xmin, ymax, xmax] on a 0 to 1000 scale
    confidence: float
    reason: str = ""


class SubjectAnswer(BaseModel):
    things_on_page: list[str] = []  # first, so the model looks at everything before it ranks
    page_kind: Literal["single", "several", "scene"]
    candidates: list[GeminiCandidate] = []


class CropLabel(BaseModel):
    label: str


_clients = {}


def _client(key: str):
    """One SDK client per key, made on first use so importing this module needs no SDK."""
    if key not in _clients:
        from google import genai
        _clients[key] = genai.Client(api_key=key)
    return _clients[key]


def _scrub(message: str, key: str) -> str:
    return message.replace(key, "***") if key else message


def _generate(image_png: bytes, prompt: str, schema) -> str:
    """One call: an image and a prompt in, the JSON text out. The only function that touches the SDK."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set")
    from google.genai import errors, types

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0,
        seed=SEED,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        thinking_config=types.ThinkingConfig(thinking_budget=MAX_THINKING_TOKENS),
        # One attempt here: retrying is decided in one place, by the caller.
        http_options=types.HttpOptions(timeout=TIMEOUT_S * 1000,
                                       retry_options=types.HttpRetryOptions(attempts=1)),
    )
    try:
        response = _client(key).models.generate_content(
            model=os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL,
            contents=[types.Part.from_bytes(data=image_png, mime_type="image/png"), prompt],
            config=config,
        )
    except errors.APIError as error:
        message = _scrub(f"Gemini error {error.code}: {error.message}", key)
        raise (RateLimited if error.code == 429 else GeminiError)(message) from None
    except Exception as error:
        raise GeminiError(_scrub(f"{type(error).__name__}: {error}", key)) from None
    candidates = getattr(response, "candidates", None) or []
    finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    if getattr(finish_reason, "name", finish_reason) == "MAX_TOKENS":
        raise GeminiError("Gemini's answer was cut off at the output limit")
    if not response.text:
        raise GeminiError("Gemini returned an empty answer")
    return response.text


def _parse(text: str, schema):
    try:
        return schema.model_validate(json.loads(text))
    except (ValueError, ValidationError):  # json.JSONDecodeError is a ValueError
        raise GeminiError("Gemini's answer did not match the expected JSON") from None


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


def _drop_non_subjects(candidates: list[GeminiCandidate]) -> list[GeminiCandidate]:
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


def choose_subjects(view_path, text: str) -> SubjectAnswer:
    """Ask for every main subject of the page. Candidates come back highest confidence first, at most five."""
    prompt = PROMPT.format(text=text.strip()[:MAX_TEXT_CHARS] or "(none)")
    answer = _parse(_generate(Path(view_path).read_bytes(), prompt, SubjectAnswer), SubjectAnswer)
    for candidate in answer.candidates:
        if len(candidate.box_2d) != 4:
            raise GeminiError("Gemini returned a box that is not four numbers")
        candidate.label = candidate.label.strip().lower()
        candidate.synonyms = [s.strip().lower() for s in candidate.synonyms if s.strip()][:MAX_SYNONYMS]
        candidate.confidence = min(1.0, max(0.0, candidate.confidence))
    answer.candidates = _drop_non_subjects(answer.candidates)[:MAX_CANDIDATES]  # already most confident first
    return answer


def label_crop(png_bytes: bytes) -> str:
    """Name the object in a cropped picture, in lowercase."""
    return _parse(_generate(png_bytes, CROP_PROMPT, CropLabel), CropLabel).label.strip().lower()
