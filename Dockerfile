FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    ML_ARTIFACT_DIR=/app/ml/artifacts/category-tfidf-logreg-v2

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev \
    && uv run python -m maxsmartcity.ml.training.cli \
       --config ml/configs/training/category-tfidf-logreg.v2.json

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uv", "run", "litestar", "--app", "main:app", "run", "--host", "0.0.0.0", "--port", "8000"]
