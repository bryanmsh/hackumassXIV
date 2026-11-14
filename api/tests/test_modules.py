import sys
import types

import pytest

from api import modules, stubs


def test_stub_settings_give_the_stubs():
    pipeline, display = modules.load("stub", "stub")
    assert pipeline.process_page is stubs.process_page
    assert pipeline.read_credits is stubs.read_credits
    assert display.render is stubs.render and display.RENDER_VERSION == "stub-1"


@pytest.mark.parametrize("args", [("rael", "stub"), ("stub", "")])
def test_unknown_setting_is_refused(args):
    with pytest.raises(ValueError, match="must be 'real' or 'stub'"):
        modules.load(*args)


def test_real_pipeline_missing_a_function_is_refused_at_load(monkeypatch):
    # An empty pipeline/ folder imports fine as a package; it must not pass as the real thing.
    monkeypatch.setitem(sys.modules, "pipeline", types.ModuleType("pipeline"))
    with pytest.raises(AttributeError, match="rasterize"):
        modules.load("real", "stub")


def fake_pipeline(monkeypatch):
    """A real pipeline package as it is before pipeline/credits.py lands."""
    package = types.ModuleType("pipeline")
    for name in ("rasterize", "process_page", "segment_at_point", "mask_from_outline", "refine_mask"):
        setattr(package, name, lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "pipeline", package)
    monkeypatch.delitem(sys.modules, "pipeline.credits", raising=False)


def test_real_pipeline_without_a_credits_reader_still_loads(monkeypatch):
    fake_pipeline(monkeypatch)
    pipeline, _ = modules.load("real", "stub")
    assert pipeline.read_credits is stubs.read_credits


def test_real_pipeline_credits_reader_is_used_once_it_exists(monkeypatch):
    fake_pipeline(monkeypatch)
    credits = types.ModuleType("pipeline.credits")
    credits.read_credits = lambda pdf_path: {}
    monkeypatch.setitem(sys.modules, "pipeline.credits", credits)
    pipeline, _ = modules.load("real", "stub")
    assert pipeline.read_credits is credits.read_credits
