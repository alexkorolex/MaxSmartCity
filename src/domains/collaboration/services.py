from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import select

from src.common.enums import ActorType
from src.common.models import utc_now
from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment, AssignmentStatusHistory, WorkItem
from src.domains.collaboration.repositories import AssignmentRepository, WorkItemRepository
from src.domains.collaboration.schemas import (
    CreateAssignmentCommand,
    CreateAssignmentResult,
    TransitionAssignmentCommand,
    TransitionAssignmentResult,
)
from src.domains.collaboration.state_machine import ensure_assignment_transition
from src.domains.identity.models import Organization
from src.domains.incidents.enums import IncidentStatus
from src.domains.incidents.models import Incident, IncidentStatusHistory
from src.domains.incidents.state_machine import ensure_incident_transition
from src.domains.infrastructure.models import OutboxEvent
from src.domains.notifications.dispatcher import OrganizationMessage, enqueue_organization_notification


class CollaborationNotFoundError(RuntimeError):
    pass


class CollaborationConflictError(RuntimeError):
    pass


class AssignmentService(SQLAlchemyAsyncRepositoryService[Assignment]):
    repository_type = AssignmentRepository

    async def create_for_incident(
        self, command: CreateAssignmentCommand, *, changed_by: UUID
    ) -> CreateAssignmentResult:
        session = self.repository.session
        incident = await session.scalar(
            select(Incident).where(Incident.id == command.incident_id).with_for_update()
        )
        if incident is None:
            raise CollaborationNotFoundError(f"Incident {command.incident_id} was not found")
        allowed = {
            IncidentStatus.CONFIRMED,
            IncidentStatus.ASSIGNED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.REOPENED,
        }
        if incident.status not in allowed:
            raise CollaborationConflictError(
                f"Assignment cannot be created in incident status {incident.status.value}"
            )
        organization = await session.get(Organization, command.organization_id)
        if organization is None or not organization.enabled:
            raise CollaborationNotFoundError(f"Enabled organization {command.organization_id} was not found")
        active = {
            AssignmentStatus.PROPOSED,
            AssignmentStatus.ACCEPTED,
            AssignmentStatus.IN_PROGRESS,
            AssignmentStatus.BLOCKED,
            AssignmentStatus.MONITORING,
        }
        duplicate = await session.scalar(
            select(Assignment.id).where(
                Assignment.incident_id == incident.id,
                Assignment.organization_id == organization.id,
                Assignment.role == command.role,
                Assignment.status.in_(active),
            )
        )
        if duplicate is not None:
            raise CollaborationConflictError(
                "An active assignment with this organization and role already exists"
            )
        if command.due_at is not None and command.due_at.tzinfo is None:
            raise CollaborationConflictError("due_at must include a timezone")

        assignment = Assignment(
            incident_id=incident.id,
            organization_id=organization.id,
            role=command.role,
            required=command.required,
            due_at=command.due_at,
        )
        session.add(assignment)
        await session.flush()
        session.add(
            AssignmentStatusHistory(
                assignment_id=assignment.id,
                from_status=None,
                to_status=AssignmentStatus.PROPOSED,
                changed_by=changed_by,
                reason="Assignment created",
            )
        )
        if incident.status in {IncidentStatus.CONFIRMED, IncidentStatus.REOPENED}:
            previous = incident.status
            ensure_incident_transition(previous, IncidentStatus.ASSIGNED)
            incident.status = IncidentStatus.ASSIGNED
            session.add(
                IncidentStatusHistory(
                    incident_id=incident.id,
                    from_status=previous,
                    to_status=IncidentStatus.ASSIGNED,
                    changed_by_type=ActorType.OPERATOR,
                    changed_by_id=changed_by,
                    reason="Executor assigned",
                )
            )
        session.add(
            OutboxEvent(
                aggregate_type="ASSIGNMENT",
                aggregate_id=assignment.id,
                event_type="ASSIGNMENT_CREATED",
                payload={
                    "assignment_id": str(assignment.id),
                    "incident_id": str(incident.id),
                    "organization_id": str(organization.id),
                    "role": command.role.value,
                },
            )
        )
        enqueue_organization_notification(
            session,
            OrganizationMessage(
                organization_id=organization.id,
                event_type="ASSIGNMENT_CREATED",
                title="Вам назначена заявка",
                body="\n".join(
                    part
                    for part in (
                        incident.title,
                        incident.description,
                        f"Срок: {command.due_at:%d.%m.%Y %H:%M}" if command.due_at else None,
                    )
                    if part
                ),
                incident_id=incident.id,
            ),
        )
        await session.flush()
        return CreateAssignmentResult(
            assignment_id=assignment.id,
            incident_id=incident.id,
            organization_id=organization.id,
            role=assignment.role,
            status=assignment.status,
            version=assignment.version,
        )

    async def transition(
        self,
        assignment_id: UUID,
        command: TransitionAssignmentCommand,
        *,
        changed_by: UUID,
    ) -> TransitionAssignmentResult:
        assignment = await self.repository.session.scalar(
            select(Assignment).where(Assignment.id == assignment_id).with_for_update()
        )
        if assignment is None:
            raise CollaborationNotFoundError(f"Assignment {assignment_id} was not found")
        if assignment.version != command.expected_version:
            raise CollaborationConflictError(
                f"Expected version {command.expected_version}, actual version {assignment.version}"
            )
        previous = assignment.status
        ensure_assignment_transition(previous, command.target_status)
        assignment.status = command.target_status
        now = utc_now()
        if command.target_status is AssignmentStatus.ACCEPTED:
            assignment.accepted_at = now
        elif command.target_status is AssignmentStatus.IN_PROGRESS:
            assignment.started_at = assignment.started_at or now
        elif command.target_status is AssignmentStatus.COMPLETED:
            assignment.completed_at = now
        self.repository.session.add(
            AssignmentStatusHistory(
                assignment_id=assignment.id,
                from_status=previous,
                to_status=command.target_status,
                changed_by=changed_by,
                reason=command.reason,
            )
        )
        self.repository.session.add(
            OutboxEvent(
                aggregate_type="ASSIGNMENT",
                aggregate_id=assignment.id,
                event_type="ASSIGNMENT_STATUS_CHANGED",
                payload={
                    "assignment_id": str(assignment.id),
                    "incident_id": str(assignment.incident_id),
                    "from_status": previous.value,
                    "to_status": command.target_status.value,
                },
            )
        )
        await self.repository.session.flush()
        return TransitionAssignmentResult(
            assignment_id=assignment.id,
            status=assignment.status,
            version=assignment.version,
        )


class WorkItemService(SQLAlchemyAsyncRepositoryService[WorkItem]):
    repository_type = WorkItemRepository
