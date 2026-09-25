import os
from pathlib import Path

from litestar.plugins.prometheus import PrometheusConfig

_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _multiproc_dir:
    Path(_multiproc_dir).mkdir(parents=True, exist_ok=True)

prometheus_config = PrometheusConfig(app_name="maxsmartcity-backend")
