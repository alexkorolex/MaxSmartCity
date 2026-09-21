#!/usr/bin/env sh
set -eu

UV_CACHE_DIR="${UV_CACHE_DIR:-$(pwd)/.uv-cache}" \
  uv run python -m maxsmartcity.ml.training.cli \
  --config "${1:-ml/configs/training/category-tfidf-logreg.v2.json}"
