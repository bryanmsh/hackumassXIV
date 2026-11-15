import numpy as np
from subject_model import text_images
from subject_model.text_images import draw_lines, find_fonts, text_page


def changed(a, b):
    return float((a != b).any(axis=2).mean())


def test_text_page_is_a_light_page_with_marks_on_it():
    page = text_page(np.random.default_rng(0), [])
    assert page.shape == (192, 256, 3) and page.dtype == np.uint8
    assert int(page[0, 0].min()) >= 225                                # the corner is plain paper
    assert 0.01 < changed(page, np.broadcast_to(page[0, 0], page.shape)) < 0.6


def test_draw_lines_marks_a_copy_and_leaves_the_photo_alone():
    photo = np.full((240, 320, 3), 255, np.uint8)
    photo[:, 160:] = 0                                                 # half white, half black
    before = photo.copy()
    out = draw_lines(photo, np.random.default_rng(1), [])
    assert out.shape == photo.shape and np.array_equal(photo, before)
    assert 0.002 < changed(out, photo) < 0.5


def test_the_same_seed_gives_the_same_picture():
    a, b = (text_page(np.random.default_rng(3), []) for _ in range(2))
    assert np.array_equal(a, b)


def test_find_fonts_skips_missing_folders(tmp_path):
    assert find_fonts([tmp_path / "nowhere"]) == []


def test_main_writes_the_pictures(tmp_path):
    text_images.main([str(tmp_path / "text"), "--count", "5", "--fonts", str(tmp_path / "nowhere")])
    assert len(list((tmp_path / "text").glob("*.png"))) == 5
