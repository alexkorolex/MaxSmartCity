from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.incidents.models import Incident


class IncidentRepository(SQLAlchemyAsyncRepository[Incident]):
    model_type = Incident
