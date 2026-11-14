"""Live tests: these call the real Gemini API and cost quota.

Skipped unless RUN_LIVE=1. They need GEMINI_API_KEY in the environment and the six
fixture pages in fixtures/pages/.
    set -a; . ./.env; set +a; RUN_LIVE=1 .venv/bin/python -m pytest pipeline/tests/test_live.py -q -s
"""
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pipeline.gemini import RateLimited, choose_subjects

pytestmark = pytest.mark.live

FIXTURES = Path(__file__).parents[2] / "fixtures" / "pages"


def view(n):
    path = FIXTURES / f"{n}_view.png"
    if not path.exists():
        pytest.skip(f"{path} is missing; commit the fixture pages first")
    return path


def test_one_page_returns_valid_answer():
    answer = choose_subjects(view(1), "")
    assert answer.page_kind in ("single", "several", "scene")
    for candidate in answer.candidates:
        assert len(candidate.box_2d) == 4
        assert all(0 <= value <= 1000 for value in candidate.box_2d)
        assert 0 <= candidate.confidence <= 1
    print("\nanswer:", answer.model_dump())


def test_four_calls_at_once():
    def timed(n):
        start = time.time()
        try:
            choose_subjects(view(n), "")
            outcome = "ok"
        except RateLimited:
            outcome = "rate_limited"
        return n, outcome, round(time.time() - start, 2)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(timed, [1, 2, 3, 4]))
    print("\nfour at once:", results)  # the finding to record in pipeline/README.md
    assert all(outcome in ("ok", "rate_limited") for _, outcome, _ in results)


def test_six_fixture_pages_each_get_a_state(tmp_path):
    """The plan's "done when" for process_page: every page gets a state, at least one needs a subject."""
    import json

    from contracts.types import PageAsset
    from pipeline import process_page

    index = FIXTURES.parent / "pages.json"
    if not index.exists():
        pytest.skip(f"{index} is missing; commit the fixture pages first")
    root = FIXTURES.parents[1]
    states = {}
    for entry in json.loads(index.read_text()):
        asset = PageAsset.model_validate(entry)
        asset.image_path, asset.view_path = str(root / asset.image_path), str(root / asset.view_path)
        start = time.time()
        result = process_page(asset, tmp_path)
        states[asset.page_number] = (result.state, result.reason, round(time.time() - start, 1))
    print("\nstates:", states)
    assert len(states) == 6
    assert all(state in ("ready", "needs_subject", "no_clear_subject", "unsupported", "failed")
               for state, _, _ in states.values())
    assert any(state == "needs_subject" for state, _, _ in states.values())
