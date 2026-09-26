import os
from datetime import UTC, datetime
from time import perf_counter

import pytest

from src.ml.evaluation.temporal_geo import (
    ArrivalBurst,
    CityBounds,
    aggregate_heatmap,
    generate_houses,
    generate_temporal_reports,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LOAD_TESTS") != "1", reason="set RUN_LOAD_TESTS=1 for the city-scale load test"
)


def test_two_city_temporal_heatmap_load() -> None:
    scenarios = (
        (CityBounds("bryansk", 53.18, 34.25, 53.34, 34.50), 10_000, 53.24, 34.36),
        (CityBounds("bakhchysarai", 44.70, 33.78, 44.82, 33.96), 4_000, 44.75, 33.86),
    )
    started = perf_counter()
    total_reports = 0
    total_cells = 0
    for index, (bounds, house_count, latitude, longitude) in enumerate(scenarios):
        houses = generate_houses(bounds, house_count, seed=100 + index)
        reports = generate_temporal_reports(
            bounds,
            houses,
            started_at=datetime(2026, 9, 25, tzinfo=UTC),
            duration_minutes=120,
            baseline_reports_per_minute=50,
            bursts=(
                ArrivalBurst("power", 20, 30, 1_500, latitude, longitude, 0.025),
                ArrivalBurst("water", 70, 20, 2_000, latitude + 0.02, longitude + 0.02, 0.015),
            ),
            seed=500 + index,
        )
        cells = aggregate_heatmap(reports)
        assert sum(cell.reports for cell in cells) == len(reports)
        total_reports += len(reports)
        total_cells += len(cells)
    elapsed = perf_counter() - started

    print(
        f"reports={total_reports} cells={total_cells} elapsed_seconds={elapsed:.3f} "
        f"reports_per_second={total_reports / elapsed:.0f}"
    )

    assert total_reports >= 100_000
    assert total_cells > 0
    assert elapsed < 30
