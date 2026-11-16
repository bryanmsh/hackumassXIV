"""process_page with the subject model replaced. No real model."""
from pathlib import Path

import cv2
import numpy as np
import pytest

import pipeline.process
import pipeline.segment
from contracts.hashing import hash_bytes
from contracts.types import Candidate, PageAsset, PageResult
from pipeline import process_page
from pipeline.process import UNSURE_REASON, box_to_pixels, decide_state, group_label
from pipeline.subjects import SubjectAnswer, SubjectCandidate, SubjectError


# --- the one place 0 to 1000 subject boxes become master pixels ---

def test_box_conversion():
    assert box_to_pixels([100, 200, 500, 600], 3000, 2000) == (600, 200, 1800, 1000)


def test_box_reversed_and_out_of_range_is_fixed():
    assert box_to_pixels([500, 600, 100, 1200], 1000, 1000) == (600, 100, 1000, 500)
    assert box_to_pixels([-50, -10, 2000, 400], 1000, 500) == (0, 0, 400, 500)


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


# --- process_page ---

@pytest.fixture
def asset(page_image):
    return PageAsset(page_number=1, image_path=page_image, view_path=page_image, width=1200, height=900,
                     text="The ball rolled.", text_source="layer")


@pytest.fixture
def model(monkeypatch):
    """model(*outcomes): each call to choose_subjects returns or raises the next outcome."""
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
    return set_outcomes


def subject(label="ball", confidence=0.9, box=(250, 300, 750, 700), synonyms=("toy",)):
    return SubjectCandidate(label=label, synonyms=list(synonyms), box_2d=list(box), confidence=confidence, reason="r")


def answer(*candidates, page_kind="single", trusted=True):
    return SubjectAnswer(page_kind=page_kind, candidates=list(candidates), trusted=trusted)


def test_spread_is_unsupported_without_force(asset, tmp_path, model):
    model(answer(subject()))
    asset.flags = ["spread"]
    result = process_page(asset, tmp_path)
    assert isinstance(result, PageResult)
    assert (result.state, result.candidates, result.selected, result.page_kind) == ("unsupported", [], None, None)
    assert result.reason
    assert model.calls == []


def test_spread_is_processed_with_force(asset, tmp_path, model):
    model(answer(subject()))
    asset.flags = ["spread"]
    result = process_page(asset, tmp_path, force=True)
    assert result.state == "ready"
    assert len(model.calls) == 1


def test_the_model_gets_the_view_and_the_text(asset, tmp_path, model):
    model(answer(subject()))
    process_page(asset, tmp_path)
    assert model.calls == [{"view_path": asset.view_path, "text": "The ball rolled."}]


def test_ready_page_has_masks_on_disk(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), subject("grass", 0.3, box=(800, 0, 1000, 1000), synonyms=[])))
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


def test_several_subjects_are_offered_as_one_combined_cut_out_but_not_pre_selected(asset, tmp_path, model):
    model(answer(subject("ball", 0.8), subject("cat", 0.6, box=(0, 0, 200, 200), synonyms=["kitten", "animal"]),
                  page_kind="several"))
    result = process_page(asset, tmp_path)
    # The teacher decides what a page with several subjects is about; the group is one click away.
    assert (result.state, result.page_kind, result.reason) == ("needs_subject", "several", "The page has several subjects")
    assert [c.label for c in result.candidates] == ["ball", "cat", "ball and cat"]  # singles first, then the group
    assert result.selected is None
    ball, cat, group = result.candidates
    assert np.array_equal(read(group), read(ball) | read(cat))  # every subject, exactly as cut
    assert group.source == "auto"
    assert group.confidence == 0.6  # as sure as its least sure member
    assert group.synonyms == ["ball", "toy", "cat", "kitten", "animal"]  # any member's name is a right answer
    assert group.box == (0, 0, 840, 675)  # around all of them
    path = Path(group.mask_path)
    assert path.parent == tmp_path / "masks" and path.name == f"1_{group.mask_hash}.png"
    assert group.mask_hash == hash_bytes(path.read_bytes())


def test_a_small_subject_survives_in_the_combined_cut_out(asset, tmp_path, model):
    """Cleanup drops regions under 5% of the largest, which must not happen to a whole subject."""
    model(answer(subject("ball", 0.9), subject("ant", 0.8, box=(10, 10, 30, 30), synonyms=[]), page_kind="several"))
    result = process_page(asset, tmp_path)
    ant, group = result.candidates[1], result.candidates[2]
    assert read(ant).sum() * 20 < read(result.candidates[0]).sum()  # the ant is under 5% of the ball
    assert not (read(ant) & ~read(group)).any()


def test_weak_candidates_stay_out_of_the_combined_cut_out(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), subject("cat", 0.8, box=(0, 0, 200, 200)),
                  subject("stone", 0.3, box=(800, 800, 1000, 1000)), page_kind="scene"))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball", "cat", "stone", "ball and cat"]
    assert (result.state, result.selected) == ("needs_subject", None)
    stone, group = result.candidates[2], result.candidates[3]
    assert not (read(stone) & read(group)).any()


def test_a_single_subject_page_gets_no_combined_cut_out(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), subject("cat", 0.8, box=(0, 0, 200, 200))))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball", "cat"]
    assert (result.state, result.selected) == ("ready", 0)


def test_page_text_no_longer_blocks_a_selection(asset, tmp_path, model):
    asset.text = "He ran all the way home."
    model(answer(subject("ball", 0.9)))
    assert process_page(asset, tmp_path).state == "ready"


def test_nothing_reasonably_sure_still_asks_the_teacher(asset, tmp_path, model):
    model(answer(subject("ball", 0.4), subject("cat", 0.3, box=(0, 0, 200, 200)), page_kind="several"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.selected) == ("needs_subject", None)
    assert [c.label for c in result.candidates] == ["ball", "cat"]
    assert result.reason


def test_scene_is_no_clear_subject_through_process_page(asset, tmp_path, model):
    model(answer(page_kind="scene"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.candidates, result.page_kind) == ("no_clear_subject", [], "scene")


def test_empty_mask_candidate_is_dropped(asset, tmp_path, model):
    model(answer(subject("speck", 0.95, box=(500, 500, 500, 500)), subject("ball", 0.6)))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball"]
    assert result.state == "needs_subject"  # judged on what is left: 0.6 is under 0.7


def test_no_usable_cut_out_is_no_clear_subject(asset, tmp_path, model):
    model(answer(subject("speck", 0.95, box=(500, 500, 500, 500))))
    result = process_page(asset, tmp_path)
    assert (result.state, result.candidates, result.selected) == ("no_clear_subject", [], None)
    assert result.reason


def test_two_candidates_with_the_same_mask_share_one_file(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), subject("toy", 0.5)))
    result = process_page(asset, tmp_path)
    first, second = result.candidates
    assert first.mask_path == second.mask_path
    assert len(list((tmp_path / "masks").iterdir())) == 1


def test_a_model_failure_is_failed_with_its_plain_reason(asset, tmp_path, model):
    model(SubjectError("The subject finder is not set up on this server"))
    result = process_page(asset, tmp_path)
    assert (result.state, result.candidates, result.selected, result.page_kind) == ("failed", [], None, None)
    assert result.reason == "The subject finder is not set up on this server"
    assert len(model.calls) == 1  # no retry: our model gives the same answer twice


def test_segmenter_error_is_failed_not_raised(asset, tmp_path, model, monkeypatch):
    model(answer(subject()))

    def broken(image, box=None, points=None):
        raise RuntimeError("model fell over")

    monkeypatch.setattr(pipeline.segment, "segment", broken)
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert "model fell over" in result.reason


def test_unbuilt_segmenter_is_failed_not_raised(asset, tmp_path, model, monkeypatch):
    model(answer(subject()))
    monkeypatch.setenv("SEGMENTER", "edgesam")
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert result.reason


def test_missing_page_image_is_failed_without_calling_the_model(asset, tmp_path, model):
    model(answer(subject()))
    asset.image_path = str(tmp_path / "pages" / "nope.png")
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert result.reason
    assert model.calls == []


def test_reason_is_short(asset, tmp_path, model):
    model(SubjectError("x" * 500))
    result = process_page(asset, tmp_path)
    assert result.state == "failed"
    assert len(result.reason) <= 200


# --- found in the whole-branch review ---

def test_a_lower_candidate_is_not_made_ready_when_the_top_one_could_not_be_cut(asset, tmp_path, model):
    """The model's first choice had no usable cut-out. Its second choice must not be picked silently."""
    model(answer(subject("speck", 0.95, box=(500, 500, 500, 500)), subject("ball", 0.75)))
    result = process_page(asset, tmp_path)
    assert [c.label for c in result.candidates] == ["ball"]
    assert (result.state, result.selected) == ("needs_subject", None)
    assert "speck" in result.reason


def test_a_dropped_lower_candidate_does_not_block_ready(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), subject("speck", 0.3, box=(500, 500, 500, 500))))
    result = process_page(asset, tmp_path)
    assert (result.state, result.selected) == ("ready", 0)


# --- the trust rule: a pick the page text does not back up is offered, not pre-selected ---

def test_an_untrusted_single_pick_asks_the_teacher_and_keeps_the_guess(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), trusted=False))
    result = process_page(asset, tmp_path)
    assert (result.state, result.selected, result.reason) == ("needs_subject", None, UNSURE_REASON)
    assert [c.label for c in result.candidates] == ["ball"]


def test_a_trusted_single_pick_stays_ready(asset, tmp_path, model):
    model(answer(subject("ball", 0.9), trusted=True))
    assert (process_page(asset, tmp_path).state, process_page(asset, tmp_path).selected) == ("ready", 0)


def test_an_untrusted_page_with_several_subjects_still_offers_them_together(asset, tmp_path, model):
    model(answer(subject("ball", 0.9, box=(100, 100, 400, 400)), subject("dog", 0.8, box=(600, 600, 900, 900)),
                  page_kind="several", trusted=False))
    result = process_page(asset, tmp_path)
    assert result.state == "needs_subject" and result.selected is None
    assert result.candidates[-1].label == "ball and dog"
