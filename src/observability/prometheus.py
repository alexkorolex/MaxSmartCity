import os
from pathlib import Path

from litestar.plugins.prometheus import PrometheusConfig

# WEB_CONCURRENCY>1 means multiple worker processes, each importing this module (and thus
# this Counter/Histogram) independently - without prometheus_client's multiprocess mode,
# each worker keeps its own private registry, so a given /metrics scrape only reflects
# whichever single worker happened to answer it, silently dropping the others' traffic.
# Setting PROMETHEUS_MULTIPROC_DIR (done in docker-compose, pointed at the tmpfs /tmp
# mount) makes prometheus_client write each worker's counters to its own file there and
# litestar's PrometheusController (see its source) auto-detects the env var and merges
# all workers' files on every scrape instead of reading just its own process's registry.
# Must happen here, at import time, before PrometheusConfig builds the metric objects -
# by the time docker-compose's `environment:` reaches this process, the var is already
# set (Docker sets it before Python even starts), so this runs early enough.
_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _multiproc_dir:
    Path(_multiproc_dir).mkdir(parents=True, exist_ok=True)

# ``app_name`` becomes the ``app_name`` label on every ``litestar_*`` metric - naming it
# after this service (rather than the generic default "litestar") is what lets the
# Grafana dashboard's queries scope to this app specifically, and keeps metrics from
# multiple litestar services distinguishable if another one starts exporting too.
prometheus_config = PrometheusConfig(app_name="maxsmartcity-backend")
