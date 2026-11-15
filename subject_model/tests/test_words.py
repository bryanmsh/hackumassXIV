from pathlib import Path
from pipeline.gemini import SETTING_WORDS
from subject_model import words
from subject_model.words import GENERAL, NEVER_A_LABEL, NOT_A_SUBJECT, SYNONYMS, match

NOT_NAMES = {"saw", "can", "left", "light", "rose", "top", "watch", "back", "like", "will",
             "home", "water", "fly", "swing", "slide"}


def test_every_class_is_covered_and_no_synonym_is_a_trap():
    classes = [c for c in (Path(words.__file__).parent / "classes.txt").read_text().split("\n") if c]
    assert len(classes) == 347 and not NEVER_A_LABEL & NOT_A_SUBJECT
    for name in classes:
        if name in NEVER_A_LABEL or name in NOT_A_SUBJECT:
            continue
        names = SYNONYMS[name]
        assert 1 <= len(names) <= 5, name
        assert all(s == s.lower() and s != name for s in names), name
        assert not NOT_NAMES & set(names), name
        assert not SETTING_WORDS & {w for n in [name, *names] for w in n.split()}, name   # the pipeline drops these


def test_fixed_examples():
    assert "animal" in SYNONYMS["rabbit"] and "bird" in SYNONYMS["owl"] and "grape" in SYNONYMS["grapes"]
    assert {"child", "boy", "girl"} <= set(SYNONYMS["person"])
    assert {"text", "squiggle", "zigzag", "line", "ocean", "grass"} <= NOT_A_SUBJECT
    assert {"hand", "face", "eye", "saw", "circle", "the mona lisa"} <= NEVER_A_LABEL
    assert {"animal", "bird"} <= GENERAL
    assert not {"rabbit", "tree", "house", "person"} & (NEVER_A_LABEL | NOT_A_SUBJECT)


def test_match_uses_whole_words_and_plurals():
    assert match("The rabbits hid under the tree.", ["rabbit", "bunny"]) == "rabbit"
    assert match("Two children ran.", ["person", "child"]) == "child"
    assert match("The mice and the geese left.", ["mouse"]) == "mouse"
    assert match("A sea turtle swam.", ["sea turtle"]) == "sea turtle"
    assert match("FOXES!", ["fox"]) == "fox"
    assert match("The rabbit's ear.", ["rabbit"]) == "rabbit"


def test_match_handles_the_plurals_a_stemmer_gets_wrong():
    text = "The horses passed two houses, six cookies and three bunnies. Two snowmen waved."
    for name in ("horse", "house", "cookie", "bunny", "snowman"):
        assert match(text, [name]) == name
    assert match("She ate one grape.", ["grapes", "grape"]) == "grape"
    assert match("Her teddy bear fell.", ["teddy bear"]) == "teddy bear"


def test_match_reads_ligatures():
    text = "The ﬁsh saw a butterﬂy."                         # "fi" and "fl" stored as single characters
    assert match(text, ["fish"]) == "fish" and match(text, ["butterfly"]) == "butterfly"


def test_match_ignores_names_inside_other_words_and_shorter_words():
    assert match("He will catch the plant.", ["cat", "ant"]) is None
    assert match("A short walk.", ["shorts"]) is None
    assert match("The dog began to pant.", ["pants"]) is None
    assert match("", ["cat"]) is None


def test_match_prefers_list_order():
    assert match("a bunny and a rabbit", ["rabbit", "bunny"]) == "rabbit"
