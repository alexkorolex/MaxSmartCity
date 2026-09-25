"""Backend-owned gateway to the standalone ML service."""

from typing import Any

from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.response import Response

from src.domains.ml.client import MLDecisionClient


def provide_ml_decision_client() -> MLDecisionClient:
    return MLDecisionClient.from_environment()


class MLController(Controller):
    path = "/ml"
    tags = ("ml",)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"client": Provide(provide_ml_decision_client, sync_to_thread=False)}

    @get("/health", name="ml:health")
    async def health(self, client: NamedDependency[MLDecisionClient]) -> Response[dict[str, Any]]:
        result = await client.readiness()
        return Response(content=result.body, status_code=result.status_code)

    @post("/decide", name="ml:decide", status_code=200)
    async def decide(
        self,
        data: dict[str, Any],
        client: NamedDependency[MLDecisionClient],
    ) -> Response[dict[str, Any]]:
        result = await client.decide(data)
        return Response(content=result.body, status_code=result.status_code)

    @post("/grouping/recommend", name="ml:grouping:recommend", status_code=200)
    async def recommend_grouping(
        self,
        data: dict[str, Any],
        client: NamedDependency[MLDecisionClient],
    ) -> Response[dict[str, Any]]:
        """Проксирует необязательную ML-рекомендацию, не изменяя Incident Core."""
        result = await client.recommend_grouping(data)
        return Response(content=result.body, status_code=result.status_code)
