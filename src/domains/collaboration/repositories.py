from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.collaboration.models import Assignment, WorkItem


class AssignmentRepository(SQLAlchemyAsyncRepository[Assignment]):
    model_type = Assignment


class WorkItemRepository(SQLAlchemyAsyncRepository[WorkItem]):
    model_type = WorkItem
