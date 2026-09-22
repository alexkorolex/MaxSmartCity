from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.enums import ActorType, Priority
from src.common.models import Association, Record, VersionedEntity, utc_now
from src.database.spatial import GeometryText
from src.domains.incidents.enums import (
    AffectedHouseSource,
    GroupingOutcome,
    IncidentRelationType,
    IncidentStatus,
    LinkSource,
    ResolutionDisputeStatus,
)


class Incident(VersionedEntity):
    __tablename__ = "incident"
    __table_args__ = (
        Index("ix_incident_grouping_candidates", "category_id", "status", "last_report_at"),
        {"schema": "incidents"},
    )

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("reports.problem_category.id"))
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, create_constraint=True, name="incident_status"),
        default=IncidentStatus.NEW,
        server_default=IncidentStatus.NEW.value,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, create_constraint=True, name="incident_priority"),
        default=Priority.NORMAL,
        server_default=Priority.NORMAL.value,
    )
    affected_area: Mapped[str | None] = mapped_column(GeometryText("MULTIPOLYGON", srid=4326))
    first_report_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_report_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_resolution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentReportLink(Record):
    __tablename__ = "incident_report_link"
    __table_args__ = (
        Index(
            "uq_incident_report_active",
            "report_id",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
        {"schema": "incidents"},
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.report.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    link_source: Mapped[LinkSource] = mapped_column(
        Enum(LinkSource, native_enum=False, create_constraint=True, name="incident_link_source")
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric)
    reason_codes: Mapped[list[str] | None] = mapped_column(JSONB)
    linked_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.operator_user.id"))
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unlink_reason: Mapped[str | None] = mapped_column(Text)


class IncidentGroupingDecision(Record):
    """Immutable explanation of an automatic or user-confirmed grouping decision."""

    __tablename__ = "incident_grouping_decision"
    __table_args__ = ({"schema": "incidents"},)

    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.report.id"), index=True)
    outcome: Mapped[GroupingOutcome] = mapped_column(
        Enum(GroupingOutcome, native_enum=False, create_constraint=True, name="grouping_outcome")
    )
    selected_incident_id: Mapped[UUID | None] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    runner_up_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    candidate_incident_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    policy_version: Mapped[str] = mapped_column(String(64))
    scorer_version: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[UUID | None] = mapped_column()


class IncidentAffectedHouse(Association):
    __tablename__ = "incident_affected_house"
    __table_args__ = (
        Index("ix_incident_affected_house_house", "house_id", "incident_id"),
        {"schema": "incidents"},
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), primary_key=True)
    house_id: Mapped[UUID] = mapped_column(ForeignKey("geo.house.id"), primary_key=True)
    source: Mapped[AffectedHouseSource] = mapped_column(
        Enum(
            AffectedHouseSource,
            native_enum=False,
            create_constraint=True,
            name="incident_affected_house_source",
        )
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class IncidentStatusHistory(Record):
    __tablename__ = "incident_status_history"
    __table_args__ = ({"schema": "incidents"},)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    from_status: Mapped[IncidentStatus | None] = mapped_column(
        Enum(
            IncidentStatus,
            native_enum=False,
            create_constraint=True,
            name="incident_previous_status",
        )
    )
    to_status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, create_constraint=True, name="incident_next_status")
    )
    changed_by_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, native_enum=False, create_constraint=True, name="incident_changed_by_type")
    )
    changed_by_id: Mapped[UUID | None] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[UUID | None] = mapped_column()


class IncidentRelation(Record):
    __tablename__ = "incident_relation"
    __table_args__ = (
        CheckConstraint(
            "source_incident_id <> target_incident_id", name="incident_relation_distinct_incidents"
        ),
        {"schema": "incidents"},
    )

    source_incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    target_incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    type: Mapped[IncidentRelationType] = mapped_column(
        Enum(
            IncidentRelationType,
            native_enum=False,
            create_constraint=True,
            name="incident_relation_type",
        )
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))


class ResolutionDispute(Record):
    __tablename__ = "resolution_dispute"
    __table_args__ = ({"schema": "incidents"},)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    resident_id: Mapped[UUID] = mapped_column(ForeignKey("identity.resident.id"))
    report_id: Mapped[UUID | None] = mapped_column(ForeignKey("reports.report.id"))
    status: Mapped[ResolutionDisputeStatus] = mapped_column(
        Enum(
            ResolutionDisputeStatus,
            native_enum=False,
            create_constraint=True,
            name="resolution_dispute_status",
        ),
        default=ResolutionDisputeStatus.OPEN,
        server_default=ResolutionDisputeStatus.OPEN.value,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.operator_user.id"))
