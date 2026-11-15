"""Synonyms, the word lists, and matching class names against page text."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

_DATA = json.loads((Path(__file__).parent / "words.json").read_text(encoding="utf-8"))
SYNONYMS: dict[str, list[str]] = {name: list(others) for name, others in _DATA["synonyms"].items()}
NEVER_A_LABEL = frozenset(_DATA["never_a_label"])  # a guess to skip; the blob stays
NOT_A_SUBJECT = frozenset(_DATA["not_a_subject"])  # the blob is not a thing at all
GENERAL = frozenset(_DATA["general"])  # general-kind words, which confirm only a blob's first guess

IRREGULAR = {"child": "children", "mouse": "mice", "goose": "geese", "man": "men", "woman": "women",
             "person": "people", "foot": "feet", "tooth": "teeth", "leaf": "leaves", "wolf": "wolves",
             "knife": "knives", "calf": "calves", "snowman": "snowmen"}
_LETTERS = re.compile(r"[^\W\d_]+")


def forms(word: str) -> set[str]:
    """A lowercase word and its plurals."""
    word = word.lower()
    found = {word, word + "s", word + "es"}
    if len(word) > 1 and word.endswith("y") and word[-2] not in "aeiou":
        found.add(word[:-1] + "ies")
    if word in IRREGULAR:
        found.add(IRREGULAR[word])
    return found


def _words(text: str) -> list[str]:
    """Lowercase words, split on anything that is not a letter; ligatures read as letters."""
    return _LETTERS.findall(unicodedata.normalize("NFKC", text).lower())


def match(text: str, names) -> str | None:
    """The first of `names` that appears in `text` as whole words, as written or plural; else None."""
    tokens = _words(text)
    for name in names:
        parts = [forms(part) for part in _words(name)]
        if not parts:
            continue
        for start in range(len(tokens) - len(parts) + 1):
            if all(tokens[start + i] in allowed for i, allowed in enumerate(parts)):
                return name
    return None
