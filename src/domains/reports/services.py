from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.reports.models import ProblemCategory, Report
from src.domains.reports.repositories import ProblemCategoryRepository, ReportRepository


class ProblemCategoryService(SQLAlchemyAsyncRepositoryService[ProblemCategory]):
    repository_type = ProblemCategoryRepository


class ReportService(SQLAlchemyAsyncRepositoryService[Report]):
    repository_type = ReportRepository
