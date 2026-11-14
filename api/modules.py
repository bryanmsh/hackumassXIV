"""Picks the real pipeline and display code or the stand-ins, one setting each.

Routes call modules.pipeline.<function> and modules.display.<function>, never api.stubs directly,
so a broken module can be bypassed by changing a setting.
"""
from types import SimpleNamespace

from api import settings, stubs


def load(pipeline: str, render: str):
    """Returns (pipeline, display). Raises ValueError on any value other than 'real' or 'stub'."""
    for name, value in (("PIPELINE", pipeline), ("RENDER", render)):
        if value not in ("real", "stub"):
            raise ValueError(f"{name} must be 'real' or 'stub', got {value!r}")

    # Real modules are imported here, not at the top, so a stub run never needs them.
    # The import paths below are a guess until the swaps at hour 4 (display) and hour 7 (pipeline).
    # Each function is named, so a real module that is missing one fails here, at startup.
    if pipeline == "real":
        import pipeline as real_pipeline
        pipeline_module = SimpleNamespace(
            rasterize=real_pipeline.rasterize, process_page=real_pipeline.process_page,
            segment_at_point=real_pipeline.segment_at_point,
            mask_from_outline=real_pipeline.mask_from_outline, refine_mask=real_pipeline.refine_mask)
    else:
        pipeline_module = stubs

    if render == "real":
        import checks
        import render as render_module
        display = SimpleNamespace(
            render=render_module.render, overlay=render_module.overlay,
            RENDER_VERSION=render_module.RENDER_VERSION,
            run_checks=checks.run_checks, second_look=checks.second_look)
    else:
        display = stubs

    return pipeline_module, display


pipeline, display = load(settings.PIPELINE, settings.RENDER)
