from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get
from litestar.di import NamedDependency, Provide
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.incidents.models import Incident
from src.domains.incidents.schemas import IncidentReadDTO
from src.domains.incidents.services import IncidentService


def provide_incident_service(db_session: NamedDependency[AsyncSession]) -> IncidentService:
    return IncidentService(session=db_session, auto_commit=True)


class IncidentController(Controller):
    path = "/incidents"
    tags = ("incidents",)
    return_dto = IncidentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_incident_service, sync_to_thread=False)}

    @get("/", name="incidents:Incident:list")
    async def list_items(
        self,
        service: NamedDependency[IncidentService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Incident]:
        with database_action("list", "incidents.Incident"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="incidents:Incident:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[IncidentService]) -> Incident:
        with database_action("get", "incidents.Incident"):
            return await service.get(item_id)
