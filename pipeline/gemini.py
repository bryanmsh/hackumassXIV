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
DEFAULT_MODEL = "gemini-flash-latest"  # used when GEMINI_MODEL is empty; confirm against the live model list
MAX_CANDIDATES = 3
MAX_SYNONYMS = 5

PROMPT = """You are helping adapt a picture-book page for a child with cortical visual impairment.
Find the subject of this page: the one object the story is about on this page, not the
largest thing in the picture. Use the page text to decide. If the text says "The rabbit
was hiding under the tree", the subject is the rabbit.

page_kind: "single" if the page is about one object, "several" if it is about two or
more objects of equal importance, "scene" if it is a landscape, a crowd, or has no
object the story is about.

candidates: up to 3, most likely first. For each:
- label: one or two lowercase words, using the word from the page text when there is one.
- synonyms: up to 5 other names, always including the general kind of thing
  (hornbill: bird).
- box_2d: [ymin, xmin, ymax, xmax], integers from 0 to 1000, tight around the whole object.
- confidence: 0 to 1, how sure you are this is the subject.
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
    if not response.text:
        raise GeminiError("Gemini returned an empty answer")
    return response.text


def _parse(text: str, schema):
    try:
        return schema.model_validate(json.loads(text))
    except (ValueError, ValidationError):  # json.JSONDecodeError is a ValueError
        raise GeminiError("Gemini's answer did not match the expected JSON") from None


def choose_subjects(view_path, text: str) -> SubjectAnswer:
    """Ask what this page is about. Candidates come back highest confidence first, at most three."""
    prompt = PROMPT.format(text=text.strip() or "(none)")
    answer = _parse(_generate(Path(view_path).read_bytes(), prompt, SubjectAnswer), SubjectAnswer)
    for candidate in answer.candidates:
        if len(candidate.box_2d) != 4:
            raise GeminiError("Gemini returned a box that is not four numbers")
        candidate.label = candidate.label.strip().lower()
        candidate.synonyms = [s.strip().lower() for s in candidate.synonyms if s.strip()][:MAX_SYNONYMS]
        candidate.confidence = min(1.0, max(0.0, candidate.confidence))
    answer.candidates = sorted(answer.candidates, key=lambda c: c.confidence, reverse=True)[:MAX_CANDIDATES]
    return answer


def label_crop(png_bytes: bytes) -> str:
    """Name the object in a cropped picture, in lowercase."""
    return _parse(_generate(png_bytes, CROP_PROMPT, CropLabel), CropLabel).label.strip().lower()
