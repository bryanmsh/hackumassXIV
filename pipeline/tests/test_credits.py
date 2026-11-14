from pathlib import Path

import pytest

from pipeline.credits import CREDIT_KEYS, parse_credits, read_credits

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

ANIMAL_HOMES = Path(__file__).resolve().parents[2] / "fixtures" / "animal-homes-pratham-FKB.pdf"
NONE = dict.fromkeys(CREDIT_KEYS)


def make_pdf(path, pages):
    """A PDF with one text block per page."""
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        page.insert_textbox(pymupdf.Rect(36, 36, 560, 800), text, fontsize=11)
    document.save(path)
    document.close()
    return path


def test_animal_homes_credits():
    if not ANIMAL_HOMES.exists():
        pytest.skip("fixtures/animal-homes-pratham-FKB.pdf is missing")
    with pymupdf.open(ANIMAL_HOMES) as document:
        if document.page_count < 16:
            pytest.skip(f"needs the 16-page Animal Homes PDF, fixture has {document.page_count} pages")
    assert read_credits(ANIMAL_HOMES) == {
        "author": "Ashwitha Jayakumar",
        "illustrator": "Nafisa Nandini Crishna",
        "publisher": "Pratham Books",
        "source": "StoryWeaver",
        "license": "CC BY 4.0",
    }


def test_storyweaver_style_credits_page_from_a_pdf(tmp_path):
    pdf = make_pdf(tmp_path / "book.pdf", [
        "Animal Homes\nAuthor: Ashwitha Jayakumar\nIllustrator: Nafisa Nandini Crishna",
        "Animals live all around us.",
        "Birds build their homes up high.",
        "This story: Animal Homes is written by Ashwitha Jayakumar . © Pratham Books , 2019. "
        "Some rights reserved. Released under CC BY 4.0 license.\n"
        "Read more stories at storyweaver.org.in",
    ])
    assert read_credits(pdf) == {
        "author": "Ashwitha Jayakumar",
        "illustrator": "Nafisa Nandini Crishna",
        "publisher": "Pratham Books",
        "source": "StoryWeaver",
        "license": "CC BY 4.0",
    }


def test_pdf_with_no_credits_gives_all_none(tmp_path):
    pdf = make_pdf(tmp_path / "plain.pdf", ["Animals live all around us.", "Fish live in the water."])
    assert read_credits(pdf) == NONE


def test_current_five_page_fixture_has_no_credits_and_does_not_raise():
    if not ANIMAL_HOMES.exists():
        pytest.skip("fixture missing")
    result = read_credits(ANIMAL_HOMES)
    assert set(result) == set(CREDIT_KEYS)


def test_only_first_two_and_last_four_pages_are_read(tmp_path):
    pages = [f"Page {i} text." for i in range(12)]
    pages[5] = "Author: Hidden Middle"  # page 6 of 12: not in the first 2 or last 4
    assert read_credits(make_pdf(tmp_path / "middle.pdf", pages))["author"] is None
    pages[9] = "Author: Near The End"  # page 10 of 12: in the last 4
    assert read_credits(make_pdf(tmp_path / "end.pdf", pages))["author"] == "Near The End"


@pytest.mark.parametrize("bad", ["does-not-exist.pdf", "not-a-pdf.pdf", None, 42])
def test_never_raises(tmp_path, bad):
    if bad == "not-a-pdf.pdf":
        (tmp_path / bad).write_text("hello")
    path = tmp_path / bad if isinstance(bad, str) else bad
    assert read_credits(path) == NONE


def test_zero_width_characters_in_the_licence():
    assert parse_credits("Released under CC​ BY​ 4.​0 license")["license"] == "CC BY 4.0"
    assert parse_credits("CC-BY-4.0")["license"] == "CC BY 4.0"


@pytest.mark.parametrize("text, licence", [
    ("CC BY-SA 4.0", "CC BY-SA 4.0"),
    ("cc-by-nc-4.0", "CC BY-NC 4.0"),
    ("CC BY-NC-SA 3.0", "CC BY-NC-SA 3.0"),
    ("no licence here", None),
])
def test_licence_variants(text, licence):
    assert parse_credits(text)["license"] == licence


@pytest.mark.parametrize("text, author", [
    ("Author: Ashwitha Jayakumar", "Ashwitha Jayakumar"),
    ("AUTHOR :  Ashwitha   Jayakumar  ", "Ashwitha Jayakumar"),
    ("This story is written by Rohini Nilekani, and drawn by others.", "Rohini Nilekani"),
    ("Written by Rohini Nilekani.", "Rohini Nilekani"),
    ("Author: A. K. Ramanujan", None),  # a full stop ends a name, so an initial leaves nothing usable: None, never a guess
    ("Author: Mira Rao Illustrator: Sam Lee", "Mira Rao"),
])
def test_author_patterns(text, author):
    assert parse_credits(text)["author"] == author


@pytest.mark.parametrize("text, illustrator", [
    ("Illustrator: Nafisa Nandini Crishna", "Nafisa Nandini Crishna"),
    ("Illustrations by Priya Kuriyan.", "Priya Kuriyan"),
    ("Illustrated by Priya Kuriyan, 2018", "Priya Kuriyan"),
    ("Author: Mira Rao Illustrator: Sam Lee", "Sam Lee"),  # a cover with both on one line
])
def test_illustrator_patterns(text, illustrator):
    assert parse_credits(text)["illustrator"] == illustrator


def test_first_match_wins():
    text = "Author: First Person\nwritten by Second Person.\nAuthor: Third Person"
    assert parse_credits(text)["author"] == "First Person"


def test_publisher_and_source():
    found = parse_credits("© Pratham Books , 2019. Some rights reserved. StoryWeaver")
    assert found["publisher"] == "Pratham Books" and found["source"] == "StoryWeaver"
    none = parse_credits("© 2019 Someone")  # no "Name, year" form
    assert none["publisher"] is None and none["source"] is None
