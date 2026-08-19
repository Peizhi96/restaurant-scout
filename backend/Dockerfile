FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY migrations ./migrations

FROM base AS test

COPY tests ./tests
RUN python -m pip install --no-cache-dir -e '.[dev]'

CMD ["sh", "-c", "ruff check . && pytest"]

FROM base AS runtime

RUN python -m pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
