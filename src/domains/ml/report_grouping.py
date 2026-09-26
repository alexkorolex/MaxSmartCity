"""Backend orchestration for advisory ``other`` incident recommendations."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.incidents.models import Incident, IncidentGroupingDecision, IncidentReportLink
from src.domains.incidents.schemas import GroupingCandidate
from src.domains.incidents.services.base import ACTIVE_INCIDENT_STATUSES
from src.domains.ml.client import MLDecisionClient
from src.domains.reports.models import ProblemCategory, Report

_CONTRACT_VERSION = "2.0.0-draft"
_MINIMUM_SCORE = 0.88
_MAX_RECOMMENDATIONS = 3
_MAX_REPRESENTATIVE_TEXTS = 20
_EXACT_SCORER_VERSION = "normalized-exact-text-v1"
_HEADLINE_LENGTH = 80
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")


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

        recommendations = await self._rank(report, decision, candidate_ids)
        return replace(recommendations, candidates=await self._describe(recommendations.candidates))

    async def _rank(
        self,
        report: Report,
        decision: IncidentGroupingDecision,
        candidate_ids: list[UUID],
    ) -> GroupingRecommendations:
        incidents = await self._load_incidents(candidate_ids)
        category_code = await self.session.scalar(
            select(ProblemCategory.code).where(ProblemCategory.id == report.category_id)
        )
        if category_code != "other":
            return GroupingRecommendations(
                [_candidate(incidents[item]) for item in candidate_ids if item in incidents]
            )

        representative_texts = await self._load_representative_texts(candidate_ids)
        exact_ids = _exact_candidate_ids(
            report.text or "",
            candidate_ids,
            incidents,
            representative_texts,
        )
        if exact_ids:
            return GroupingRecommendations(
                [_candidate(incidents[item], score=1.0) for item in exact_ids],
                _EXACT_SCORER_VERSION,
            )

        result = await self.client.recommend_grouping(
            self._payload(report, decision, candidate_ids, incidents, representative_texts)
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

    async def _describe(self, candidates: list[GroupingCandidate]) -> list[GroupingCandidate]:
        if not candidates:
            return candidates
        ids = [candidate.incident_id for candidate in candidates]
        reports = dict(
            (
                await self.session.execute(
                    select(IncidentReportLink.incident_id, func.count())
                    .where(IncidentReportLink.incident_id.in_(ids), IncidentReportLink.is_active.is_(True))
                    .group_by(IncidentReportLink.incident_id)
                )
            )
            .tuples()
            .all()
        )
        details = {
            row.id: row
            for row in (
                await self.session.execute(
                    select(
                        Incident.id,
                        Incident.first_report_at,
                        Incident.last_report_at,
                        Incident.created_at,
                        ProblemCategory.name.label("category_name"),
                    )
                    .join(ProblemCategory, ProblemCategory.id == Incident.category_id)
                    .where(Incident.id.in_(ids))
                )
            ).all()
        }
        described = []
        for candidate in candidates:
            row = details.get(candidate.incident_id)
            described.append(
                replace(
                    candidate,
                    headline=headline_from(candidate.description) or candidate.title,
                    category_name=row.category_name if row else None,
                    reports_count=reports.get(candidate.incident_id, 0),
                    first_report_at=(row.first_report_at or row.created_at) if row else None,
                    last_report_at=row.last_report_at if row else None,
                )
            )
        return described

    async def _load_incidents(self, candidate_ids: list[UUID]) -> dict[UUID, Incident]:
        values = await self.session.scalars(
            select(Incident).where(
                Incident.id.in_(candidate_ids),
                Incident.status.in_(ACTIVE_INCIDENT_STATUSES),
            )
        )
        return {incident.id: incident for incident in values.all()}

    async def _load_representative_texts(
        self,
        candidate_ids: list[UUID],
    ) -> dict[UUID, list[str]]:
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
        return texts

    @staticmethod
    def _payload(
        report: Report,
        decision: IncidentGroupingDecision,
        candidate_ids: list[UUID],
        incidents: dict[UUID, Incident],
        texts: dict[UUID, list[str]],
    ) -> dict[str, Any]:
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


def headline_from(text: str | None) -> str | None:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None
    sentence = _SENTENCE_END.split(cleaned, maxsplit=1)[0].rstrip(".!?… ")
    if len(sentence) > _HEADLINE_LENGTH:
        cut = sentence[:_HEADLINE_LENGTH].rsplit(" ", 1)[0].rstrip(",;:—- ")
        sentence = f"{cut}…"
    return sentence[:1].upper() + sentence[1:]


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


def _exact_candidate_ids(
    report_text: str,
    candidate_ids: list[UUID],
    incidents: dict[UUID, Incident],
    representative_texts: dict[UUID, list[str]],
) -> list[UUID]:
    normalized_report = _normalize_text(report_text)
    if not normalized_report:
        return []
    matches = [
        incident_id
        for incident_id in candidate_ids
        if incident_id in incidents
        and normalized_report
        in {
            _normalize_text(incidents[incident_id].description or ""),
            *(_normalize_text(value) for value in representative_texts.get(incident_id, [])),
        }
    ]
    return matches[:_MAX_RECOMMENDATIONS]


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


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
