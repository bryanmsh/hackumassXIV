"""Subject choosing with our own model, and the trust rule. No real model is called, except where marked."""
import logging

import pytest

from pipeline import subjects
from pipeline.subjects import LOCAL_CONFIRMED, SubjectAnswer, SubjectError, choose_subjects, label_crop

NOT_SET_UP = "^The subject finder is not set up on this server$"


def local(*confidences, reason="", page_kind=None):
    kind = page_kind or ("single" if len(confidences) == 1 else "several")
    return SubjectAnswer(page_kind=kind, candidates=[
        {"label": f"thing{i}", "box_2d": [100, 100, 500, 500], "confidence": c, "reason": reason}
        for i, c in enumerate(confidences)])


def named(label, page_kind="single"):
    return SubjectAnswer(page_kind=page_kind, candidates=[
        {"label": label, "box_2d": [100, 100, 500, 500], "confidence": 0.9, "reason": LOCAL_CONFIRMED}])


@pytest.fixture
def model(monkeypatch):
    """model(answer=..., label=..., error=...) sets our model's fake answer; model.calls lists the calls."""
    for name in ("SUBJECT_FINDER", "SUBJECT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    calls = []

    def use(answer=None, label="", error=None):
        def fake_subjects(view_path, text):
            calls.append("subjects")
            if error:
                raise error
            return answer

        def fake_label(png):
            calls.append("label")
            if error:
                raise error
            return label
        monkeypatch.setattr(subjects, "_local_subjects", fake_subjects)
        monkeypatch.setattr(subjects, "_local_label", fake_label)
    use.calls = calls
    return use


def test_one_subject_the_text_names_is_trusted(page_image, model):
    model(local(0.9, reason=LOCAL_CONFIRMED))
    answer = choose_subjects(page_image, "")
    assert answer.trusted and answer.candidates[0].label == "thing0"
    assert subjects.last_subject_route() == {"trusted": True, "reason": 'the page text names "thing0"'}


@pytest.mark.parametrize("answer, reason", [
    (SubjectAnswer(page_kind="scene", candidates=[]), "found nothing"),
    # sure and selected, but the text does not name it: the 4-of-7 wrong Ready pages on Animal Homes
    (local(0.9, reason="Stands out on the page."), 'the page text does not name "thing0"'),
    (local(0.3, reason=LOCAL_CONFIRMED), "would not pre-select one subject (needs_subject, 0 selected)"),
    (local(0.9, 0.8, reason=LOCAL_CONFIRMED), "would not pre-select one subject (ready, 2 selected)"),
])
def test_anything_less_is_not_trusted_but_still_returned(page_image, model, answer, reason):
    model(answer)
    result = choose_subjects(page_image, "")
    assert not result.trusted and result.candidates == answer.candidates
    assert subjects.last_subject_route() == {"trusted": False, "reason": reason}


def test_a_single_page_with_extra_unsure_things_still_counts_as_one(page_image, model):
    model(local(0.9, 0.9, reason=LOCAL_CONFIRMED, page_kind="single"))  # "single" selects only the top one
    assert choose_subjects(page_image, "").trusted


def test_one_subject_the_text_names_alone_is_trusted(page_image, model):
    pytest.importorskip("subject_model.words")
    model(named("crocodile"))
    assert choose_subjects(page_image, "10/12\nCrocodiles live in swamps.").trusted


@pytest.mark.parametrize("label, text, why", [
    ("bear", "9/12\nBears and wolves live in dens.", "it links things"),              # Animal Homes p9
    ("tiger", "11/12\nDeer live in forests.\nAnd so do tigers!", "it links things"),  # p11: the deer is missed
    ("cat", "A cat & a hat.", "it links things"),
    ("bear", "A bear sleeps under a tree.", 'it also names "tree"'),
])
def test_text_about_more_than_one_thing_is_not_trusted(page_image, model, label, text, why):
    pytest.importorskip("subject_model.words")
    model(named(label))
    assert not choose_subjects(page_image, text).trusted
    assert subjects.last_subject_route()["reason"] == f"the page text is about more than one thing ({why})"


def test_a_failing_text_check_is_not_trusted(page_image, model, monkeypatch):
    model(named("crocodile"))

    def broken(text, chosen):
        raise ImportError("no subject_model")
    monkeypatch.setattr(subjects, "_text_names_more", broken)
    assert not choose_subjects(page_image, "Crocodiles live in swamps.").trusted
    assert subjects.last_subject_route()["reason"] == "could not check the page text: ImportError"


def test_the_confirmed_reason_matches_the_subject_model():
    local_module = pytest.importorskip("subject_model.local")
    assert LOCAL_CONFIRMED == local_module.CONFIRMED


@pytest.mark.parametrize("error", [ImportError("no subject_model"), FileNotFoundError("finder.pt"), RuntimeError("x")])
def test_a_missing_or_failing_model_is_a_plain_sentence(page_image, model, error):
    model(error=error)
    with pytest.raises(SubjectError, match=NOT_SET_UP):
        choose_subjects(page_image, "")
    with pytest.raises(SubjectError, match=NOT_SET_UP):
        label_crop(b"png")


def test_missing_weights_fail_with_the_plain_sentence(page_image, monkeypatch):
    pytest.importorskip("torch")
    for name in ("SUBJECT_FINDER", "SUBJECT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NAMER_WEIGHTS", "does-not-exist.pt")
    monkeypatch.setenv("FINDER_WEIGHTS", "does-not-exist.pt")
    with pytest.raises(SubjectError, match=NOT_SET_UP):
        choose_subjects(page_image, "")


def test_the_standin_finds_nothing(page_image, monkeypatch):
    monkeypatch.setenv("SUBJECT_MODEL", "standin")
    answer = choose_subjects(page_image, "")
    assert answer.candidates == [] and not answer.trusted
    assert label_crop(b"png") == ""


@pytest.mark.parametrize("old", ["gemini", "cascade"])
def test_an_old_setting_is_ignored_with_one_warning(page_image, model, monkeypatch, caplog, old):
    monkeypatch.setenv("SUBJECT_FINDER", old)
    monkeypatch.setattr(subjects, "_warned", [])
    model(local(0.9, reason=LOCAL_CONFIRMED))
    with caplog.at_level(logging.WARNING, logger="mirai.subjects"):
        choose_subjects(page_image, "")
        choose_subjects(page_image, "")
    assert model.calls == ["subjects", "subjects"]
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        f"SUBJECT_FINDER={old} is ignored: subjects always come from our own model"]


@pytest.mark.parametrize("found", ["rabbit", ""])  # "": not sure, and the teacher types the name
def test_label_crop_is_our_model(model, found):
    model(label=found)
    assert label_crop(b"png") == found
    assert model.calls == ["label"]
