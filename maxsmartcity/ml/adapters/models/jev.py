"""Jev-like NLI data preparation and an explicit untrained adapter."""

import json
from dataclasses import asdict, dataclass
from typing import Literal, Never

from maxsmartcity.ml.domain.requests import DecisionRequest, IncidentCandidate
from maxsmartcity.ml.ports.models import ComponentUnavailableError

NliLabel = Literal["ENTAILMENT", "CONTRADICTION", "NEUTRAL"]


@dataclass(frozen=True, slots=True)
class NliExample:
    example_id: str
    premise: str
    hypothesis: str
    label: NliLabel
    candidate_id: str


def build_incident_nli_examples(
    request: DecisionRequest,
    *,
    target_incident_ids: frozenset[str],
    neutral_incident_ids: frozenset[str] = frozenset(),
) -> tuple[NliExample, ...]:
    allowed = {candidate.id for candidate in request.incident_candidates}
    unknown_targets = (target_incident_ids | neutral_incident_ids) - allowed
    if unknown_targets:
        msg = f"targets are absent from allowed candidates: {sorted(unknown_targets)}"
        raise ValueError(msg)
    premise = _render_premise(request)
    examples: list[NliExample] = []
    for candidate in request.incident_candidates:
        if candidate.id in target_incident_ids:
            label: NliLabel = "ENTAILMENT"
        elif candidate.id in neutral_incident_ids:
            label = "NEUTRAL"
        else:
            label = "CONTRADICTION"
        examples.append(
            NliExample(
                example_id=f"{request.request_id}:{candidate.id}",
                premise=premise,
                hypothesis=_render_incident_hypothesis(candidate),
                label=label,
                candidate_id=candidate.id,
            )
        )
    return tuple(examples)


class UntrainedJevIncidentRanker:
    """TODO[model]: implement after dataset validation and training on RTX 3060."""

    def rank(self, request: DecisionRequest) -> Never:
        del request
        msg = "Jev-like incident ranker has no trained and calibrated artifact"
        raise ComponentUnavailableError(msg)


def _render_premise(request: DecisionRequest) -> str:
    payload = {"report": asdict(request.report), "external_context": request.external_context}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _render_incident_hypothesis(candidate: IncidentCandidate) -> str:
    details = {
        "id": candidate.id,
        "title": candidate.title,
        "category_id": candidate.category_id,
        "affected_house_ids": candidate.affected_house_ids,
        "fias_guids": candidate.fias_guids,
        "status": candidate.status,
        "priority": candidate.priority,
        "started_at": candidate.started_at.isoformat(),
    }
    return "Сообщение относится к инциденту: " + json.dumps(details, ensure_ascii=False, sort_keys=True)
