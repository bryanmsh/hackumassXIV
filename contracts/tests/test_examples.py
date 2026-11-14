"""Keeps examples.json honest: positions are fractions and hashes match the hashing helper."""
import json
from pathlib import Path

from contracts.hashing import settings_hash, version_token
from contracts.types import Settings

EXAMPLES = json.loads((Path(__file__).parents[1] / "examples.json").read_text())


def walk(node):
    """Yield every dict anywhere inside the examples."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def flat(value):
    return [n for item in value for n in flat(item)] if isinstance(value, list) else [value]


def test_every_position_is_a_fraction():
    numbers = [n for d in walk(EXAMPLES) for key in ("box", "point", "outline") if key in d
               for n in flat(d[key])]
    assert numbers, "expected at least one position in the examples"
    assert all(0 <= n <= 1 for n in numbers)


def test_profile_hashes_match_the_helper():
    profiles = [d for d in walk(EXAMPLES) if "settings_hash" in d and "settings" in d]
    assert profiles
    for p in profiles:
        assert p["settings_hash"] == settings_hash(Settings(**p["settings"]))


def test_version_tokens_match_the_helper():
    versions = [d for d in walk(EXAMPLES) if "v" in d and "render_version" in d]
    assert versions
    for v in versions:
        assert v["v"] == version_token(
            v["subject_hash"], v["settings_hash"], v["level"], v["render_version"])
