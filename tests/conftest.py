"""Tests that call the API from outside, over HTTP.

By default a local API is started (tests/local_server.py: in-memory database, pipeline
stand-ins, real display code). To test a running server instead:

    MIRAI_URL=https://our-domain  SITE_USER=...  SITE_PASSWORD=...  pytest tests

Against a real server these tests create books and profiles named "zz-test ...". There is no
delete route, so run them against the live site only when that is acceptable.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _dotenv(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name and value.strip():
                return value.strip()
    return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def api():
    url = os.environ.get("MIRAI_URL")
    server = None
    if url:
        user, password = _dotenv("SITE_USER"), _dotenv("SITE_PASSWORD")
        auth = (user, password) if user and password else None
    else:
        port = _free_port()
        env = {k: v for k, v in os.environ.items() if k not in ("PIPELINE", "RENDER")}
        server = subprocess.Popen([sys.executable, "-m", "tests.local_server", "--port", str(port)],
                                  cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        url, auth = f"http://127.0.0.1:{port}", None

    client = httpx.Client(base_url=url.rstrip("/"), auth=auth, timeout=60)
    deadline = time.monotonic() + 45
    while True:
        if server is not None and server.poll() is not None:
            output = server.stdout.read().decode(errors="replace")
            pytest.fail(f"The local API did not start:\n{output[-3000:]}")
        try:
            r = client.get("/api/books")
            if r.status_code == 401:
                pytest.fail("The site asks for a password: set SITE_USER and SITE_PASSWORD.")
            if r.status_code < 500:
                break
        except httpx.TransportError:
            pass
        if time.monotonic() > deadline:
            pytest.fail(f"No API answered at {url}/api/books")
        time.sleep(0.5)

    yield client
    client.close()
    if server is not None:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
