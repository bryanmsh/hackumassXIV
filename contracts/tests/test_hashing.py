from contracts.hashing import settings_hash, subject_hash, version_token
from contracts.types import Settings

MAYA = Settings()
LEO = Settings(colors=["#FDD835", "#1E88E5"], position="left", text_mode="below")


def test_settings_hash_golden():
    # If this fails, every stored approval has stopped matching. Do not update the values lightly.
    assert settings_hash(MAYA) == "2804b24a29e2"
    assert settings_hash(LEO) == "67b2391e8a8b"


def test_change_and_change_back_gives_same_hash():
    assert settings_hash(Settings(colors=["#E53935"])) == settings_hash(MAYA)


def test_hex_case_does_not_change_hash():
    assert settings_hash(Settings(colors=["#e53935"])) == settings_hash(MAYA)


def test_color_order_changes_hash():
    assert settings_hash(Settings(colors=["#1E88E5", "#FDD835"])) != \
           settings_hash(Settings(colors=["#FDD835", "#1E88E5"]))


def test_subject_hash_is_hash_of_file_bytes(tmp_path):
    p = tmp_path / "m.png"
    p.write_bytes(bytes(16))
    assert subject_hash(p) == "374708fff771"


def test_version_token_golden_and_level_type():
    assert version_token("374708fff771", "2804b24a29e2", 1, "r1") == "ad960d083f3b"
    assert version_token("374708fff771", "2804b24a29e2", "1", "r1") == "ad960d083f3b"
