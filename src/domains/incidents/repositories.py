from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.incidents.models import Incident, ResolutionDispute


class IncidentRepository(SQLAlchemyAsyncRepository[Incident]):
    model_type = Incident


class ResolutionDisputeRepository(SQLAlchemyAsyncRepository[ResolutionDispute]):
    model_type = ResolutionDispute
