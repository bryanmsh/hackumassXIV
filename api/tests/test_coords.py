import pytest
from api import coords


def test_fraction_to_master_pixels():
    assert coords.to_pixels((0.5, 0.1), 3000, 2250) == (1500.0, 225.0)


def test_box_to_fractions():
    assert coords.box_to_fractions((900, 900, 1800, 1800), 3000, 2250) == [0.3, 0.4, 0.6, 0.8]


@pytest.mark.parametrize("point", [(-0.01, 0.5), (0.5, 1.01), (float("nan"), 0.5)])
def test_outside_the_page_is_refused(point):
    with pytest.raises(ValueError):
        coords.to_pixels(point, 3000, 2250)
