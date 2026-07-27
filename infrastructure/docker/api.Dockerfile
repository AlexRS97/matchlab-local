FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api:/app/packages

WORKDIR /app

COPY pyproject.toml ./
COPY apps/api ./apps/api
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]" && \
    groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app && \
    chown -R app:app /app

EXPOSE 8000

USER app
