"""Deterministic city-scale arrival and heatmap simulation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np


@dataclass(frozen=True, slots=True)
class CityBounds:
    city: str
    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if not (-90 <= self.south < self.north <= 90):
            raise ValueError("invalid latitude bounds")
        if not (-180 <= self.west < self.east <= 180):
            raise ValueError("invalid longitude bounds")


@dataclass(frozen=True, slots=True)
class HousePoint:
    house_id: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class ArrivalBurst:
    topic: str
    start_minute: int
    duration_minutes: int
    peak_reports_per_minute: float
    latitude: float
    longitude: float
    radius_degrees: float = 0.02


@dataclass(frozen=True, slots=True)
class TemporalReport:
    report_id: str
    city: str
    house_id: str
    latitude: float
    longitude: float
    occurred_at: datetime
    topic: str


@dataclass(frozen=True, slots=True)
class HeatmapCell:
    city: str
    time_bucket: datetime
    latitude_bucket: int
    longitude_bucket: int
    reports: int


def generate_houses(bounds: CityBounds, count: int, *, seed: int) -> tuple[HousePoint, ...]:
    if count < 1:
        raise ValueError("count must be positive")
    rng = np.random.default_rng(seed)
    latitudes = rng.uniform(bounds.south, bounds.north, count)
    longitudes = rng.uniform(bounds.west, bounds.east, count)
    return tuple(
        HousePoint(f"{bounds.city.upper()}-{index:06d}", float(latitude), float(longitude))
        for index, (latitude, longitude) in enumerate(zip(latitudes, longitudes, strict=True))
    )


def generate_temporal_reports(
    bounds: CityBounds,
    houses: tuple[HousePoint, ...],
    *,
    started_at: datetime,
    duration_minutes: int,
    baseline_reports_per_minute: float,
    bursts: tuple[ArrivalBurst, ...],
    seed: int,
) -> tuple[TemporalReport, ...]:
    if not houses:
        raise ValueError("houses must not be empty")
    if duration_minutes < 1 or baseline_reports_per_minute < 0:
        raise ValueError("duration and baseline rate must be valid")
    rng = np.random.default_rng(seed)
    coordinates = np.asarray([(house.latitude, house.longitude) for house in houses])
    burst_house_probabilities = {burst: _nearby_house_probabilities(coordinates, burst) for burst in bursts}
    reports: list[TemporalReport] = []
    for minute in range(duration_minutes):
        active = tuple(burst for burst in bursts if _burst_weight(burst, minute) > 0)
        burst_rates = np.asarray([_burst_weight(burst, minute) for burst in active])
        total_rate = baseline_reports_per_minute + float(burst_rates.sum())
        arrivals = int(rng.poisson(total_rate))
        for _ in range(arrivals):
            use_burst = bool(active) and rng.random() >= baseline_reports_per_minute / total_rate
            if use_burst:
                selected_burst = active[int(rng.choice(len(active), p=burst_rates / burst_rates.sum()))]
                probabilities = burst_house_probabilities[selected_burst]
                house_index = int(rng.choice(len(coordinates), p=probabilities))
                topic = selected_burst.topic
            else:
                house_index = int(rng.integers(0, len(houses)))
                topic = "background"
            house = houses[house_index]
            second = int(rng.integers(0, 60))
            reports.append(
                TemporalReport(
                    report_id=f"LOAD-{len(reports):09d}",
                    city=bounds.city,
                    house_id=house.house_id,
                    latitude=house.latitude,
                    longitude=house.longitude,
                    occurred_at=started_at + timedelta(minutes=minute, seconds=second),
                    topic=topic,
                )
            )
    reports.sort(key=lambda report: (report.occurred_at, report.report_id))
    return tuple(reports)


def aggregate_heatmap(
    reports: tuple[TemporalReport, ...],
    *,
    spatial_cell_degrees: float = 0.005,
    time_bucket_minutes: int = 5,
) -> tuple[HeatmapCell, ...]:
    if spatial_cell_degrees <= 0 or time_bucket_minutes < 1:
        raise ValueError("heatmap bucket sizes must be positive")
    counts: dict[tuple[str, datetime, int, int], int] = {}
    for report in reports:
        bucket = report.occurred_at.replace(second=0, microsecond=0) - timedelta(
            minutes=report.occurred_at.minute % time_bucket_minutes
        )
        key = (
            report.city,
            bucket,
            int(np.floor(report.latitude / spatial_cell_degrees)),
            int(np.floor(report.longitude / spatial_cell_degrees)),
        )
        counts[key] = counts.get(key, 0) + 1
    return tuple(
        HeatmapCell(city, bucket, latitude, longitude, count)
        for (city, bucket, latitude, longitude), count in sorted(counts.items())
    )


def _burst_weight(burst: ArrivalBurst, minute: int) -> float:
    offset = minute - burst.start_minute
    if offset < 0 or offset >= burst.duration_minutes:
        return 0.0
    midpoint = (burst.duration_minutes - 1) / 2
    distance = abs(offset - midpoint) / max(midpoint, 1)
    return burst.peak_reports_per_minute * max(0.2, 1 - 0.8 * distance)


def _nearby_house_probabilities(coordinates: np.ndarray, burst: ArrivalBurst) -> np.ndarray:
    squared_distance = np.square(coordinates[:, 0] - burst.latitude) + np.square(
        coordinates[:, 1] - burst.longitude
    )
    weights = np.exp(-squared_distance / max(burst.radius_degrees**2, 1e-12))
    total = float(weights.sum())
    if not np.isfinite(total) or total == 0:
        weights.fill(0)
        weights[int(np.argmin(squared_distance))] = 1
        return weights
    return weights / total
