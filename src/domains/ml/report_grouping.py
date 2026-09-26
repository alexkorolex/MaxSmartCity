"""Backend orchestration for advisory ``other`` incident recommendations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.incidents.models import Incident, IncidentGroupingDecision, IncidentReportLink
from src.domains.incidents.schemas import GroupingCandidate
from src.domains.ml.client import MLDecisionClient
from src.domains.reports.models import ProblemCategory, Report

_CONTRACT_VERSION = "2.0.0-draft"
_MINIMUM_SCORE = 0.88
_MAX_RECOMMENDATIONS = 3
_MAX_REPRESENTATIVE_TEXTS = 20


@dataclass(frozen=True, slots=True)
class GroupingRecommendations:
    candidates: list[GroupingCandidate]
    scorer_version: str | None = None


class ReportGroupingRecommendationService:
    """Rank backend-filtered candidates without granting ML write access."""

    def __init__(self, session: AsyncSession, client: MLDecisionClient) -> None:
        self.session = session
        self.client = client

    async def recommend(
        self,
        report: Report,
        decision: IncidentGroupingDecision,
    ) -> GroupingRecommendations:
        candidate_ids = _candidate_ids(decision.candidate_incident_ids)
        if not candidate_ids:
            return GroupingRecommendations([])

        incidents = await self._load_incidents(candidate_ids)
        category_code = await self.session.scalar(
            select(ProblemCategory.code).where(ProblemCategory.id == report.category_id)
        )
        if category_code != "other":
            return GroupingRecommendations(
                [_candidate(incidents[item]) for item in candidate_ids if item in incidents]
            )

        result = await self.client.recommend_grouping(
            await self._payload(report, decision, candidate_ids, incidents)
        )
        if result.status_code != 200:
            return GroupingRecommendations([])

        ranked = _ranked_scores(result.body, allowed_ids=set(candidate_ids))
        candidates = [
            _candidate(incidents[incident_id], score=score)
            for incident_id, score in ranked
            if incident_id in incidents
        ]
        scorer = result.body.get("scorer_version")
        return GroupingRecommendations(candidates, scorer if isinstance(scorer, str) else None)

    async def _load_incidents(self, candidate_ids: list[UUID]) -> dict[UUID, Incident]:
        values = await self.session.scalars(select(Incident).where(Incident.id.in_(candidate_ids)))
        return {incident.id: incident for incident in values.all()}

    async def _payload(
        self,
        report: Report,
        decision: IncidentGroupingDecision,
        candidate_ids: list[UUID],
        incidents: dict[UUID, Incident],
    ) -> dict[str, Any]:
        rows = (
            await self.session.execute(
                select(IncidentReportLink.incident_id, Report.text)
                .join(Report, Report.id == IncidentReportLink.report_id)
                .where(
                    IncidentReportLink.incident_id.in_(candidate_ids),
                    IncidentReportLink.is_active.is_(True),
                    Report.text.is_not(None),
                )
                .order_by(Report.received_at.desc(), Report.id)
            )
        ).all()
        texts: dict[UUID, list[str]] = defaultdict(list)
        for incident_id, text in rows:
            if text and len(texts[incident_id]) < _MAX_REPRESENTATIVE_TEXTS:
                texts[incident_id].append(text)

        occurred_at = report.occurred_at or report.received_at or report.created_at
        return {
            "contract_version": _CONTRACT_VERSION,
            "request_id": str(decision.request_id or decision.id),
            "report": {"text": report.text or "", "occurred_at": occurred_at.isoformat()},
            "candidate_incidents": [
                {
                    "id": str(incident_id),
                    "title": incidents[incident_id].title,
                    "representative_texts": [
                        value for value in (incidents[incident_id].description, *texts[incident_id]) if value
                    ][:_MAX_REPRESENTATIVE_TEXTS],
                    "last_activity_at": (
                        incidents[incident_id].last_report_at
                        or incidents[incident_id].first_report_at
                        or incidents[incident_id].created_at
                    ).isoformat(),
                }
                for incident_id in candidate_ids
                if incident_id in incidents
            ],
        }


def _candidate_ids(values: list[str]) -> list[UUID]:
    result: list[UUID] = []
    for value in values:
        try:
            result.append(UUID(value))
        except (TypeError, ValueError):
            continue
    return result


def _candidate(incident: Incident, *, score: float | None = None) -> GroupingCandidate:
    return GroupingCandidate(
        incident_id=incident.id,
        title=incident.title,
        description=incident.description,
        score=score,
    )


def _ranked_scores(body: dict[str, Any], *, allowed_ids: set[UUID]) -> list[tuple[UUID, float]]:
    payload = body.get("candidates")
    if not isinstance(payload, list):
        return []
    ranked: list[tuple[UUID, float]] = []
    seen: set[UUID] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            incident_id = UUID(str(item.get("incident_id")))
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        if incident_id not in allowed_ids or incident_id in seen or not _MINIMUM_SCORE <= score <= 1:
            continue
        seen.add(incident_id)
        ranked.append((incident_id, score))
    ranked.sort(key=lambda item: (-item[1], str(item[0])))
    return ranked[:_MAX_RECOMMENDATIONS]
