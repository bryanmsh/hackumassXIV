import pytest

from api import modules, stubs


def test_stub_settings_give_the_stubs():
    pipeline, display = modules.load("stub", "stub")
    assert pipeline.process_page is stubs.process_page
    assert display.render is stubs.render and display.RENDER_VERSION == "stub-1"


@pytest.mark.parametrize("args", [("rael", "stub"), ("stub", "")])
def test_unknown_setting_is_refused(args):
    with pytest.raises(ValueError, match="must be 'real' or 'stub'"):
        modules.load(*args)
