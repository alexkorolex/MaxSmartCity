from datetime import UTC, datetime

from maxsmartcity.ml.evaluation.temporal_geo import (
    ArrivalBurst,
    CityBounds,
    aggregate_heatmap,
    generate_houses,
    generate_temporal_reports,
)


def test_temporal_burst_is_reproducible_and_spatially_bounded() -> None:
    bounds = CityBounds("bryansk", 53.20, 34.30, 53.30, 34.45)
    houses = generate_houses(bounds, 500, seed=42)
    kwargs = {
        "started_at": datetime(2026, 9, 25, tzinfo=UTC),
        "duration_minutes": 60,
        "baseline_reports_per_minute": 1.0,
        "bursts": (ArrivalBurst("power", 20, 15, 100, 53.24, 34.36),),
        "seed": 2026,
    }

    first = generate_temporal_reports(bounds, houses, **kwargs)
    second = generate_temporal_reports(bounds, houses, **kwargs)

    assert first == second
    assert sum(report.topic == "power" for report in first) > 500
    assert all(bounds.south <= report.latitude <= bounds.north for report in first)
    assert all(bounds.west <= report.longitude <= bounds.east for report in first)


def test_heatmap_preserves_report_count() -> None:
    bounds = CityBounds("bakhchysarai", 44.72, 33.82, 44.79, 33.91)
    houses = generate_houses(bounds, 100, seed=7)
    reports = generate_temporal_reports(
        bounds,
        houses,
        started_at=datetime(2026, 9, 25, tzinfo=UTC),
        duration_minutes=10,
        baseline_reports_per_minute=3,
        bursts=(),
        seed=8,
    )

    cells = aggregate_heatmap(reports)

    assert sum(cell.reports for cell in cells) == len(reports)
    assert all(cell.city == "bakhchysarai" for cell in cells)
