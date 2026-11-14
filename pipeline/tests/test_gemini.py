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


def test_trims_to_five_candidates_and_five_synonyms(page_image, reply):
    seven = ["a", "b", "c", "d", "e", "f", "g"]
    boxes = [(0, i * 100, 90, i * 100 + 90) for i in range(7)]  # seven separate objects in a row
    confidences = [0.2, 0.9, 0.6, 0.1, 0.8, 0.5, 0.7]
    reply(answer(*[candidate(f"thing{i}", confidences[i], box=boxes[i], synonyms=seven) for i in range(7)]))
    result = choose_subjects(page_image, "")
    assert [c.confidence for c in result.candidates] == [0.9, 0.8, 0.7, 0.6, 0.5]  # the five most confident
    assert result.candidates[0].synonyms == ["a", "b", "c", "d", "e"]


def test_confidence_clamped_to_0_1(page_image, reply):
    reply(answer(candidate("a", 1.4), candidate("b", -0.2, box=(700, 700, 900, 900))))  # two separate objects
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


# --- limits on a single call, so one that goes wrong cannot run up a bill ---
# They are set far above normal use: a real answer is a few hundred tokens and a
# picture-book page a few hundred characters. They should never trip in a demo.

def test_call_caps_output_and_thinking(page_image, monkeypatch):
    calls = fake_client(monkeypatch, lambda: SimpleNamespace(text=answer(candidate())))
    choose_subjects(page_image, "The rabbit sat.")
    config = calls[0]["config"]
    assert config.max_output_tokens == gemini.MAX_OUTPUT_TOKENS
    assert config.thinking_config.thinking_budget == gemini.MAX_THINKING_TOKENS
    # thinking counts against the output cap, so there must always be room left for the answer
    assert gemini.MAX_OUTPUT_TOKENS - gemini.MAX_THINKING_TOKENS >= 4000
    assert gemini.MAX_THINKING_TOKENS >= 8000


def test_label_crop_has_the_same_caps(monkeypatch):
    calls = fake_client(monkeypatch, lambda: SimpleNamespace(text=json.dumps({"label": "ball"})))
    label_crop(b"png-bytes")
    assert calls[0]["config"].max_output_tokens == gemini.MAX_OUTPUT_TOKENS


def test_very_long_page_text_is_cut_before_sending(page_image, reply):
    reply(answer(candidate()))
    text = "a" * gemini.MAX_TEXT_CHARS + "ZZZ-past-the-limit"
    choose_subjects(page_image, text)
    prompt = reply.calls[0]["prompt"]
    assert "a" * gemini.MAX_TEXT_CHARS in prompt
    assert "ZZZ" not in prompt
    assert gemini.MAX_TEXT_CHARS >= 5000


def test_ordinary_page_text_is_sent_whole(page_image, reply):
    reply(answer(candidate()))
    text = "The rabbit was hiding under the tree. " * 20  # 760 characters: a long page for a picture book
    choose_subjects(page_image, text)
    assert text.strip() in reply.calls[0]["prompt"]


def test_answer_cut_off_at_the_output_cap_is_a_clear_gemini_error(page_image, monkeypatch):
    from google.genai import types

    cut_off = SimpleNamespace(text='{"page_kind": "sin',
                              candidates=[SimpleNamespace(finish_reason=types.FinishReason.MAX_TOKENS)])
    fake_client(monkeypatch, lambda: cut_off)
    with pytest.raises(GeminiError) as error:
        choose_subjects(page_image, "")
    assert "output limit" in str(error.value)


def test_empty_answer_at_the_output_cap_says_so(page_image, monkeypatch):
    from google.genai import types

    fake_client(monkeypatch, lambda: SimpleNamespace(
        text=None, candidates=[SimpleNamespace(finish_reason=types.FinishReason.MAX_TOKENS)]))
    with pytest.raises(GeminiError) as error:
        choose_subjects(page_image, "")
    assert "output limit" in str(error.value)


# --- finding every main subject, one clean object each ---

BIRD = (200, 330, 300, 370)       # [ymin, xmin, ymax, xmax] on 0 to 1000
ANTS = (900, 380, 990, 470)
CHILDREN = (580, 520, 690, 620)


def labels(result):
    return [c.label for c in result.candidates]


def test_answer_may_list_what_is_on_the_page_first(page_image, reply):
    reply(json.dumps({"things_on_page": ["boy", "girl", "woodpecker"], "page_kind": "single",
                      "candidates": [candidate()]}))
    assert choose_subjects(page_image, "").things_on_page == ["boy", "girl", "woodpecker"]
    assert list(SubjectAnswer.model_fields)[0] == "things_on_page"  # listed before anything is ranked


def test_prompt_asks_for_every_main_subject_up_to_five(page_image, reply):
    reply(answer(candidate()))
    choose_subjects(page_image, "")
    prompt = reply.calls[0]["prompt"]
    assert "up to 5" in prompt
    assert "every main subject" in prompt


@pytest.mark.parametrize("label", ["forest", "dense forest", "the sky", "background", "Grass"])
def test_the_setting_is_not_a_subject(page_image, reply, label):
    reply(answer(candidate("woodpecker", 0.6, box=BIRD), candidate(label, 0.9, box=(400, 400, 950, 850))))
    assert labels(choose_subjects(page_image, "")) == ["woodpecker"]


@pytest.mark.parametrize("label", ["grasshopper", "tree", "nest", "burrow"])
def test_words_that_only_look_like_settings_are_kept(page_image, reply, label):
    reply(answer(candidate(label, 0.9, box=BIRD)))
    assert labels(choose_subjects(page_image, "")) == [label]


def test_a_box_holding_two_other_candidates_is_a_group_and_is_dropped(page_image, reply):
    tall = (190, 320, 995, 480)  # runs from the bird down to the ants, as in the demo page failure
    reply(answer(candidate("bird and lizard", 0.9, box=tall), candidate("bird", 0.5, box=BIRD),
                 candidate("ants", 0.4, box=ANTS), candidate("children", 0.3, box=CHILDREN)))
    assert labels(choose_subjects(page_image, "")) == ["bird", "ants", "children"]


def test_a_box_holding_one_other_candidate_is_kept(page_image, reply):
    nest = (150, 300, 400, 500)  # an animal's home is a real subject
    reply(answer(candidate("nest", 0.6, box=nest), candidate("bird", 0.8, box=BIRD)))
    assert labels(choose_subjects(page_image, "")) == ["bird", "nest"]


def test_overlapping_but_not_containing_boxes_are_kept(page_image, reply):
    reply(answer(candidate("girl", 0.6, box=(580, 520, 690, 575)), candidate("boy", 0.6, box=(580, 560, 690, 620)),
                 candidate("woodpecker", 0.5, box=BIRD)))
    assert sorted(labels(choose_subjects(page_image, ""))) == ["boy", "girl", "woodpecker"]


def test_near_duplicate_boxes_keep_the_more_confident(page_image, reply):
    reply(answer(candidate("bird", 0.5, box=BIRD), candidate("woodpecker", 0.7, box=(202, 331, 299, 369)),
                 candidate("ants", 0.4, box=ANTS)))
    assert labels(choose_subjects(page_image, "")) == ["woodpecker", "ants"]


def test_guards_run_before_the_trim_so_a_dropped_one_frees_a_place(page_image, reply):
    boxes = [(0, i * 150, 90, i * 150 + 90) for i in range(5)]
    reply(answer(candidate("forest", 0.99, box=(0, 0, 1000, 1000)),
                 *[candidate(f"thing{i}", 0.5 - i * 0.05, box=boxes[i]) for i in range(5)]))
    assert labels(choose_subjects(page_image, "")) == [f"thing{i}" for i in range(5)]


def test_zero_area_boxes_do_not_break_the_guards(page_image, reply):
    reply(answer(candidate("speck", 0.9, box=(500, 500, 500, 500)), candidate("bird", 0.5, box=BIRD)))
    assert labels(choose_subjects(page_image, "")) == ["speck", "bird"]


def test_every_call_uses_the_same_fixed_seed(page_image, monkeypatch):
    """Measured live: with the seed, four runs of one page gave the identical answer."""
    calls = fake_client(monkeypatch, lambda: SimpleNamespace(text=answer(candidate())))
    choose_subjects(page_image, "")
    monkeypatch.setattr(gemini, "_client", lambda key: SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(text=json.dumps({"label": "ball"})))))
    label_crop(b"png-bytes")
    assert [call["config"].seed for call in calls] == [gemini.SEED, gemini.SEED]
