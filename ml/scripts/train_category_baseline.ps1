param(
    [string]$Config = "ml/configs/training/category-tfidf-logreg.v2.json"
)

$ErrorActionPreference = "Stop"
$env:UV_CACHE_DIR = Join-Path (Get-Location) ".uv-cache"
uv run python -m maxsmartcity.ml.training.cli --config $Config
