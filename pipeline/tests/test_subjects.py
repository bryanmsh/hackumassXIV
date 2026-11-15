"""SUBJECT_FINDER routing: Gemini, our own subject model, or both in a cascade. No real model is called."""
import json

import pytest

from pipeline import gemini
from pipeline.gemini import GeminiError, SubjectAnswer, choose_subjects, label_crop

GEMINI_ANSWER = json.dumps({"page_kind": "single", "candidates": [
    {"label": "crocodile", "synonyms": ["animal"], "box_2d": [100, 100, 600, 900], "confidence": 0.95}]})


def local(*confidences, reason="", page_kind=None):
    kind = page_kind or ("single" if len(confidences) == 1 else "several")
    return SubjectAnswer(page_kind=kind, candidates=[
        {"label": f"thing{i}", "box_2d": [100, 100, 500, 500], "confidence": c, "reason": reason}
        for i, c in enumerate(confidences)])


CONFIRMED = gemini.LOCAL_CONFIRMED


class Calls(list):
    """Who was asked, in order, plus use_local() to set our model's fake answer."""


@pytest.fixture
def calls(monkeypatch):
    """Fakes for both models; calls lists who was asked, in order."""
    made = Calls()

    def fake_generate(image_png, prompt, schema):
        made.append("gemini")
        return GEMINI_ANSWER if schema is SubjectAnswer else json.dumps({"label": "Crocodile"})
    monkeypatch.setattr(gemini, "_generate", fake_generate)
    for name in ("SUBJECT_FINDER", "SUBJECT_MODEL"):
        monkeypatch.delenv(name, raising=False)

    def use_local(answer=None, label="", error=None):
        def fake_subjects(view_path, text):
            made.append("local")
            if error:
                raise error
            return answer
        def fake_label(png):
            made.append("local")
            if error:
                raise error
            return label
        monkeypatch.setattr(gemini, "_local_subjects", fake_subjects)
        monkeypatch.setattr(gemini, "_local_label", fake_label)
    made.use_local = use_local
    return made


def test_gemini_is_the_default_and_never_asks_ours(page_image, calls):
    calls.use_local(local(0.99))
    assert choose_subjects(page_image, "").candidates[0].label == "crocodile"
    assert calls == ["gemini"] and gemini.last_subject_route()["model"] == "gemini"


def test_local_mode_never_calls_gemini(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "local")
    calls.use_local(local(0.2))
    assert choose_subjects(page_image, "").candidates[0].label == "thing0"
    assert calls == ["local"]


def test_local_mode_without_the_model_fails_with_a_plain_sentence(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "local")
    calls.use_local(error=FileNotFoundError("namer.pt"))
    with pytest.raises(GeminiError, match="^The local subject finder is not set up on this server$"):
        choose_subjects(page_image, "")
    assert calls == ["local"]


def test_cascade_keeps_one_preselected_subject_the_text_names(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "cascade")
    calls.use_local(local(0.9, reason=CONFIRMED))
    assert choose_subjects(page_image, "").candidates[0].label == "thing0"
    assert calls == ["local"]
    assert gemini.last_subject_route() == {"model": "local", "reason": 'the page text names "thing0"'}


@pytest.mark.parametrize("answer, reason", [
    (SubjectAnswer(page_kind="scene", candidates=[]), "found nothing"),
    # sure and selected, but the text does not name it: the 4-of-7 wrong Ready pages on Animal Homes
    (local(0.9, reason="Stands out on the page."), 'the page text does not name "thing0"'),
    # nothing reasonably sure, so the page would ask the teacher anyway
    (local(0.3, reason=CONFIRMED), "would not pre-select one subject (needs_subject, 0 selected)"),
    # several sure subjects: not one pre-selected subject
    (local(0.9, 0.8, reason=CONFIRMED), "would not pre-select one subject (ready, 2 selected)"),
])
def test_cascade_asks_gemini_when_ours_is_not_enough(page_image, calls, monkeypatch, answer, reason):
    monkeypatch.setenv("SUBJECT_FINDER", "cascade")
    calls.use_local(answer)
    assert choose_subjects(page_image, "").candidates[0].label == "crocodile"
    assert calls == ["local", "gemini"]
    assert gemini.last_subject_route() == {"model": "gemini", "reason": reason}


def test_a_single_page_with_extra_unsure_things_still_counts_as_one(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "cascade")
    calls.use_local(local(0.9, 0.9, reason=CONFIRMED, page_kind="single"))  # "single" selects only the top one
    choose_subjects(page_image, "")
    assert calls == ["local"]


def test_the_confirmed_reason_matches_the_subject_model():
    local_module = pytest.importorskip("subject_model.local")
    assert gemini.LOCAL_CONFIRMED == local_module.CONFIRMED


@pytest.mark.parametrize("error", [ImportError("no subject_model"), FileNotFoundError("finder.pt"), RuntimeError("x")])
def test_cascade_uses_gemini_when_ours_is_missing_or_fails(page_image, calls, monkeypatch, error):
    monkeypatch.setenv("SUBJECT_FINDER", "cascade")
    calls.use_local(error=error)
    assert choose_subjects(page_image, "").candidates[0].label == "crocodile"
    assert gemini.last_subject_route()["reason"] == f"our model unavailable: {type(error).__name__}"


def test_this_branch_has_no_subject_model_and_the_cascade_still_answers(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "cascade")  # the real import runs and fails where subject_model is absent
    monkeypatch.setenv("NAMER_WEIGHTS", "does-not-exist.pt")
    monkeypatch.setenv("FINDER_WEIGHTS", "does-not-exist.pt")
    assert choose_subjects(page_image, "").candidates[0].label == "crocodile"
    assert gemini.last_subject_route()["model"] == "gemini"


def test_the_standin_always_escalates(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "cascade")
    monkeypatch.setenv("SUBJECT_MODEL", "standin")
    assert choose_subjects(page_image, "").candidates[0].label == "crocodile"
    assert gemini.last_subject_route() == {"model": "gemini", "reason": "found nothing"}


def test_a_mistyped_setting_fails_loudly(page_image, calls, monkeypatch):
    monkeypatch.setenv("SUBJECT_FINDER", "locall")
    with pytest.raises(GeminiError, match="SUBJECT_FINDER must be"):
        choose_subjects(page_image, "")
    assert calls == []


@pytest.mark.parametrize("finder, local_label, expected, asked", [
    ("gemini", "rabbit", "crocodile", ["gemini"]),
    ("local", "", "", ["local"]),  # not sure, and nothing behind it: the teacher types the name
    ("cascade", "rabbit", "rabbit", ["local"]),
    ("cascade", "", "crocodile", ["local", "gemini"]),
])
def test_label_crop_routing(calls, monkeypatch, finder, local_label, expected, asked):
    monkeypatch.setenv("SUBJECT_FINDER", finder)
    calls.use_local(label=local_label)
    assert label_crop(b"png") == expected
    assert calls == asked
