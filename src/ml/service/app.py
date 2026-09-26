"""Litestar application exposing bounded, versioned ML inference."""

from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from litestar import Litestar, get, post
from litestar.response import Response

from src.ml.adapters.embeddings.fastembed import DEFAULT_MODEL as DEFAULT_SEMANTIC_MODEL
from src.ml.domain.results import CONTRACT_VERSION
from src.ml.service.runtime import (
    MLRuntime,
    RequestValidationError,
    decision_response_to_dict,
    metadata_to_dict,
)


def _error(
    code: str,
    message: str,
    *,
    status_code: int,
    request_id: str | None = None,
    retryable: bool = False,
) -> Response[dict[str, Any]]:
    return Response(
        content={
            "request_id": request_id,
            "code": code,
            "message": message,
            "retryable": retryable,
        },
        status_code=status_code,
    )


def create_app(runtime: MLRuntime | None = None) -> Litestar:
    semantic_enabled = os.getenv("ML_SEMANTIC_ENABLED", "false").casefold() in {"1", "true", "yes"}
    active_runtime = runtime or MLRuntime.load(
        artifact_dir=Path(os.getenv("ML_ARTIFACT_DIR", "ml/artifacts/category-tfidf-logreg-v2")),
        rule_config_path=Path(os.getenv("ML_RULE_CONFIG", "ml/configs/rule-baseline.v1.json")),
        extraction_config_path=Path(os.getenv("ML_EXTRACTION_CONFIG", "ml/configs/extraction-rules.v1.json")),
        max_input_characters=int(os.getenv("ML_MAX_INPUT_CHARACTERS", "4000")),
        semantic_model_name=(
            os.getenv(
                "ML_SEMANTIC_MODEL",
                DEFAULT_SEMANTIC_MODEL,
            )
            if semantic_enabled
            else None
        ),
        semantic_cache_dir=Path(os.getenv("ML_SEMANTIC_CACHE_DIR", "ml/models")),
    )

    @get("/health", sync_to_thread=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @get("/ready", sync_to_thread=False)
    def ready() -> Response[dict[str, Any]]:
        reasons = () if active_runtime.ready else (active_runtime.artifact_error,)
        return Response(
            content={"ready": active_runtime.ready, "reasons": reasons},
            status_code=200 if active_runtime.ready else 503,
        )

    @get("/v1/models", sync_to_thread=False)
    def models() -> dict[str, Any]:
        return {
            "models": [metadata_to_dict(item) for item in active_runtime.model_metadata],
        }

    async def classify_payload(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
        request_id = data.get("request_id") if isinstance(data.get("request_id"), str) else None
        if data.get("contract_version") != CONTRACT_VERSION:
            return (
                _error_payload(
                    "UNKNOWN_CONTRACT_VERSION",
                    f"contract_version must equal {CONTRACT_VERSION}",
                    request_id=request_id,
                ),
                400,
            )
        text = data.get("text")
        top_k = data.get("top_k", 3)
        if not isinstance(text, str) or not isinstance(top_k, int):
            return (
                _error_payload(
                    "INVALID_INPUT",
                    "text must be a string and top_k must be an integer",
                    request_id=request_id,
                ),
                422,
            )
        try:
            prediction, truncated = await asyncio.to_thread(active_runtime.classify, text, top_k)
        except RequestValidationError as exc:
            return _error_payload("INVALID_INPUT", str(exc), request_id=request_id), 422
        except RuntimeError as exc:
            return (
                _error_payload("MODEL_NOT_READY", str(exc), request_id=request_id, retryable=True),
                503,
            )
        return (
            {
                "contract_version": CONTRACT_VERSION,
                "request_id": request_id,
                "labels": [asdict(item) for item in prediction.labels],
                "abstain": prediction.abstain,
                "abstain_reason": prediction.abstain_reason,
                "model_version": prediction.model_version,
                "taxonomy_version": prediction.taxonomy_version,
                "input_truncated": truncated,
            },
            200,
        )

    @post("/v1/classify", status_code=200)
    async def classify(data: dict[str, Any]) -> Response[dict[str, Any]]:
        content, status_code = await classify_payload(data)
        return Response(content=content, status_code=status_code)

    @post("/v1/classify:batch", status_code=200)
    async def classify_batch(data: dict[str, Any]) -> Response[dict[str, Any]]:
        items = data.get("items")
        batch_id = data.get("batch_id")
        if data.get("contract_version") != CONTRACT_VERSION:
            return _error(
                "UNKNOWN_CONTRACT_VERSION",
                f"contract_version must equal {CONTRACT_VERSION}",
                status_code=400,
            )
        valid_batch = isinstance(batch_id, str) and isinstance(items, list) and 1 <= len(items) <= 1024
        if not valid_batch:
            return _error(
                "INVALID_INPUT",
                "batch_id must be a string and items must contain 1..1024 entries",
                status_code=422,
            )
        results: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                results.append(
                    {
                        "request_id": None,
                        "error": _error_payload("INVALID_INPUT", "item must be an object"),
                    }
                )
                continue
            body, status_code = await classify_payload({"contract_version": CONTRACT_VERSION, **item})
            if status_code == 200:
                results.append({"request_id": item.get("request_id"), "response": body})
            else:
                results.append({"request_id": item.get("request_id"), "error": body})
        return Response(content={"batch_id": batch_id, "items": results})

    @post("/v1/decide", status_code=200)
    async def decide(data: dict[str, Any]) -> Response[dict[str, Any]]:
        request_id = data.get("request_id") if isinstance(data.get("request_id"), str) else None
        try:
            deadline_ms = data.get("deadline_ms", 5_000)
            if not isinstance(deadline_ms, int) or deadline_ms < 1:
                raise RequestValidationError("deadline_ms must be a positive integer")
            async with asyncio.timeout(deadline_ms / 1000):
                result = await asyncio.to_thread(active_runtime.decide, data)
        except RequestValidationError as exc:
            code = "UNKNOWN_CONTRACT_VERSION" if "contract_version" in str(exc) else "INVALID_INPUT"
            status_code = 400 if code == "UNKNOWN_CONTRACT_VERSION" else 422
            return _error(code, str(exc), status_code=status_code, request_id=request_id)
        except TimeoutError:
            return _error(
                "TIMEOUT",
                "inference deadline exceeded",
                status_code=504,
                request_id=request_id,
                retryable=True,
            )
        except ValueError as exc:
            return _error("FORBIDDEN_CANDIDATE", str(exc), status_code=500, request_id=request_id)
        return Response(content=decision_response_to_dict(result))

    @post("/v1/grouping:recommend", status_code=200)
    async def recommend_grouping(data: dict[str, Any]) -> Response[dict[str, Any]]:
        request_id = data.get("request_id") if isinstance(data.get("request_id"), str) else None
        try:
            deadline_ms = data.get("deadline_ms", 5_000)
            if not isinstance(deadline_ms, int) or deadline_ms < 1:
                raise RequestValidationError("deadline_ms must be a positive integer")
            async with asyncio.timeout(deadline_ms / 1000):
                result = await asyncio.to_thread(active_runtime.recommend_semantic_grouping, data)
        except RequestValidationError as exc:
            code = "UNKNOWN_CONTRACT_VERSION" if "contract_version" in str(exc) else "INVALID_INPUT"
            status_code = 400 if code == "UNKNOWN_CONTRACT_VERSION" else 422
            return _error(code, str(exc), status_code=status_code, request_id=request_id)
        except TimeoutError:
            return _error(
                "TIMEOUT",
                "semantic grouping deadline exceeded",
                status_code=504,
                request_id=request_id,
                retryable=True,
            )
        return Response(
            content={
                "contract_version": CONTRACT_VERSION,
                "request_id": request_id,
                **asdict(result),
            }
        )

    return Litestar(
        route_handlers=[health, ready, models, classify, classify_batch, decide, recommend_grouping]
    )


def _error_payload(
    code: str,
    message: str,
    *,
    request_id: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "code": code,
        "message": message,
        "retryable": retryable,
    }
