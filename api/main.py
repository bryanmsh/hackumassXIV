"""Mirai API. Start with: uvicorn api.main:app --host 0.0.0.0 --port 8000

Each route is its own function in api/routes/, one router per area.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import db, jobs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.ensure_indexes()
    jobs.recover_interrupted()
    yield


app = FastAPI(title="Mirai API", lifespan=lifespan)


from api.routes import approval, books, pages, profiles, reader  # noqa: E402

for module in (books, pages, profiles, approval, reader):
    app.include_router(module.router)
