"""process_page with Gemini replaced. No network, no real model."""
from pathlib import Path

import cv2
import numpy as np
import pytest

import pipeline.process
import pipeline.segment
from contracts.hashing import hash_bytes
from contracts.types import Candidate, PageAsset, PageResult
from pipeline import process_page
from pipeline.gemini import GeminiCandidate, GeminiError, RateLimited, SubjectAnswer
from pipeline.process import call_with_retry, decide_state, gemini_box_to_pixels, group_label


# --- the one place Gemini's 0 to 1000 boxes become master pixels ---

def test_box_conversion():
    assert gemini_box_to_pixels([100, 200, 500, 600], 3000, 2000) == (600, 200, 1800, 1000)


def test_box_reversed_and_out_of_range_is_fixed():
    assert gemini_box_to_pixels([500, 600, 100, 1200], 1000, 1000) == (600, 100, 1000, 500)
    assert gemini_box_to_pixels([-50, -10, 2000, 400], 1000, 500) == (0, 0, 400, 500)


# --- state rules: pre-select on almost every page, ask only when nothing is reasonably sure ---

def cand(label="rabbit", confidence=0.9, synonyms=()):
    return Candidate(label=label, synonyms=list(synonyms), box=(0, 0, 10, 10), confidence=confidence,
                     mask_path="m.png", mask_hash="0" * 12, source="auto")


@pytest.mark.parametrize("page_kind", ["single", "several", "scene"])
def test_no_candidates_is_no_clear_subject(page_kind):
    state, members, reason = decide_state(page_kind, [])
    assert (state, members) == ("no_clear_subject", [])
    assert reason


def test_single_page_selects_the_top_candidate():
    assert decide_state("single", [cand(confidence=0.9), cand("tree", 0.3)]) == ("ready", [0], None)


def test_single_page_with_a_close_second_still_selects_the_top_one():
    assert decide_state("single", [cand(confidence=0.8), cand("tree", 0.75)]) == ("ready", [0], None)


def test_several_page_selects_every_reasonably_sure_subject():
    candidates = [cand("rabbit", 0.95), cand("rabbit", 0.95), cand("rat", 0.9), cand("rat", 0.9)]
    assert decide_state("several", candidates) == ("ready", [0, 1, 2, 3], None)


def test_scene_page_with_subjects_selects_them_too():
    candidates = [cand("children", 0.85), cand("woodpecker", 0.8), cand("ants", 0.75), cand("ant", 0.65)]
    assert decide_state("scene", candidates) == ("ready", [0, 1, 2, 3], None)


def test_weak_candidates_are_left_out_of_the_selection():
    candidates = [cand("rabbit", 0.9), cand("rat", 0.8), cand("stone", 0.3)]
    assert decide_state("several", candidates) == ("ready", [0, 1], None)


def test_one_sure_subject_on_a_several_page_is_selected_alone():
    assert decide_state("several", [cand("rabbit", 0.9), cand("stone", 0.3)]) == ("ready", [0], None)


def test_the_selection_floor_is_half():
    assert decide_state("single", [cand(confidence=0.5)]) == ("ready", [0], None)
    state, members, reason = decide_state("single", [cand(confidence=0.49)])
    assert (state, members) == ("needs_subject", [])
    assert reason


def test_nothing_reasonably_sure_asks_the_teacher_on_any_kind_of_page():
    for page_kind in ("single", "several", "scene"):
        state, members, reason = decide_state(page_kind, [cand(confidence=0.4), cand("tree", 0.3)])
        assert (state, members) == ("needs_subject", [])
        assert reason


# --- the name of a combined cut-out ---

def test_group_label_joins_the_different_things():
    assert group_label(["rabbit", "rat"]) == "rabbit and rat"
    assert group_label(["children", "woodpecker", "ants"]) == "children, woodpecker and ants"


def test_group_label_says_each_thing_once():
    assert group_label(["rabbit", "rabbit", "rat", "rat"]) == "rabbit and rat"
    assert group_label(["children", "woodpecker", "ants", "ant", "ant"]) == "children, woodpecker and ants"
    assert group_label(["fox", "foxes"]) == "fox"


# --- retry rule ---

def test_call_with_retry_waits_only_for_a_rate_limit(monkeypatch):
    sleeps = []
    monkeypatch.setattr(pipeline.process.time, "sleep", sleeps.append)
    outcomes = iter([RateLimited("429"), "ok"])

    def flaky():
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    assert call_with_retry(flaky) == "ok"
    assert sleeps == [10]

    outcomes = iter([GeminiError("timeout"), "ok"])
    assert call_with_retry(flaky) == "ok"
    assert sleeps == [10]  # no extra wait for an ordinary failure


def test_call_with_retry_gives_up_after_the_second_failure(monkeypatch):
    monkeypatch.setattr(pipeline.process.time, "sleep", lambda s: None)
    calls = []

    def always_fails():
        calls.append(1)
        raise GeminiError("down")

    with pytest.raises(GeminiError):
        call_with_retry(always_fails)
    assert len(calls) == 2


# --- process_page ---

@pytest.fixture
def asset(page_image):
    return PageAsset(page_number=1, image_path=page_image, view_path=page_image, width=1200, height=900,
                     text="The ball rolled.", text_source="layer")


@pytest.fixture
def gemini(monkeypatch):
    """gemini(*outcomes): each call to choose_subjects returns or raises the next outcome."""
    calls = []

    def set_outcomes(*outcomes):
        remaining = list(outcomes)

        def fake(view_path, text):
            calls.append({"view_path": view_path, "text": text})
            outcome = remaining.pop(0) if len(remaining) > 1 else remaining[0]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(pipeline.process, "choose_subjects", fake)

    set_outcomes.calls = calls
    monkeypatch.setenv("SEGMENTER", "stub")
    monkeypatch.setattr(pipeline.process.time, "sleep", lambda seconds: calls.append({"sleep": seconds}))
    return set_outcomes


def subject(label="ball", confidence=0.9, box=(250, 300, 750, 700), synonyms=("toy",)):
    return GeminiCandidate(label=label, synonyms=list(synonyms), box_2d=list(box), confidence=confidence, reason="r")


def answer(*candidates, page_kind="single"):
    return SubjectAnswer(page_kind=page_kind, candidates=list(candidates))


def test_spread_is_unsupported_without_force(asset, tmp_path, gemini):
    gemini(answer(subject()))
    asset.flags = ["spread"]
    result = process_page(asset, tmp_path)
    assert isinstance(result, PageResult)
    assert (result.state, result.candidates, result.selected, result.page_kind) == ("unsupported", [], None, None)
    assert result.reason
    assert gemini.calls == []


def test_spread_is_processed_with_force(asset, tmp_path, gemini):
    gemini(answer(subject()))
    asset.flags = ["spread"]
    result = process_page(asset, tmp_path, force=True)
    assert result.state == "ready"
    assert len(gemini.calls) == 1


def test_gemini_gets_the_view_and_the_text(asset, tmp_path, gemini):
    gemini(answer(subject()))
    process_page(asset, tmp_path)
    assert gemini.calls == [{"view_path": asset.view_path, "text": "The ball rolled."}]


def test_ready_page_has_masks_on_disk(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.9), subject("grass", 0.3, box=(800, 0, 1000, 1000), synonyms=[])))
    result = process_page(asset, tmp_path)
    assert (result.state, result.selected, result.page_kind, result.reason) == ("ready", 0, "single", None)
    assert [c.label for c in result.candidates] == ["ball", "grass"]
    ball = result.candidates[0]
    assert ball.source == "auto"
    assert ball.synonyms == ["toy"]
    assert ball.confidence == 0.9
    assert ball.box == (360, 225, 840, 675)  # [250, 300, 750, 700] on a 1200x900 master
    path = Path(ball.mask_path)
    assert path.parent == tmp_path / "masks" and path.name == f"1_{ball.mask_hash}.png"
    assert ball.mask_hash == hash_bytes(path.read_bytes())
    mask = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert mask.shape == (900, 1200)
    assert mask[450, 600] == 255 and mask[10, 10] == 0


def read(candidate):
    return cv2.imread(candidate.mask_path, cv2.IMREAD_UNCHANGED)


def test_several_subjects_are_pre_selected_as_one_combined_cut_out(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.8), subject("cat", 0.6, box=(0, 0, 200, 200), synonyms=["kitten", "animal"]),
                  page_kind="several"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.page_kind, result.reason) == ("ready", "several", None)
    assert [c.label for c in result.candidates] == ["ball", "cat", "ball and cat"]  # singles first, then the group
    assert result.selected == 2
    ball, cat, group = result.candidates
    assert np.array_equal(read(group), read(ball) | read(cat))  # every subject, exactly as cut
    assert group.source == "auto"
    assert group.confidence == 0.6  # as sure as its least sure member
    assert group.synonyms == ["ball", "toy", "cat", "kitten", "animal"]  # any member's name is a right answer
    assert group.box == (0, 0, 840, 675)  # around all of them
    path = Path(group.mask_path)
    assert path.parent == tmp_path / "masks" and path.name == f"1_{group.mask_hash}.png"
    assert group.mask_hash == hash_bytes(path.read_bytes())


def test_a_small_subject_survives_in_the_combined_cut_out(asset, tmp_path, gemini):
    """Cleanup drops regions under 5% of the largest, which must not happen to a whole subject."""
    gemini(answer(subject("ball", 0.9), subject("ant", 0.8, box=(10, 10, 30, 30), synonyms=[]), page_kind="several"))
    result = process_page(asset, tmp_path)
    ant, group = result.candidates[1], result.candidates[2]
    assert read(ant).sum() * 20 < read(result.candidates[0]).sum()  # the ant is under 5% of the ball
    assert not (read(ant) & ~read(group)).any()


def test_weak_candidates_stay_out_of_the_combined_cut_out(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.9), subject("cat", 0.8, box=(0, 0, 200, 200)),
                  subject("stone", 0.3, box=(800, 800, 1000, 1000)), page_kind="scene"))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball", "cat", "stone", "ball and cat"]
    assert (result.state, result.selected) == ("ready", 3)
    stone, group = result.candidates[2], result.candidates[3]
    assert not (read(stone) & read(group)).any()


def test_a_single_subject_page_gets_no_combined_cut_out(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.9), subject("cat", 0.8, box=(0, 0, 200, 200))))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball", "cat"]
    assert (result.state, result.selected) == ("ready", 0)


def test_page_text_no_longer_blocks_a_selection(asset, tmp_path, gemini):
    asset.text = "He ran all the way home."
    gemini(answer(subject("ball", 0.9)))
    assert process_page(asset, tmp_path).state == "ready"


def test_nothing_reasonably_sure_still_asks_the_teacher(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.4), subject("cat", 0.3, box=(0, 0, 200, 200)), page_kind="several"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.selected) == ("needs_subject", None)
    assert [c.label for c in result.candidates] == ["ball", "cat"]
    assert result.reason


def test_scene_is_no_clear_subject_through_process_page(asset, tmp_path, gemini):
    gemini(answer(page_kind="scene"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.candidates, result.page_kind) == ("no_clear_subject", [], "scene")


def test_empty_mask_candidate_is_dropped(asset, tmp_path, gemini):
    gemini(answer(subject("speck", 0.95, box=(500, 500, 500, 500)), subject("ball", 0.6)))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball"]
    assert result.state == "needs_subject"  # judged on what is left: 0.6 is under 0.7


def test_no_usable_cut_out_is_no_clear_subject(asset, tmp_path, gemini):
    gemini(answer(subject("speck", 0.95, box=(500, 500, 500, 500))))
    result = process_page(asset, tmp_path)
    assert (result.state, result.candidates, result.selected) == ("no_clear_subject", [], None)
    assert result.reason


def test_two_candidates_with_the_same_mask_share_one_file(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.9), subject("toy", 0.5)))
    result = process_page(asset, tmp_path)
    first, second = result.candidates
    assert first.mask_path == second.mask_path
    assert len(list((tmp_path / "masks").iterdir())) == 1


def test_rate_limit_retries_once_then_succeeds(asset, tmp_path, gemini):
    gemini(RateLimited("429"), answer(subject()))
    result = process_page(asset, tmp_path)
    assert result.state == "ready"
    assert {"sleep": 10} in gemini.calls
    assert sum("view_path" in call for call in gemini.calls) == 2


def test_second_failure_is_failed_with_reason(asset, tmp_path, gemini):
    gemini(GeminiError("timed out"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.candidates, result.selected, result.page_kind) == ("failed", [], None, None)
    assert "timed out" in result.reason
    assert sum("view_path" in call for call in gemini.calls) == 2


def test_segmenter_error_is_failed_not_raised(asset, tmp_path, gemini, monkeypatch):
    gemini(answer(subject()))

    def broken(image, box=None, points=None):
        raise RuntimeError("model fell over")

    monkeypatch.setattr(pipeline.segment, "segment", broken)
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert "model fell over" in result.reason


def test_unbuilt_segmenter_is_failed_not_raised(asset, tmp_path, gemini, monkeypatch):
    gemini(answer(subject()))
    monkeypatch.setenv("SEGMENTER", "edgesam")
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert result.reason


def test_missing_page_image_is_failed_without_calling_gemini(asset, tmp_path, gemini):
    gemini(answer(subject()))
    asset.image_path = str(tmp_path / "pages" / "nope.png")
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert result.reason
    assert gemini.calls == []


def test_reason_never_contains_the_key_and_is_short(asset, tmp_path, gemini, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret123")
    gemini(GeminiError("bad request to ?key=secret123 " + "x" * 500))
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert "secret123" not in result.reason
    assert len(result.reason) <= 200


# --- found in the whole-branch review ---

def test_a_lower_candidate_is_not_made_ready_when_the_top_one_could_not_be_cut(asset, tmp_path, gemini):
    """Gemini's first choice had no usable cut-out. Its second choice must not be picked silently."""
    gemini(answer(subject("speck", 0.95, box=(500, 500, 500, 500)), subject("ball", 0.75)))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball"]
    assert (result.state, result.selected) == ("needs_subject", None)
    assert "speck" in result.reason


def test_a_dropped_lower_candidate_does_not_block_ready(asset, tmp_path, gemini):
    gemini(answer(subject("ball", 0.9), subject("speck", 0.3, box=(500, 500, 500, 500))))
    result = process_page(asset, tmp_path)
    assert (result.state, result.selected) == ("ready", 0)
