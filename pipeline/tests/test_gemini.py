"""Offline tests: the SDK is never reached. `_generate` or `_client` is replaced in every test."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline import gemini
from pipeline.gemini import GeminiError, RateLimited, SubjectAnswer, choose_subjects, label_crop


def candidate(label="rabbit", confidence=0.9, box=(100, 200, 500, 600), synonyms=("bunny", "animal")):
    return {"label": label, "synonyms": list(synonyms), "box_2d": list(box),
            "confidence": confidence, "reason": "named in the text"}


def answer(*candidates, page_kind="single"):
    return json.dumps({"page_kind": page_kind, "candidates": list(candidates)})


@pytest.fixture
def reply(monkeypatch):
    """reply(text) makes the next Gemini call return `text`; reply.calls records what was sent."""
    calls = []

    def set_reply(text):
        def fake(image_png, prompt, schema):
            calls.append({"image": image_png, "prompt": prompt, "schema": schema})
            return text
        monkeypatch.setattr(gemini, "_generate", fake)

    set_reply.calls = calls
    return set_reply


def test_parses_answer(page_image, reply):
    reply(answer(candidate("rabbit", 0.9), candidate("tree", 0.3, box=(0, 600, 900, 1000), synonyms=["plant"])))
    result = choose_subjects(page_image, "The rabbit sat.")
    assert isinstance(result, SubjectAnswer)
    assert result.page_kind == "single"
    assert [c.label for c in result.candidates] == ["rabbit", "tree"]
    first = result.candidates[0]
    assert first.synonyms == ["bunny", "animal"]
    assert first.box_2d == [100, 200, 500, 600]
    assert first.confidence == 0.9
    assert first.reason == "named in the text"


def test_sends_the_image_and_the_page_text(page_image, reply):
    reply(answer(candidate()))
    choose_subjects(page_image, "The rabbit sat.")
    call = reply.calls[0]
    assert call["image"] == Path(page_image).read_bytes()
    assert "Page text: <<<The rabbit sat.>>>" in call["prompt"]
    assert call["schema"] is SubjectAnswer


def test_empty_page_text_is_sent_as_none(page_image, reply):
    reply(answer(candidate()))
    choose_subjects(page_image, "  ")
    assert "Page text: <<<(none)>>>" in reply.calls[0]["prompt"]


def test_trims_to_three_candidates_and_five_synonyms(page_image, reply):
    seven = ["a", "b", "c", "d", "e", "f", "g"]
    reply(answer(candidate("low", 0.2), candidate("top", 0.9, synonyms=seven),
                 candidate("mid", 0.6), candidate("lowest", 0.1)))
    result = choose_subjects(page_image, "")
    assert [c.label for c in result.candidates] == ["top", "mid", "low"]  # highest confidence first
    assert result.candidates[0].synonyms == ["a", "b", "c", "d", "e"]


def test_confidence_clamped_to_0_1(page_image, reply):
    reply(answer(candidate("a", 1.4), candidate("b", -0.2)))
    result = choose_subjects(page_image, "")
    assert [c.confidence for c in result.candidates] == [1.0, 0.0]


def test_labels_and_synonyms_are_tidied(page_image, reply):
    reply(answer(candidate("  Rabbit ", synonyms=[" Bunny", "", "animal "])))
    first = choose_subjects(page_image, "").candidates[0]
    assert first.label == "rabbit"
    assert first.synonyms == ["bunny", "animal"]


def test_scene_with_no_candidates_is_valid(page_image, reply):
    reply(answer(page_kind="scene"))
    result = choose_subjects(page_image, "")
    assert result.page_kind == "scene"
    assert result.candidates == []


@pytest.mark.parametrize("text", ["not json", "", "[]", json.dumps({"page_kind": "poster", "candidates": []})])
def test_bad_json_raises_gemini_error(page_image, reply, text):
    reply(text)
    with pytest.raises(GeminiError):
        choose_subjects(page_image, "")


def test_wrong_box_length_raises_gemini_error(page_image, reply):
    reply(answer(candidate(box=(1, 2, 3))))
    with pytest.raises(GeminiError):
        choose_subjects(page_image, "")


def test_missing_key_raises_gemini_error(page_image, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiError) as error:
        choose_subjects(page_image, "")
    assert "GEMINI_API_KEY" in str(error.value)
    assert not isinstance(error.value, RateLimited)


def fake_client(monkeypatch, behaviour):
    """Replace the SDK client. `behaviour` is called in place of generate_content."""
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        return behaviour()

    monkeypatch.setenv("GEMINI_API_KEY", "secret123")
    monkeypatch.setattr(gemini, "_client", lambda key: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)))
    return calls


def raiser(error):
    def behaviour():
        raise error
    return behaviour


def test_sdk_429_becomes_rate_limited(page_image, monkeypatch):
    from google.genai import errors

    fake_client(monkeypatch, raiser(errors.APIError(429, {"error": {"message": "quota"}})))
    with pytest.raises(RateLimited):
        choose_subjects(page_image, "")


def test_sdk_500_becomes_gemini_error(page_image, monkeypatch):
    from google.genai import errors

    fake_client(monkeypatch, raiser(errors.APIError(500, {"error": {"message": "boom"}})))
    with pytest.raises(GeminiError) as error:
        choose_subjects(page_image, "")
    assert not isinstance(error.value, RateLimited)
    assert "500" in str(error.value)


def test_any_other_sdk_failure_becomes_gemini_error_without_the_key(page_image, monkeypatch):
    fake_client(monkeypatch, raiser(TimeoutError("timed out calling https://x/?key=secret123")))
    with pytest.raises(GeminiError) as error:
        choose_subjects(page_image, "")
    assert "secret123" not in str(error.value)
    assert "timed out" in str(error.value)


def test_call_uses_json_schema_model_and_20_second_timeout(page_image, monkeypatch):
    calls = fake_client(monkeypatch, lambda: SimpleNamespace(text=answer(candidate())))
    monkeypatch.setenv("GEMINI_MODEL", "some-flash-model")
    choose_subjects(page_image, "The rabbit sat.")
    call = calls[0]
    assert call["model"] == "some-flash-model"
    config = call["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is SubjectAnswer
    assert config.http_options.timeout == 20_000  # milliseconds


def test_default_model_when_setting_is_empty(page_image, monkeypatch):
    calls = fake_client(monkeypatch, lambda: SimpleNamespace(text=answer(candidate())))
    monkeypatch.setenv("GEMINI_MODEL", "")
    choose_subjects(page_image, "")
    assert calls[0]["model"] == gemini.DEFAULT_MODEL


def test_empty_reply_raises_gemini_error(page_image, monkeypatch):
    fake_client(monkeypatch, lambda: SimpleNamespace(text=None))
    with pytest.raises(GeminiError):
        choose_subjects(page_image, "")


def test_label_crop_returns_a_tidy_label(reply):
    reply(json.dumps({"label": "  Red Ball "}))
    assert label_crop(b"png-bytes") == "red ball"
    assert reply.calls[0]["image"] == b"png-bytes"


def test_label_crop_bad_reply_raises_gemini_error(reply):
    reply("nope")
    with pytest.raises(GeminiError):
        label_crop(b"png-bytes")
