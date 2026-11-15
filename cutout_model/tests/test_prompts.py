import numpy as np
from cutout_model.prompts import build_input, crop_window


def test_crop_window_grows_box_by_margin_and_clips():
    assert crop_window((100, 100, 300, 200), 1000, 800, margin=0.25) == (50, 75, 350, 225)
    assert crop_window((0, 0, 100, 100), 1000, 800, margin=0.25) == (0, 0, 125, 125)


def test_crop_window_orders_corners():
    assert crop_window((300, 200, 100, 100), 1000, 800, margin=0.25) == (50, 75, 350, 225)


def test_crop_window_is_none_for_empty_or_offpage_box():
    assert crop_window((500, 500, 500, 500), 1000, 800) is None
    assert crop_window((1200, 900, 1300, 950), 1000, 800) is None
    assert crop_window((999.5, 10, 1400, 60), 1000, 800) is None  # under 2 px left on the page


def test_build_input_shape_values_and_box_channel():
    image = np.full((800, 1000, 3), 255, np.uint8)
    x, window = build_input(image, (100, 100, 300, 200), size=64)
    assert x.shape == (4, 64, 64) and x.dtype == np.float32
    assert window == (50, 75, 350, 225)
    assert x[:3].min() == 1.0 and x[:3].max() == 1.0      # pixels scaled to 0..1
    assert x[3, 32, 32] == 1.0 and x[3, 0, 0] == 0.0      # inside the box / in the margin
    assert abs(x[3].mean() - 0.444) < 0.03                 # box is 2/3 of the window each way


def test_build_input_is_none_for_empty_box():
    image = np.zeros((800, 1000, 3), np.uint8)
    assert build_input(image, (500, 500, 500, 500)) is None
