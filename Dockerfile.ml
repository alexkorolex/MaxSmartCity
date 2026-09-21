# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY pyproject.toml uv.lock README.md main.py ./
COPY maxsmartcity ./maxsmartcity
COPY ml ./ml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev \
    && uv run python -m maxsmartcity.ml.training.cli \
       --config ml/configs/training/category-tfidf-logreg.v2.json


FROM python:3.12-slim AS runtime

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --from=builder --chown=app:app /app/main.py ./main.py
COPY --from=builder --chown=app:app /app/maxsmartcity ./maxsmartcity
COPY --from=builder --chown=app:app /app/ml/configs ./ml/configs
COPY --from=builder --chown=app:app /app/ml/artifacts ./ml/artifacts

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ML_ARTIFACT_DIR=/app/ml/artifacts/category-tfidf-logreg-v2 \
    ML_RULE_CONFIG=/app/ml/configs/rule-baseline.v1.json \
    ML_EXTRACTION_CONFIG=/app/ml/configs/extraction-rules.v1.json

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]

CMD ["litestar", "--app", "main:app", "run", "--host", "0.0.0.0", "--port", "8000"]
