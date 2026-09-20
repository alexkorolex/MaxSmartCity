from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.incidents.models import Incident
from src.domains.incidents.repositories import IncidentRepository


class IncidentService(SQLAlchemyAsyncRepositoryService[Incident]):
    repository_type = IncidentRepository
