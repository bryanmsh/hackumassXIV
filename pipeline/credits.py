"""Read a book's credits from its PDF, so the teacher doesn't have to type them.

read_credits(pdf_path) -> {"author", "illustrator", "publisher", "source", "license"},
each a string or None.

It only copies text that is printed in the PDF's text layer. There is no AI model and no
OCR, so it can't invent a name: anything it doesn't find stays None for the teacher to fill
in. It looks at the first 2 and last 4 pages, where picture books put their cover and credits.
It never raises: on any error every value is None.
"""
import re

try:
    import pymupdf
except ImportError:  # older PyMuPDF releases only have the fitz name
    import fitz as pymupdf

CREDIT_KEYS = ("author", "illustrator", "publisher", "source", "license")
FIRST_PAGES = 2
LAST_PAGES = 4
MAX_NAME = 80  # longer than any real name list; past this the match ran into other text

# StoryWeaver puts zero-width characters inside words such as "CC BY 4.0".
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)

# A name ends at a full stop, a comma, a line end, a copyright sign, or the next credit label.
# The labels matter on covers that print "Author: A Illustrator: B" on one line, which is
# also why "Author:" and "Illustrator:" are matched anywhere, not only at the start of a line.
_LABELS = r"author|illustrators?|illustrated|illustrations?|translators?|translated|written|story|©"
_NAME = r"([^\n,.©]+?)\s*(?=\s\.|\.|,|\n|$|\b(?:" + _LABELS + r")\b|©)"

_AUTHOR = [
    re.compile(r"\bauthors?[ \t]*:[ \t]*" + _NAME, re.I),
    re.compile(r"\bwritten[ \t]+by[ \t]+" + _NAME, re.I),
]
_ILLUSTRATOR = [
    re.compile(r"\billustrators?[ \t]*:[ \t]*" + _NAME, re.I),
    re.compile(r"\billustrations?[ \t]+by[ \t]+" + _NAME, re.I),
    re.compile(r"\billustrated[ \t]+by[ \t]+" + _NAME, re.I),
]
_PUBLISHER = re.compile(r"©[ \t]*([^,©\n]+?)[ \t]*,[ \t]*(?:19|20)\d\d\b")
_LICENSE = re.compile(
    r"\bCC[ \t-]*BY(?P<parts>(?:[ \t-]*(?:SA|NC|ND)\b)*)[ \t-]*(?P<version>\d\.\d)", re.I)
_SOURCE = re.compile(r"storyweaver", re.I)


def read_credits(pdf_path) -> dict:
    """Credits printed in the PDF. Every key is always present; missing ones are None."""
    try:
        return parse_credits(_credit_text(pdf_path))
    except Exception:
        return dict.fromkeys(CREDIT_KEYS)


def _credit_text(pdf_path) -> str:
    """Text of the first 2 and last 4 pages, in page order, each page once."""
    with pymupdf.open(pdf_path) as document:
        count = document.page_count
        wanted = sorted(set(range(min(FIRST_PAGES, count))) | set(range(max(0, count - LAST_PAGES), count)))
        return "\n".join(document[i].get_text() for i in wanted)


def parse_credits(text: str) -> dict:
    """The credit fields found in plain text. Split out so it can be tested without a PDF."""
    text = (text or "").translate(_INVISIBLE).replace(" ", " ")
    return {
        "author": _first_name(_AUTHOR, text),
        "illustrator": _first_name(_ILLUSTRATOR, text),
        "publisher": _first_name([_PUBLISHER], text),
        "source": "StoryWeaver" if _SOURCE.search(text) else None,
        "license": _license(text),
    }


def _first_name(patterns, text):
    """The first pattern, in the order given, that finds a usable name."""
    for pattern in patterns:
        for match in pattern.finditer(text):
            name = " ".join(match.group(1).split())
            if 1 < len(name) <= MAX_NAME:
                return name
    return None


def _license(text):
    match = _LICENSE.search(text)
    if not match:
        return None
    parts = [p.upper() for p in re.findall(r"SA|NC|ND", match.group("parts"), re.I)]
    return "CC BY" + "".join("-" + p for p in parts) + " " + match.group("version")
