"""Small fail-closed HTTP adapter for ML recommendations."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MLHTTPResult:
    status_code: int
    body: dict[str, Any]


class MLDecisionClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @classmethod
    def from_environment(cls) -> MLDecisionClient:
        base_url = os.environ.get("ML_SERVICE_URL", "http://ml-service:8000")
        timeout = float(os.environ.get("ML_REQUEST_TIMEOUT_SECONDS", "5"))
        if timeout <= 0:
            raise ValueError("ML_REQUEST_TIMEOUT_SECONDS must be positive")
        return cls(base_url, timeout_seconds=timeout)

    async def readiness(self) -> MLHTTPResult:
        return await self._request("GET", "/ready")

    async def decide(self, payload: dict[str, Any]) -> MLHTTPResult:
        return await self._request("POST", "/v1/decide", json=payload)

    async def recommend_grouping(self, payload: dict[str, Any]) -> MLHTTPResult:
        """Ask for an advisory semantic match; callers must keep a non-ML fallback."""

        return await self._request("POST", "/v1/grouping:recommend", json=payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> MLHTTPResult:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.request(method, path, json=json)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            # Callers fall back to rules, so this is not an error for the request - but a
            # silently dead ML service would never be noticed otherwise.
            logger.warning(
                "ML service is unreachable, falling back",
                extra={"method": method, "path": path, "ml_base_url": self._base_url},
                exc_info=True,
            )
            return MLHTTPResult(
                status_code=503,
                body={
                    "request_id": json.get("request_id") if json else None,
                    "code": "MODEL_UNAVAILABLE",
                    "message": type(exc).__name__,
                    "retryable": True,
                },
            )
        try:
            body = response.json()
        except ValueError:
            logger.warning(
                "ML service returned a non-JSON response",
                extra={
                    "path": path,
                    "status_code": response.status_code,
                    "body_preview": response.text[:200],
                },
            )
            body = {
                "request_id": json.get("request_id") if json else None,
                "code": "MODEL_UNAVAILABLE",
                "message": "ML service returned a non-JSON response",
                "retryable": response.status_code >= 500,
            }
        if not isinstance(body, dict):
            body = {
                "request_id": json.get("request_id") if json else None,
                "code": "MODEL_UNAVAILABLE",
                "message": "ML service returned an invalid response envelope",
                "retryable": response.status_code >= 500,
            }
        return MLHTTPResult(status_code=response.status_code, body=body)
