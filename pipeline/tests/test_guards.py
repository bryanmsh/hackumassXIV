"""The guards on every subject answer: settings, repeats and group boxes are not subjects."""
import pytest

from pipeline.subjects import SubjectCandidate, _drop_non_subjects

BIRD = (200, 330, 300, 370)       # [ymin, xmin, ymax, xmax] on 0 to 1000
ANTS = (900, 380, 990, 470)
CHILDREN = (580, 520, 690, 620)


def candidate(label, confidence=0.9, box=BIRD):
    return SubjectCandidate(label=label, box_2d=list(box), confidence=confidence)


def labels(*candidates):
    return [c.label for c in _drop_non_subjects(list(candidates))]


@pytest.mark.parametrize("label", ["forest", "dense forest", "the sky", "background", "grass"])
def test_the_setting_is_not_a_subject(label):
    assert labels(candidate("woodpecker", 0.6), candidate(label, 0.9, box=(400, 400, 950, 850))) == ["woodpecker"]


@pytest.mark.parametrize("label", ["grasshopper", "tree", "nest", "burrow"])
def test_words_that_only_look_like_settings_are_kept(label):
    assert labels(candidate(label)) == [label]


def test_a_box_holding_two_other_candidates_is_a_group_and_is_dropped():
    tall = (190, 320, 995, 480)  # runs from the bird down to the ants
    assert labels(candidate("bird and lizard", 0.9, tall), candidate("bird", 0.5),
                  candidate("ants", 0.4, ANTS), candidate("children", 0.3, CHILDREN)) == ["bird", "ants", "children"]


def test_a_box_holding_one_other_candidate_is_kept():
    nest = (150, 300, 400, 500)  # an animal's home is a real subject
    assert labels(candidate("nest", 0.6, nest), candidate("bird", 0.8)) == ["bird", "nest"]


def test_overlapping_but_not_containing_boxes_are_kept():
    assert sorted(labels(candidate("girl", 0.6, (580, 520, 690, 575)), candidate("boy", 0.6, (580, 560, 690, 620)),
                         candidate("woodpecker", 0.5))) == ["boy", "girl", "woodpecker"]


def test_near_duplicate_boxes_keep_the_more_confident():
    assert labels(candidate("bird", 0.5), candidate("woodpecker", 0.7, (202, 331, 299, 369)),
                  candidate("ants", 0.4, ANTS)) == ["woodpecker", "ants"]


def test_zero_area_boxes_do_not_break_the_guards():
    assert labels(candidate("speck", 0.9, (500, 500, 500, 500)), candidate("bird", 0.5)) == ["speck", "bird"]
