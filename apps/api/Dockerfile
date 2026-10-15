# Build from the repo root: docker build -f apps/api/Dockerfile .
# content/ is baked in so a PaaS needs no bind mount (compose still mounts it for dev).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 CONTENT_DIR=/srv/content
WORKDIR /srv/api

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
RUN pip install .

COPY apps/api/alembic.ini ./
COPY apps/api/migrations ./migrations
COPY content /srv/content

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT', '8000'))"
# PaaS hosts inject PORT; locally it stays 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
