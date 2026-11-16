"""Start the API on this machine with an in-memory database, so tests/ can run with no MongoDB.

    python -m tests.local_server --port 8765

The API code is unchanged; only pymongo's client is swapped for mongomock before the API is
imported. Pipeline stand-ins, real display code. Nothing is written outside a temp folder.
"""
import argparse
import os
import tempfile


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mirai-http-")
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017/mirai_http_tests"
    os.environ.setdefault("PIPELINE", "stub")
    os.environ.setdefault("RENDER", "real")

    import mongomock
    import pymongo

    pymongo.MongoClient = mongomock.MongoClient

    import uvicorn

    from api.main import app

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
