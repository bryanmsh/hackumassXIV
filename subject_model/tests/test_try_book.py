import pipeline.process
from pipeline.gemini import SubjectAnswer
from subject_model import local, try_book
from subject_model.tests.conftest import book


def test_a_book_goes_through_the_real_page_code(tmp_path, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "stub")
    fixed = SubjectAnswer.model_validate({"page_kind": "single", "candidates": [
        {"label": "ball", "synonyms": [], "box_2d": [100, 100, 500, 500], "confidence": 0.9, "reason": ""}]})
    monkeypatch.setattr(local, "local_answer", lambda view_path, text: fixed)
    before = pipeline.process.choose_subjects
    summary = try_book.run(book(tmp_path / "book.pdf", pages=2), tmp_path / "out")
    assert sum(summary["counts"].values()) == 2 and "failed" not in summary["counts"]
    assert pipeline.process.choose_subjects is before          # put back afterwards
