from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.collaboration.models import Assignment, WorkItem
from src.domains.collaboration.repositories import AssignmentRepository, WorkItemRepository


class AssignmentService(SQLAlchemyAsyncRepositoryService[Assignment]):
    repository_type = AssignmentRepository


class WorkItemService(SQLAlchemyAsyncRepositoryService[WorkItem]):
    repository_type = WorkItemRepository
