# The API image: every Python folder's code and every folder's requirements.
# Build from the repo root:  docker compose build api

# Stage 1 collects every */requirements.txt, keeping its folder. Copying from this
# stage (not from the repo) means the pip layer below is rebuilt only when a
# requirements file changes, not on every code change.
FROM busybox:stable AS requirements
COPY . /src
RUN cd /src && for f in */requirements.txt; do mkdir -p "/requirements/$(dirname "$f")" && cp "$f" "/requirements/$f"; done

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ONE pip install for all folders, so two folders that want clashing versions fail
# here, at build time, and not when the modules are joined.
COPY --from=requirements /requirements/ ./
RUN pip install --no-cache-dir $(for f in */requirements.txt; do printf -- '-r %s ' "$f"; done)

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
