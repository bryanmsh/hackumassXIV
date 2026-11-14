"""The one place hashes are computed, so no two modules can disagree.

Approvals are matched on these values. Changing how any of them is computed
voids every stored approval.
"""
import hashlib
import json
from pathlib import Path

from contracts.types import Settings


def hash_bytes(data: bytes) -> str:
    """First 12 hex characters of the SHA-256. Also names mask files."""
    return hashlib.sha256(data).hexdigest()[:12]


def settings_hash(settings: Settings) -> str:
    """Hash of the display settings only: not the name, level or contrast note.

    Rule for adding a field to Settings after the freeze: leave it out of this payload
    while it equals its default, so settings saved before the field existed keep their hash.
    """
    # Validate again: model_copy(update=...) and attribute assignment skip validation,
    # and "#e53935" must hash the same as "#E53935".
    settings = Settings.model_validate(settings.model_dump())
    payload = json.dumps(settings.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hash_bytes(payload.encode())


def subject_hash(mask_path: str | Path) -> str:
    """Hash of the selected mask file's bytes."""
    return hash_bytes(Path(mask_path).read_bytes())


def version_token(subject_hash: str, settings_hash: str, level: int | str, render_version: str) -> str:
    """The token `v` for one page version: what was shown, to whom, in which look."""
    return hash_bytes("|".join([subject_hash, settings_hash, str(int(level)), render_version]).encode())
