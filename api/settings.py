"""Settings read from the environment. Names and defaults match .env.example.

Locally: uvicorn api.main:app --env-file .env
"""
import os
from pathlib import Path

PIPELINE = os.environ.get("PIPELINE", "stub")  # "real" or "stub"
RENDER = os.environ.get("RENDER", "stub")  # "real" or "stub"
PAGE_CONCURRENCY = int(os.environ.get("PAGE_CONCURRENCY", "4"))
MONGODB_URI = os.environ.get("MONGODB_URI", "")
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))

# Upload limits. Fixed, not environment settings.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_UPLOAD_PAGES = 30
