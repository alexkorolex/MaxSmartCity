from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import select

from src.common.models import utc_now
from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment, AssignmentStatusHistory, WorkItem
from src.domains.collaboration.repositories import AssignmentRepository, WorkItemRepository
from src.domains.collaboration.schemas import (
    TransitionAssignmentCommand,
    TransitionAssignmentResult,
)
from src.domains.collaboration.state_machine import ensure_assignment_transition


class CollaborationNotFoundError(RuntimeError):
    pass


class CollaborationConflictError(RuntimeError):
    pass


class AssignmentService(SQLAlchemyAsyncRepositoryService[Assignment]):
    repository_type = AssignmentRepository

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
        await self.repository.session.flush()
        return TransitionAssignmentResult(
            assignment_id=assignment.id,
            status=assignment.status,
            version=assignment.version,
        )


class WorkItemService(SQLAlchemyAsyncRepositoryService[WorkItem]):
    repository_type = WorkItemRepository
