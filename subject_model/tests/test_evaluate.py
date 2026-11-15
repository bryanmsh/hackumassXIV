import json
import pytest
from pipeline.gemini import SubjectAnswer
from subject_model import evaluate
from subject_model.evaluate import box_iou, judge, load_labels, outcome, page_text, score

NOTHING = SubjectAnswer.model_validate({"page_kind": "scene"})
HAND = (100, 100, 300, 200)                               # on a 400 by 300 page
HERE, AWAY = [333, 250, 667, 750], [0, 0, 100, 100]       # the same rectangle as HAND, and a far corner
DOG, THERE = (300, 0, 400, 100), [0, 750, 333, 1000]     # a second subject at the top right, and its box_2d


def answer(label, synonyms, box_2d, confidence=0.9):
    return SubjectAnswer.model_validate({"things_on_page": [label], "page_kind": "single", "candidates": [
        {"label": label, "synonyms": synonyms, "box_2d": box_2d, "confidence": confidence, "reason": ""}]})


def two(first, second):
    both = first.model_copy(deep=True)
    both.candidates.append(second.candidates[0])
    both.page_kind = "several"
    return both


def test_box_iou():
    assert box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert box_iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)
    assert box_iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_judge_counts_subjects_found_and_named_and_the_first_choice():
    ball = [("ball", HAND)]
    right = answer("toy", ["ball", "thing"], HERE)
    assert judge(right, ball, 400, 300) == (1, True, 1)
    assert judge(answer("dog", ["animal"], HERE), ball, 400, 300) == (1, True, 0)
    assert judge(answer("ball", [], AWAY), ball, 400, 300) == (0, False, 0)
    assert judge(NOTHING, ball, 400, 300) == (0, False, 0)
    assert judge(two(answer("words", [], AWAY), right), ball, 400, 300) == (1, False, 1)


def test_every_main_subject_counts_and_the_first_choice_may_be_any_of_them():
    girl_and_dog = [("girl", HAND), ("dog", DOG)]
    both = two(answer("dog", ["puppy"], THERE), answer("person", ["child", "girl"], HERE))
    assert judge(both, girl_and_dog, 400, 300) == (2, True, 2)
    assert judge(answer("person", ["child", "girl"], HERE), girl_and_dog, 400, 300) == (1, True, 1)
    assert judge(answer("cat", [], AWAY), girl_and_dog, 400, 300) == (0, False, 0)


def test_outcome_is_what_the_teacher_gets():
    hand = [HAND]
    assert outcome(answer("ball", [], HERE), hand, 400, 300) == "ready_right"
    assert outcome(answer("ball", [], AWAY), hand, 400, 300) == "ready_wrong"
    assert outcome(answer("ball", [], HERE, confidence=0.4), hand, 400, 300) == "asked"
    assert outcome(two(answer("ball", [], HERE), answer("dog", [], AWAY)), hand, 400, 300) == "asked"
    assert outcome(NOTHING, hand, 400, 300) == "nothing"
    assert outcome(answer("dog", [], THERE), [HAND, DOG], 400, 300) == "ready_right"    # any main subject


def test_score_counts_and_writes_results(testset, monkeypatch):
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: answer("ball", ["toy"], HERE))
    result = score(testset, modes=("local",))
    assert result["total"] == 1 and result["subjects"] == 1 and result["candidates"] == {"local": 1}
    assert result["found"] == result["first"] == result["named"] == {"local": 1}
    assert result["outcomes"] == {"local": {"ready_right": 1, "ready_wrong": 0, "asked": 0, "nothing": 0}}
    assert result["pages"][0]["labels"] == {"local": ["ball"]} and result["pages"][0]["subjects"] == ["ball"]
    assert json.load(open(testset / "results_subjects.json")) == result


def test_a_page_with_two_subjects_counts_both(testset, monkeypatch):
    with open(testset / "labels.csv", "a") as f:
        f.write("ball,dog,300,0,400,100,\n")
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: answer("ball", ["toy"], HERE))
    result = score(testset, modes=("local",))
    assert result["total"] == 1 and result["subjects"] == 2
    assert result["found"] == {"local": 1} and result["first"] == {"local": 1} and result["named"] == {"local": 1}
    assert result["pages"][0]["subjects"] == ["ball", "dog"]


def test_a_mode_that_fails_on_a_page_counts_as_nothing(testset, monkeypatch):
    def broken(view_path, text):
        raise RuntimeError("no service")
    monkeypatch.setattr(evaluate.local, "local_answer", broken)
    result = score(testset, modes=("local",))
    assert result["found"] == {"local": 0} and result["outcomes"]["local"]["nothing"] == 1
    assert "no service" in result["pages"][0]["error"]["local"]


def test_page_without_a_label_row_is_reported(testset):
    (testset / "labels.csv").write_text("name,label,x0,y0,x1,y1,text\n")
    with pytest.raises(ValueError, match="ball"):
        load_labels(testset)


def test_labels_group_the_subjects_of_a_page(testset):
    with open(testset / "labels.csv", "a") as f:
        f.write("ball,dog,300,0,400,100,\n")
    assert load_labels(testset) == {"ball": ([("ball", (100.0, 100.0, 300.0, 200.0)),
                                              ("dog", (300.0, 0.0, 400.0, 100.0))], "The ball rolled.")}


def test_page_text_comes_from_the_pdf_when_it_is_there(testset):
    assert page_text(testset, "tale_2") == "Page 2."
    assert page_text(testset, "ball", fallback="typed") == "typed"


def test_gemini_is_asked_once_for_a_page(tmp_path, monkeypatch):
    calls = []
    def fake(view_path, text):
        calls.append(view_path)
        return answer("ball", [], HERE)
    monkeypatch.setattr(evaluate, "choose_subjects", fake)
    cache = tmp_path / "gemini" / "page.json"
    assert evaluate.ask_gemini("page.png", "", cache=cache) == evaluate.ask_gemini("page.png", "", cache=cache)
    assert len(calls) == 1


from subject_model.evaluate import agree
from subject_model.tests.conftest import book


def test_agreement_takes_every_third_unlabelled_page(testset, monkeypatch):
    book(testset / "books" / "story.pdf", pages=10)
    (testset / "story_3.png").write_bytes((testset / "ball.png").read_bytes())      # page 3 is hand-labelled
    ball, dog = answer("ball", ["toy"], [100, 100, 500, 500]), answer("dog", [], [600, 600, 900, 900])
    local_answers = iter([ball, dog])
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: next(local_answers))
    monkeypatch.setattr(evaluate, "ask_gemini", lambda view_path, text, cache=None: ball)
    (testset / "books" / "tale.pdf").unlink()
    result = agree(testset)
    assert [page["name"] for page in result["pages"]] == ["story_6", "story_9"]
    assert result["total"] == 2 and result["agree"] == 1 and result["named"] == 1 and result["failed"] == []
    assert json.load(open(testset / "results_agreement.json")) == result


def test_two_empty_answers_agree(testset, monkeypatch):
    book(testset / "books" / "story.pdf", pages=3)
    (testset / "books" / "tale.pdf").unlink()
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: NOTHING)
    monkeypatch.setattr(evaluate, "ask_gemini", lambda view_path, text, cache=None: NOTHING)
    result = agree(testset)
    assert result["total"] == 1 and result["agree"] == 1 and result["named"] == 0


def test_a_subject_may_list_several_accepted_names(testset, monkeypatch):
    officer = [("police officer/officer/woman", HAND)]
    assert judge(answer("person", ["child", "woman"], HERE), officer, 400, 300) == (1, True, 1)
    assert judge(answer("police officer", ["cop"], HERE), officer, 400, 300) == (1, True, 1)
    assert judge(answer("dog", ["animal"], HERE), officer, 400, 300) == (1, True, 0)
    (testset / "labels.csv").write_text("name,label,x0,y0,x1,y1,text\nball,ball/toy,100,100,300,200,\n")
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: answer("toy", [], HERE))
    result = score(testset, modes=("local",))
    assert result["named"] == {"local": 1} and result["pages"][0]["subjects"] == ["ball"]   # shown by its first name
