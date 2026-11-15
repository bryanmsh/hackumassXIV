from collections import Counter
import cv2
import numpy as np
import torch
from subject_model.namer_data import NamerDataset, class_name, find_images, load_image, split, to_square


def test_class_names_are_plain_lowercase_words():
    assert class_name("Sea_Turtle") == "sea turtle" and class_name("teddy-bear") == "teddy bear"
    assert class_name("The_Mona_Lisa") == "the mona lisa" and class_name("t-shirt") == "t shirt"


def test_find_images_merges_roots_and_names_classes(image_roots):
    items, classes = find_images(image_roots)
    assert classes == ["cat", "dog", "person", "sea turtle"]
    assert Counter(classes[i] for _, i in items) == {"cat": 5, "dog": 5, "person": 3, "sea turtle": 1}


def test_split_is_disjoint_and_repeatable(image_roots):
    items, _ = find_images(image_roots)
    train, val = split(items, val_fraction=0.2, seed=0)
    assert len(val) == 3 and len(train) == 11 and not set(train) & set(val)
    assert split(items, val_fraction=0.2, seed=0) == (train, val)
    assert len(split(items[:4], val_fraction=0.05)[1]) == 1          # never empty


def test_load_image_puts_transparent_art_on_white_and_widens_grey(image_roots):
    person = load_image(image_roots[1] / "person" / "0.png")
    assert person.shape == (48, 48, 3)
    assert person[0, 0].tolist() == [255, 255, 255] and person[24, 24].tolist() == [0, 0, 255]
    assert load_image(image_roots[1] / "cat" / "grey.png").shape == (48, 48, 3)
    assert load_image(image_roots[0] / "dog" / "bad.jpg") is None


def test_load_image_may_decode_a_large_jpeg_smaller(tmp_path):
    cv2.imwrite(str(tmp_path / "big.jpg"), np.full((480, 640, 3), 200, np.uint8))
    assert load_image(tmp_path / "big.jpg").shape == (480, 640, 3)
    small = load_image(tmp_path / "big.jpg", at_least=100)
    assert small.shape[0] < 480 and min(small.shape[:2]) >= 100


def test_to_square_pads_with_white():
    wide = np.zeros((20, 40, 3), np.uint8)
    square = to_square(wide, size=32)
    assert square.shape == (32, 32, 3)
    assert square[0, 16].tolist() == [255, 255, 255] and square[16, 16].tolist() == [0, 0, 0]


def test_items_are_tensors_and_bad_files_are_skipped(image_roots):
    items, _ = find_images(image_roots)
    data = NamerDataset(items, train=False, size=32)
    for index in range(len(data)):                                    # includes bad.jpg
        x, y = data[index]
        assert x.shape == (3, 32, 32) and x.dtype == torch.float32
        assert -1.0 <= float(x.min()) and float(x.max()) <= 1.0 and isinstance(y, int)


def test_train_items_vary(image_roots):
    items, _ = find_images(image_roots)
    index = next(i for i, (path, _) in enumerate(items) if "person" in path.parts)
    data = NamerDataset(items, train=True, size=32)
    assert any(not torch.equal(data[index][0], data[index][0]) for _ in range(5))
