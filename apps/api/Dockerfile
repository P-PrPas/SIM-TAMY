# Build from the repo root: docker build -f apps/api/Dockerfile .
# content/ is baked in so a PaaS needs no bind mount (compose still mounts it for dev).
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 CONTENT_DIR=/srv/content
WORKDIR /srv/api

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
RUN pip install .

COPY apps/api/alembic.ini ./
COPY apps/api/migrations ./migrations
COPY content /srv/content
COPY recordings /recordings

# nothing here needs root; a compromised process should not own the container
RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT', '8000'))"
# The image migrates itself, so compose, Render and any other host start from an empty database the
# same way (alembic is idempotent). A failed migration stops the container before it serves; a
# database already ahead of this image (after a rollback) is served as is (app/db/migrate.py).
# PaaS hosts inject PORT; locally it stays 8000.
CMD ["sh", "-c", "python -m app.db.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
