import json
import os

import pytest

import pipeline.run_book
from contracts.types import Candidate, PageResult
from pipeline.run_book import load_env, main, run_book

LETTER = (612, 792)


def result_for(page_number):
    """Page 1 ready, page 2 needs a subject, page 3 failed."""
    if page_number == 3:
        return PageResult(state="failed", page_kind=None, candidates=[], selected=None, reason="timed out")
    rabbit = Candidate(label="rabbit", synonyms=["animal"], box=(1, 2, 3, 4), confidence=0.9,
                       mask_path="masks/x.png", mask_hash="a" * 12, source="auto")
    if page_number == 1:
        return PageResult(state="ready", page_kind="single", candidates=[rabbit], selected=0, reason=None)
    return PageResult(state="needs_subject", page_kind="several", candidates=[rabbit], selected=None,
                      reason="The page has several subjects")


@pytest.fixture
def fake_process(monkeypatch):
    calls = []

    def fake(asset, out_dir, force=False):
        calls.append(asset.page_number)
        return result_for(asset.page_number)

    monkeypatch.setattr(pipeline.run_book, "process_page", fake)
    return calls


@pytest.fixture
def book(make_pdf):
    return make_pdf([{"size": LETTER, "text": f"Page {n}"} for n in (1, 2, 3)])


def test_summary_has_every_page_in_order(book, tmp_path, fake_process):
    out = tmp_path / "out"
    summary = run_book(book, out)
    assert sorted(fake_process) == [1, 2, 3]
    assert [page["page_number"] for page in summary["pages"]] == [1, 2, 3]
    assert [page["state"] for page in summary["pages"]] == ["ready", "needs_subject", "failed"]
    assert summary["counts"] == {"ready": 1, "needs_subject": 1, "failed": 1}
    first = summary["pages"][0]
    assert first["page_kind"] == "single" and first["selected"] == 0 and first["reason"] is None
    assert first["candidates"][0]["label"] == "rabbit"
    assert first["flags"] == []
    assert first["seconds"] >= 0
    assert summary["total_seconds"] >= 0
    assert summary["pdf"] == str(book)


def test_writes_summary_json_and_copies_the_pdf(book, tmp_path, fake_process):
    out = tmp_path / "out"
    summary = run_book(book, out)
    assert json.loads((out / "summary.json").read_text()) == summary
    assert (out / "source.pdf").read_bytes() == book.read_bytes()
    assert (out / "pages" / "3.png").exists()


def test_failed_page_does_not_stop_the_others(book, tmp_path, fake_process):
    summary = run_book(book, tmp_path / "out")
    assert summary["pages"][2]["state"] == "failed"
    assert summary["pages"][2]["reason"] == "timed out"
    assert summary["pages"][0]["state"] == "ready"


def test_a_raising_process_page_is_recorded_as_failed(book, tmp_path, monkeypatch):
    def broken(asset, out_dir, force=False):
        if asset.page_number == 2:
            raise RuntimeError("should never happen")
        return result_for(1)

    monkeypatch.setattr(pipeline.run_book, "process_page", broken)
    summary = run_book(book, tmp_path / "out")
    assert [page["state"] for page in summary["pages"]] == ["ready", "failed", "ready"]
    assert "should never happen" in summary["pages"][1]["reason"]


def test_runs_at_most_the_given_number_of_pages_at_once(make_pdf, tmp_path, monkeypatch):
    import threading
    import time

    running, peak, lock = [0], [0], threading.Lock()

    def slow(asset, out_dir, force=False):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        time.sleep(0.05)
        with lock:
            running[0] -= 1
        return result_for(1)

    monkeypatch.setattr(pipeline.run_book, "process_page", slow)
    pdf = make_pdf([{"size": (200, 200)} for _ in range(6)])
    run_book(pdf, tmp_path / "out", concurrency=2)
    assert peak[0] == 2


def test_cli_prints_one_line_per_page(book, tmp_path, fake_process, capsys):
    code = main([str(book), str(tmp_path / "out")])
    assert code == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("page ")]
    assert len(lines) == 3
    assert "ready" in lines[0]
    assert "needs_subject" in lines[1] and "several subjects" in lines[1]
    assert "failed" in lines[2] and "timed out" in lines[2]
    assert all(line.rstrip().endswith("s") for line in lines)  # seconds


def test_cli_with_wrong_arguments_exits_2(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_cli_with_a_missing_pdf_exits_1(tmp_path, capsys):
    assert main([str(tmp_path / "nope.pdf"), str(tmp_path / "out")]) == 1


def test_load_env_sets_missing_names_only_and_prints_nothing(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text('# comment\nMIRAI_TEST_SETTING=on\nSEGMENTER="grabcut"\n\nEMPTY=\nnot a line\n')
    monkeypatch.delenv("MIRAI_TEST_SETTING", raising=False)
    monkeypatch.setenv("SEGMENTER", "stub")
    monkeypatch.delenv("EMPTY", raising=False)
    load_env(env)
    assert os.environ["MIRAI_TEST_SETTING"] == "on"
    assert os.environ["SEGMENTER"] == "stub"  # what is already set wins
    assert "EMPTY" not in os.environ  # an empty value is the same as unset
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    monkeypatch.delenv("MIRAI_TEST_SETTING")


def test_load_env_missing_file_is_fine(tmp_path):
    load_env(tmp_path / "no.env")
