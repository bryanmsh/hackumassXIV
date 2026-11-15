import cv2
import numpy as np
import pytest
from pipeline.gemini import SubjectAnswer, _drop_non_subjects
from pipeline.process import SELECT_MIN_CONFIDENCE, decide_state
from subject_model import local

SCENE = {"things_on_page": [], "page_kind": "scene", "candidates": []}


@pytest.fixture
def view(tmp_path):
    path = tmp_path / "view.png"
    cv2.imwrite(str(path), np.full((500, 1000, 3), 255, np.uint8))
    return path


@pytest.fixture
def small_words(monkeypatch):
    monkeypatch.setattr(local, "SYNONYMS", {"dog": ["puppy", "animal"], "rabbit": ["bunny", "animal"],
                                            "owl": ["bird", "animal"], "cat": ["kitten", "animal"],
                                            "tree": ["plant"]})
    monkeypatch.setattr(local, "GENERAL", frozenset({"animal", "bird", "plant"}))
    monkeypatch.setattr(local, "NEVER_A_LABEL", frozenset({"hand"}))
    monkeypatch.setattr(local, "NOT_A_SUBJECT", frozenset({"squiggle", "text"}))


def blob(x0, y0, x1, y1):
    mask = np.zeros((500, 1000), bool)
    mask[y0:y1, x0:x1] = True
    return (x0, y0, x1, y1), mask


def names(*answers):
    queue = iter(answers)
    return lambda image, mask: list(next(queue))


def pairs(answer):
    return [(c["label"], c["confidence"]) for c in answer["candidates"]]


def two_blobs(image):
    return [blob(100, 50, 300, 250), blob(600, 100, 900, 400)]


def one_blob(image):
    return [blob(0, 0, 500, 500)]


def guesses():
    return names([("dog", 0.5), ("rabbit", 0.3), ("cat", 0.1)], [("owl", 0.9), ("cat", 0.05)])


def test_text_picks_the_name_and_orders_by_confidence(view, small_words):
    answer = local.choose_subjects(view, "The rabbit saw a bird.", find=two_blobs, name=guesses())
    SubjectAnswer.model_validate(answer)
    assert answer["page_kind"] == "several" and answer["things_on_page"] == ["dog", "owl"]
    first, second = answer["candidates"]
    assert first == {"label": "bird", "synonyms": ["owl", "animal"], "box_2d": [200, 600, 800, 900],
                     "confidence": 0.96, "reason": "Stands out on the page and the text names it."}
    assert second["label"] == "rabbit" and second["synonyms"] == ["bunny", "animal"]
    assert second["box_2d"] == [100, 100, 500, 300] and second["confidence"] == 0.72


def test_a_name_goes_to_one_blob_unless_it_is_their_first_guess(view, small_words):
    answer = local.choose_subjects(view, "The rabbit ran.", find=two_blobs,
                                   name=names([("cat", 0.5), ("rabbit", 0.15)], [("rabbit", 0.6), ("dog", 0.2)]))
    assert pairs(answer) == [("rabbit", 0.84), ("cat", 0.4)]
    assert answer["candidates"][1]["reason"] == "Stands out on the page."
    both = local.choose_subjects(view, "The rabbits ran.", find=two_blobs,
                                 name=names([("rabbit", 0.6)], [("rabbit", 0.5)]))
    assert pairs(both) == [("rabbit", 0.84), ("rabbit", 0.8)]


def test_a_general_word_or_an_unlikely_guess_is_not_confirmed(view, small_words):
    hungry = "The animals were hungry."
    assert pairs(local.choose_subjects(view, hungry, find=one_blob,
                                       name=names([("tree", 0.35), ("rabbit", 0.2)]))) == [("tree", 0.28)]
    assert pairs(local.choose_subjects(view, "The rabbit hid.", find=one_blob,
                                       name=names([("tree", 0.5), ("rabbit", 0.05)]))) == [("tree", 0.4)]
    first = local.choose_subjects(view, hungry, find=one_blob, name=names([("rabbit", 0.35), ("tree", 0.2)]))
    assert pairs(first) == [("animal", 0.74)] and first["candidates"][0]["synonyms"] == ["rabbit", "bunny"]


def test_no_text_uses_each_top_guess(view, small_words):
    answer = local.choose_subjects(view, "", find=two_blobs, name=guesses())
    assert pairs(answer) == [("owl", 0.72), ("dog", 0.4)]
    assert answer["candidates"][0]["reason"] == "Stands out on the page."


def test_nothing_found_is_a_scene(view, small_words):
    assert local.choose_subjects(view, "A quiet morning.", find=lambda image: [], name=names()) == SCENE


def test_one_subject_is_single(view, small_words):
    answer = local.choose_subjects(view, "", find=one_blob, name=names([("cat", 0.7)]))
    assert answer["page_kind"] == "single" and answer["candidates"][0]["box_2d"] == [0, 0, 1000, 500]


def test_a_guess_that_is_never_a_label_is_skipped_but_the_blob_stays(view, small_words):
    answer = local.choose_subjects(view, "", find=one_blob, name=names([("hand", 0.6), ("cat", 0.3)]))
    assert pairs(answer) == [("cat", 0.24)]
    assert local.choose_subjects(view, "", find=one_blob, name=names([("hand", 0.9)])) == SCENE


def test_a_blob_that_is_mostly_printed_words_or_marks_is_dropped(view, small_words):
    answer = local.choose_subjects(view, "The cat sat.", find=two_blobs,
                                   name=names([("text", 0.4), ("squiggle", 0.2), ("cat", 0.3)], [("cat", 0.7)]))
    assert pairs(answer) == [("cat", 0.88)] and answer["page_kind"] == "single"
    assert answer["candidates"][0]["box_2d"] == [200, 600, 800, 900] and answer["things_on_page"] == ["cat"]
    kept = local.choose_subjects(view, "", find=one_blob, name=names([("squiggle", 0.4), ("cat", 0.3)]))
    assert pairs(kept) == [("cat", 0.24)]                             # under DROP_AT the blob stays


def test_at_most_five_candidates(view, small_words):
    seven = lambda image: [blob(i * 100, 0, i * 100 + 90, 90) for i in range(7)]
    answer = local.choose_subjects(view, "", find=seven, name=names(*[[("cat", 0.9)]] * 7))
    assert len(answer["candidates"]) == 5


def test_the_pipeline_guard_leaves_the_answer_unchanged(view, small_words):
    nested = lambda image: [blob(100, 50, 900, 450), blob(200, 100, 300, 200), blob(600, 300, 700, 400)]
    answer = local.choose_subjects(view, "", find=nested,
                                   name=names([("cat", 0.7)], [("dog", 0.3)], [("owl", 0.2)]))
    assert pairs(answer) == [("cat", 0.56), ("dog", 0.24)]            # the big one stays; the least sure small one goes
    kept = _drop_non_subjects(SubjectAnswer.model_validate(answer).candidates)
    assert [c.label for c in kept] == ["cat", "dog"]


def test_what_the_pipeline_does_with_the_answers(view, small_words):
    def state(text, *guess_lists):
        find = lambda image: [blob(100 + 300 * i, 50, 300 + 300 * i, 250) for i in range(len(guess_lists))]
        answer = SubjectAnswer.model_validate(local.choose_subjects(view, text, find=find, name=names(*guess_lists)))
        return decide_state(answer.page_kind, answer.candidates)[:2]
    assert SELECT_MIN_CONFIDENCE == 0.5
    assert state("The rabbit ran.", [("rabbit", 0.3)]) == ("ready", [0])              # confirmed: 0.72
    assert state("", [("rabbit", 0.5)]) == ("needs_subject", [])                      # 0.4: the teacher is asked
    assert state("The rabbits ran.", [("rabbit", 0.6)], [("rabbit", 0.5)]) == ("ready", [0, 1])   # two: asked, with a combined cut-out


def test_the_cap_keeps_every_page_for_the_teacher(view, small_words, monkeypatch):
    monkeypatch.setattr(local, "CONFIDENCE_CAP", 0.49)
    answer = local.choose_subjects(view, "The rabbit saw a bird.", find=two_blobs, name=guesses())
    assert [c["confidence"] for c in answer["candidates"]] == [0.49, 0.49]


def test_find_and_name_get_rgb(tmp_path, small_words):
    cv2.imwrite(str(tmp_path / "red.png"), np.full((50, 100, 3), (0, 0, 255), np.uint8))     # OpenCV writes BGR
    seen = []
    def find(image):
        seen.append(image[0, 0].tolist())
        return []
    local.choose_subjects(tmp_path / "red.png", "", find=find, name=names())
    assert seen == [[255, 0, 0]]


def test_local_answer_is_what_the_hook_returns(view, monkeypatch):
    def candidate(label, box_2d, confidence):
        return {"label": label, "synonyms": [], "box_2d": box_2d, "confidence": confidence, "reason": ""}
    raw = {"things_on_page": ["cat"], "page_kind": "single",
           "candidates": [candidate("forest", [500, 500, 900, 900], 0.9), candidate("cat", [0, 0, 400, 400], 0.7)]}
    monkeypatch.setattr(local, "choose_subjects", lambda view_path, text: raw)
    answer = local.local_answer(view, "")
    assert isinstance(answer, SubjectAnswer) and [c.label for c in answer.candidates] == ["cat"]   # the guard ran


def test_label_crop_names_only_what_the_namer_is_sure_of(small_words, view):
    png = open(view, "rb").read()
    assert local.label_crop(png, name=lambda image, mask=None: [("dog", 0.6), ("hand", 0.2)]) == "dog"
    assert local.label_crop(png, name=lambda image, mask=None: [("hand", 0.5), ("dog", 0.3)]) == ""
    assert local.label_crop(png, name=lambda image, mask=None: []) == ""
