# Deploying Mirai

One Vultr server runs two containers: the API, and Caddy, which serves the built web
app, forwards `/api` to the API, handles HTTPS and asks for a password on every path.

## The server

| | |
| --- | --- |
| Address | `https://140-82-15-107.sslip.io` (IP `140.82.15.107`) |
| Log in | `ssh -i ~/.ssh/mirai_vultr root@140.82.15.107` (key only) |
| Repo | `/opt/mirai`, branch `bryan`, read-only deploy key |
| Data | `/opt/mirai/data`, mounted into the API container; survives restarts and rebuilds |
| Open ports | 22, 80, 443 |

## First time: create `/opt/mirai/.env`

Copy `.env.example` and fill it in on the server. It is never committed.

| Name | Value on the server |
| --- | --- |
| `SITE_ADDRESS` | `140-82-15-107.sslip.io` |
| `SITE_USER`, `SITE_PASSWORD` | The site login. Compose refuses to start if either is empty |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | The key and the Flash model name |
| `SEGMENTER` | `grabcut` until the PyTorch segmenter is added |
| `PIPELINE`, `RENDER` | `stub` or `real`. Start on `stub`; switch one at a time |
| `MONGODB_URI` | Leave as is; Compose points the API at its own `mongo` container (data in the `mongo_data` volume) |
| `DATA_DIR` | Leave as is; Compose sets `/app/data` inside the container |

Keep the password free of `$` characters, or wrap it in single quotes: Compose reads `$` as a variable.

## Deploy

```bash
cd /opt/mirai && git pull && docker compose up -d --build
```

The first build takes a few minutes; later ones reuse the pip and npm layers unless a
requirements file or `package-lock.json` changed.

## Check it

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://140-82-15-107.sslip.io/api/books          # 401
curl -s -o /dev/null -w "%{http_code}\n" -u USER:PASSWORD https://140-82-15-107.sslip.io/api/books   # 200
docker compose ps
docker compose logs --tail 50 api
```

The first request after a fresh start can take a few seconds while Caddy gets its certificate.

## Roll back

```bash
cd /opt/mirai && git log --oneline -5
git checkout <previous commit> && docker compose up -d --build
```

Go back to the branch afterwards with `git checkout bryan`.

## Try it on a laptop

```bash
SITE_USER=test SITE_PASSWORD=test docker compose up -d --build
curl -k -u test:test https://localhost/api/books
docker compose down
```

`SITE_ADDRESS` empty means `localhost`, with Caddy's own certificate, hence `-k`.

## What is where

| File | What it does |
| --- | --- |
| `Dockerfile` | API image, Python 3.11. Installs every `*/requirements.txt` in one `pip install`, so clashing versions fail at build time |
| `infra/caddy.Dockerfile` | Builds the web app with Node, then puts it inside a Caddy image |
| `infra/caddy-start.sh` | Hashes `SITE_PASSWORD` at start-up; refuses to start an open site |
| `Caddyfile` | Password on every path, 55 MB request cap, `/api/*` to the API, everything else the web app |
| `compose.yaml` | The two services, the `./data` mount and the certificate volumes |
| `.dockerignore` | Keeps `.env`, `.git`, `data/` and local clutter out of the images |
