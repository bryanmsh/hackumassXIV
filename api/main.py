"""Mirai API. Start with: uvicorn api.main:app --host 0.0.0.0 --port 8000

Each route is its own function in api/routes/, one router per area.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pymongo.errors import PyMongoError

from api import db, jobs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.ensure_indexes()
    jobs.recover_interrupted()
    yield


app = FastAPI(title="Mirai API", lifespan=lifespan)


@app.get("/health")  # inside the Docker network, for health checks
@app.get("/api/health")  # through Caddy, which forwards only /api/*
def health():
    """Up and able to reach the database. Touches no book data."""
    try:
        db.client.admin.command("ping")
    except PyMongoError:
        raise HTTPException(503, "The database is not reachable.")
    return {"status": "ok"}


from api.routes import approval, books, pages, profiles, reader  # noqa: E402

for module in (books, pages, profiles, approval, reader):
    app.include_router(module.router)
