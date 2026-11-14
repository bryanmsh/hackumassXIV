# Overnight notes

## Decisions

## Needed from other owners

This is the expected state before the hour 4 (display) and hour 7 (pipeline) swaps; re-run with `PIPELINE=real RENDER=real .venv/bin/python -m pytest api/tests/test_swap.py -q 2>&1 | tail -30`.

```text
==================================== ERRORS ====================================
___________________ ERROR collecting api/tests/test_swap.py ____________________
api/tests/test_swap.py:13: in <module>
    from api import modules
api/modules.py:42: in <module>
    pipeline, display = load(settings.PIPELINE, settings.RENDER)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api/modules.py:23: in load
    rasterize=real_pipeline.rasterize, process_page=real_pipeline.process_page,
              ^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: module 'pipeline' has no attribute 'rasterize'
=========================== short test summary info ============================
ERROR api/tests/test_swap.py - AttributeError: module 'pipeline' has no attri...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.07s
```

## Not done
