from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.reports.models import ProblemCategory, Report


class ProblemCategoryRepository(SQLAlchemyAsyncRepository[ProblemCategory]):
    model_type = ProblemCategory


class ReportRepository(SQLAlchemyAsyncRepository[Report]):
    model_type = Report
