"""Mirai API. Start with: uvicorn api.main:app --host 0.0.0.0 --port 8000

Hour 1 skeleton: every Contract 1 route answers with its example from contracts/examples.json
and ignores ids and bodies. Image routes return one stand-in page. Each route is its own
function in api/routes/ so it can be replaced by the real version without touching the others.
"""
import json
from pathlib import Path

from fastapi import FastAPI

EXAMPLES = json.loads((Path(__file__).parents[1] / "contracts" / "examples.json").read_text())

app = FastAPI(title="Mirai API")


def example(key: str):
    return EXAMPLES[key]["response"]


# The routers import example() from this module, so they are included after it is defined.
from api.routes import approval, books, pages, profiles, reader  # noqa: E402

for module in (books, pages, profiles, approval, reader):
    app.include_router(module.router)
