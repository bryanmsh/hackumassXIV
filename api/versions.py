"""The version of a page: what a child would be shown, in which look, and the token that names it."""
from typing import NamedTuple

from api import modules
from contracts.hashing import version_token


class Version(NamedTuple):
    subject_hash: str
    settings_hash: str
    level: int
    render_version: str

    @property
    def token(self) -> str:
        return version_token(*self)


def current_version(page: dict, profile: dict, level: int) -> Version | None:
    """None unless the page has a subject, is confirmed and is not omitted."""
    if not page.get("subject_hash") or not page["confirmed"] or page["omitted"]:
        return None
    return Version(page["subject_hash"], profile["settings_hash"], level, modules.display.RENDER_VERSION)
