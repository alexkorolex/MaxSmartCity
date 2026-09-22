from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.incidents.models import Incident, ResolutionDispute
from src.domains.incidents.repositories import IncidentRepository, ResolutionDisputeRepository


class IncidentService(SQLAlchemyAsyncRepositoryService[Incident]):
    repository_type = IncidentRepository


class ResolutionDisputeService(SQLAlchemyAsyncRepositoryService[ResolutionDispute]):
    repository_type = ResolutionDisputeRepository
