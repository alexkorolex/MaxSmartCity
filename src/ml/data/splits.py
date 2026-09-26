"""Leakage-safe dataset utilities independent of concrete record types."""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


class ScenarioBoundRecord(Protocol):
    @property
    def scenario_id(self) -> str: ...


@dataclass(frozen=True, slots=True)
class DatasetSplit[RecordT: ScenarioBoundRecord]:
    train: tuple[RecordT, ...]
    validation: tuple[RecordT, ...]
    test: tuple[RecordT, ...]


def split_by_scenario[RecordT: ScenarioBoundRecord](
    records: Iterable[RecordT], *, seed: int
) -> DatasetSplit[RecordT]:
    buckets: dict[str, list[RecordT]] = {"train": [], "validation": [], "test": []}
    for record in records:
        digest = hashlib.sha256(f"{seed}:{record.scenario_id}".encode()).digest()
        value = int.from_bytes(digest[:8]) % 100
        split = "train" if value < 70 else "validation" if value < 85 else "test"
        buckets[split].append(record)
    return DatasetSplit(
        train=tuple(buckets["train"]),
        validation=tuple(buckets["validation"]),
        test=tuple(buckets["test"]),
    )


def assert_no_scenario_leakage(split: DatasetSplit[ScenarioBoundRecord]) -> None:
    groups = [
        {record.scenario_id for record in split.train},
        {record.scenario_id for record in split.validation},
        {record.scenario_id for record in split.test},
    ]
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        msg = "scenario leakage detected between dataset splits"
        raise ValueError(msg)
