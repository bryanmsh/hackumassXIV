"""Keeps examples.json honest: positions are fractions and hashes match the hashing helper."""
import json
from pathlib import Path
from typing import get_args

from contracts.hashing import settings_hash, version_token
from contracts.types import Candidate, CheckItem, PageResult, Profile, SecondLook, Settings

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
    # "outline" is also a profile setting ("off"), so only lists count as positions.
    numbers = [n for d in walk(EXAMPLES) for key in ("box", "point", "outline")
               if isinstance(d.get(key), list) for n in flat(d[key])]
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


def literal_values(annotation):
    """The allowed values of a Literal, also when it is wrapped in `| None`."""
    args = get_args(annotation)
    if not args:
        return [] if annotation is type(None) else [annotation]
    return [v for arg in args for v in literal_values(arg)]


def test_enums_list_every_allowed_value():
    enums = EXAMPLES["_enums"]
    field = lambda model, name: literal_values(model.model_fields[name].annotation)
    assert enums["page.state"] == ["processing"] + field(PageResult, "state")
    assert enums["page.page_kind"] == field(PageResult, "page_kind")
    assert enums["candidate.source"] == field(Candidate, "source")
    assert enums["level"] == field(Profile, "level")
    for name in ("size", "position", "text_mode", "outline"):
        assert enums[f"settings.{name}"] == field(Settings, name)
    assert enums["check.status"] == field(CheckItem, "status")
    assert enums["second_look.status"] == field(SecondLook, "status")
    for api_only in ("book.state", "sheet.approval", "approve.decision", "reader.skipped.reason"):
        assert enums[api_only]


def test_approve_sends_back_the_version_exactly_as_the_sheet_gave_it():
    sheet = {row["page_id"]: row["version"]
             for row in EXAMPLES["GET /api/books/{id}/sheet"]["response"]["pages"]}
    approve = EXAMPLES["POST /api/books/{id}/approve"]
    for page in approve["request"]["pages"]:
        assert page["version"] == sheet[page["page_id"]]
    for stale in approve["errors"]["409"]["stale"]:
        assert set(stale["current_version"]) == {"subject_hash", "settings_hash", "level",
                                                 "render_version", "v"}
