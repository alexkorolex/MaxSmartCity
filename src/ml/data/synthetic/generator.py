"""Deterministic generation of linked city entities and labelled decisions."""

import hashlib
import random
from collections.abc import Iterator

from src.ml.data.synthetic.config import SyntheticArchetype, SyntheticConfig
from src.ml.data.synthetic.models import (
    CounterfactualRecord,
    DecisionRecord,
    ExternalEventRecord,
    HouseRecord,
    IncidentRecord,
    OrganizationRecord,
    ReportRecord,
    ScenarioRecord,
    SyntheticBundle,
)


class SyntheticWorldGenerator:
    def __init__(self, config: SyntheticConfig, *, master_seed: int) -> None:
        self.config = config
        self.master_seed = master_seed

    def generate_standard(
        self,
        *,
        scenario_count: int,
        reports_per_scenario: int,
        noise_reports: int = 0,
    ) -> SyntheticBundle:
        if scenario_count < 2:
            msg = "at least two scenarios are required for hard negatives"
            raise ValueError(msg)
        scenarios: list[ScenarioRecord] = []
        houses: list[HouseRecord] = []
        external_events: list[ExternalEventRecord] = []
        incidents: list[IncidentRecord] = []
        reports: list[ReportRecord] = []
        counterfactuals: list[CounterfactualRecord] = []

        for index in range(scenario_count):
            scenario_id = f"SCN-{index:05d}"
            incident_id = f"INC-{index:05d}"
            seed = stable_seed(self.master_seed, scenario_id, "scenario", self.config.version)
            rng = random.Random(seed)
            archetype = self.config.archetypes[index % len(self.config.archetypes)]
            street = rng.choice(self.config.streets)
            house_number = str(1 + index * 2)
            fias_guid = f"demo-fias-{index:05d}"
            started_at = f"2026-09-20T{8 + index % 10:02d}:00:00+03:00"
            scenarios.append(ScenarioRecord(scenario_id, self.config.city_id, archetype.id, seed))
            houses.append(
                HouseRecord(
                    house_id=f"HOUSE-{index:05d}",
                    scenario_id=scenario_id,
                    fias_guid=fias_guid,
                    street=street,
                    house_number=house_number,
                )
            )
            incidents.append(
                IncidentRecord(
                    incident_id,
                    scenario_id,
                    archetype.category_id,
                    archetype.organization_id,
                    (fias_guid,),
                    started_at,
                )
            )
            external_events.append(
                ExternalEventRecord(
                    external_event_id=f"EXT-{index:05d}",
                    scenario_id=scenario_id,
                    category_id=archetype.category_id,
                    affected_fias_guids=(fias_guid,),
                    organization_id=archetype.organization_id,
                    observed_at=started_at,
                )
            )
            for report_index in range(reports_per_scenario):
                report = self._generate_report(
                    scenario_id=scenario_id,
                    incident_id=incident_id,
                    report_index=report_index,
                    category_id=archetype.category_id,
                    organization_id=archetype.organization_id,
                    phrases=archetype.phrases,
                    street=street,
                    house_number=house_number,
                    fias_guid=fias_guid,
                    hour=8 + index % 10,
                )
                reports.append(report)
                if report_index == 0:
                    counterfactuals.append(
                        self._counterfactual_address(
                            report,
                            phrases=archetype.phrases,
                            street=street,
                            original_house=house_number,
                            mutated_house=str(int(house_number) + 1),
                        )
                    )

        noise = self._generate_noise(noise_reports)
        reports.extend(noise)
        scenarios.extend(
            ScenarioRecord(
                scenario_id=report.scenario_id,
                city_id=self.config.city_id,
                archetype_id="non-incident-noise",
                seed=report.generation_seed,
                scenario_kind="NOISE",
            )
            for report in noise
        )
        decisions = self._build_decisions(tuple(reports), tuple(incidents))
        organizations = tuple(
            OrganizationRecord(
                organization_id=archetype.organization_id,
                organization_type=archetype.organization_type,
                name=f"Demo {archetype.organization_id}",
            )
            for archetype in _unique_organizations(self.config)
        )
        return SyntheticBundle(
            scenarios=tuple(scenarios),
            houses=tuple(houses),
            organizations=organizations,
            external_events=tuple(external_events),
            incidents=tuple(incidents),
            reports=tuple(reports),
            decisions=decisions,
            counterfactuals=tuple(counterfactuals),
        )

    def generate_mass_outage(self, *, report_count: int) -> SyntheticBundle:
        if report_count < 1:
            msg = "report_count must be positive"
            raise ValueError(msg)
        archetype = self.config.archetypes[0]
        scenario_id = "STRESS-MASS-00001"
        incident_id = "STRESS-INC-00001"
        seed = stable_seed(self.master_seed, scenario_id, self.config.version)
        house_count = 100
        houses = tuple(
            HouseRecord(
                house_id=f"STRESS-HOUSE-{index:03d}",
                scenario_id=scenario_id,
                fias_guid=f"stress-fias-{index:03d}",
                street="Массовая улица",
                house_number=str(index + 1),
            )
            for index in range(house_count)
        )
        reports: list[ReportRecord] = []
        for index in range(report_count):
            house = houses[index % house_count]
            report_seed = stable_seed(self.master_seed, scenario_id, str(index), "stress-report")
            rng = random.Random(report_seed)
            reports.append(
                ReportRecord(
                    report_id=f"STRESS-REP-{index:05d}",
                    scenario_id=scenario_id,
                    incident_id=incident_id,
                    text=_corrupt(
                        rng.choice(archetype.phrases) + f" на Массовой улице, дом {house.house_number}",
                        rng,
                    ),
                    category_id=archetype.category_id,
                    organization_id=archetype.organization_id,
                    fias_guid=house.fias_guid,
                    timestamp=f"2026-09-20T10:{index % 60:02d}:{index % 60:02d}+03:00",
                    style_id="stress-burst",
                    generation_seed=report_seed,
                    paraphrase_family_id=scenario_id,
                )
            )
        incident = IncidentRecord(
            incident_id,
            scenario_id,
            archetype.category_id,
            archetype.organization_id,
            tuple(house.fias_guid for house in houses),
            "2026-09-20T10:00:00+03:00",
        )
        return SyntheticBundle(
            scenarios=(
                ScenarioRecord(
                    scenario_id,
                    self.config.city_id,
                    archetype.id,
                    seed,
                    "MASS_OUTAGE",
                ),
            ),
            houses=houses,
            organizations=(
                OrganizationRecord(
                    archetype.organization_id,
                    archetype.organization_type,
                    f"Demo {archetype.organization_id}",
                ),
            ),
            external_events=(
                ExternalEventRecord(
                    "STRESS-EXT-00001",
                    scenario_id,
                    archetype.category_id,
                    tuple(house.fias_guid for house in houses),
                    archetype.organization_id,
                    "2026-09-20T10:00:00+03:00",
                ),
            ),
            incidents=(incident,),
            reports=tuple(reports),
            decisions=tuple(
                DecisionRecord(
                    f"DEC-{report.report_id}",
                    scenario_id,
                    report.report_id,
                    (incident_id,),
                    (incident_id,),
                    (),
                )
                for report in reports
            ),
            counterfactuals=(),
        )

    def _generate_report(
        self,
        *,
        scenario_id: str,
        incident_id: str,
        report_index: int,
        category_id: str,
        organization_id: str,
        phrases: tuple[str, ...],
        street: str,
        house_number: str,
        fias_guid: str,
        hour: int,
    ) -> ReportRecord:
        report_id = f"{scenario_id}-REP-{report_index:04d}"
        seed = stable_seed(self.master_seed, scenario_id, report_id, "text", self.config.version)
        text, style_index = self._render_report_text(
            seed=seed,
            phrases=phrases,
            street=street,
            house_number=house_number,
        )
        return ReportRecord(
            report_id=report_id,
            scenario_id=scenario_id,
            incident_id=incident_id,
            text=text,
            category_id=category_id,
            organization_id=organization_id,
            fias_guid=fias_guid,
            timestamp=f"2026-09-20T{hour:02d}:{report_index % 60:02d}:00+03:00",
            style_id=f"style-{style_index}",
            generation_seed=seed,
            paraphrase_family_id=f"FAMILY-{scenario_id}",
        )

    def _counterfactual_address(
        self,
        report: ReportRecord,
        *,
        phrases: tuple[str, ...],
        street: str,
        original_house: str,
        mutated_house: str,
    ) -> CounterfactualRecord:
        return CounterfactualRecord(
            counterfactual_id=f"CF-{report.report_id}-HOUSE",
            scenario_id=report.scenario_id,
            source_report_id=report.report_id,
            mutated_field="house",
            original_value=original_house,
            mutated_value=mutated_house,
            text=self._render_report_text(
                seed=report.generation_seed,
                phrases=phrases,
                street=street,
                house_number=mutated_house,
            )[0],
        )

    def _render_report_text(
        self,
        *,
        seed: int,
        phrases: tuple[str, ...],
        street: str,
        house_number: str,
    ) -> tuple[str, int]:
        rng = random.Random(seed)
        style_index = rng.randrange(len(self.config.styles))
        text = self.config.styles[style_index].format(
            problem=rng.choice(phrases),
            street=street,
            house=house_number,
            duration=rng.randint(1, 12),
        )
        return _corrupt(text, rng), style_index

    def _generate_noise(self, count: int) -> list[ReportRecord]:
        noise: list[ReportRecord] = []
        for index in range(count):
            report_id = f"NOISE-REP-{index:05d}"
            seed = stable_seed(self.master_seed, report_id, "noise", self.config.version)
            rng = random.Random(seed)
            noise.append(
                ReportRecord(
                    report_id=report_id,
                    scenario_id=f"NOISE-SCN-{index:05d}",
                    incident_id=None,
                    text=rng.choice(self.config.noise_phrases),
                    category_id="non_incident",
                    organization_id=None,
                    fias_guid=None,
                    timestamp="2026-09-20T12:00:00+03:00",
                    style_id="noise",
                    generation_seed=seed,
                    needs_clarification=False,
                    supported_by_context=False,
                )
            )
        return noise

    @staticmethod
    def _build_decisions(
        reports: tuple[ReportRecord, ...],
        incidents: tuple[IncidentRecord, ...],
    ) -> tuple[DecisionRecord, ...]:
        by_category: dict[str, list[IncidentRecord]] = {}
        for incident in incidents:
            by_category.setdefault(incident.category_id, []).append(incident)
        decisions: list[DecisionRecord] = []
        for report in reports:
            if report.incident_id is None:
                decisions.append(
                    DecisionRecord(
                        f"DEC-{report.report_id}",
                        report.scenario_id,
                        report.report_id,
                        (),
                        (),
                        (),
                    )
                )
                continue
            same_category = by_category.get(report.category_id, [])
            negatives = tuple(
                item.incident_id for item in same_category if item.incident_id != report.incident_id
            )[:2]
            if not negatives:
                negatives = tuple(
                    item.incident_id for item in incidents if item.incident_id != report.incident_id
                )[:1]
            decisions.append(
                DecisionRecord(
                    decision_id=f"DEC-{report.report_id}",
                    scenario_id=report.scenario_id,
                    report_id=report.report_id,
                    candidate_incident_ids=(report.incident_id, *negatives),
                    target_incident_ids=(report.incident_id,),
                    hard_negative_incident_ids=negatives,
                )
            )
        return tuple(decisions)


def stable_seed(master_seed: int, *parts: str) -> int:
    payload = ":".join((str(master_seed), *parts)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8])


def _corrupt(text: str, rng: random.Random) -> str:
    if rng.random() < 0.2:
        text = text.replace("!", "!!!")
    if rng.random() < 0.15:
        text = text.lower()
    if rng.random() < 0.1:
        text = text.replace("воды", "вады")
    if rng.random() < 0.05:
        text += " 😡"
    return text


def _unique_organizations(config: SyntheticConfig) -> Iterator[SyntheticArchetype]:
    seen: set[str] = set()
    for archetype in config.archetypes:
        if archetype.organization_id not in seen:
            seen.add(archetype.organization_id)
            yield archetype
