import pytest
from pydantic import ValidationError

from contracts.types import PageResult, Profile, Settings


def test_settings_defaults():
    assert Settings().model_dump() == {"colors": ["#E53935"], "background": "#000000",
        "size": "medium", "position": "center", "text_mode": "off", "outline": "off"}


def test_hex_is_normalized_to_uppercase():
    assert Settings(colors=["#e53935"]).colors == ["#E53935"]


@pytest.mark.parametrize("colors", [[], ["#111111"] * 4, ["red"]])
def test_bad_colors_rejected(colors):
    with pytest.raises(ValidationError):
        Settings(colors=colors)


def test_level_must_be_1_to_4():
    with pytest.raises(ValidationError):
        Profile(id="x", name="Maya", level=5, settings=Settings(), settings_hash="0" * 12)


def test_page_result_rejects_unknown_state():
    with pytest.raises(ValidationError):
        PageResult(state="processing", page_kind=None, candidates=[], selected=None, reason=None)
