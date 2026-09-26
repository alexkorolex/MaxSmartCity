"""OpenAI-compatible AI Tunnel adapter used only by the offline generator."""

import json
from collections.abc import Sequence
from typing import Any, Protocol, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import ResponseFormat

from src.ml.data.llm.models import (
    GeneratedVariant,
    GenerationResponse,
    GenerationUsage,
)


class LexicalizationClient(Protocol):
    def generate(
        self,
        *,
        model: str,
        messages: Sequence[dict[str, str]],
        response_schema: dict[str, Any],
        temperature: float,
        top_p: float,
        max_output_tokens: int,
    ) -> GenerationResponse: ...


class AitunnelLexicalizationClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def generate(
        self,
        *,
        model: str,
        messages: Sequence[dict[str, str]],
        response_schema: dict[str, Any],
        temperature: float,
        top_p: float,
        max_output_tokens: int,
    ) -> GenerationResponse:
        response = self._client.chat.completions.create(
            model=model,
            messages=cast(Sequence[ChatCompletionMessageParam], messages),
            response_format=cast(
                ResponseFormat,
                {"type": "json_schema", "json_schema": response_schema},
            ),
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=max_output_tokens,
        )
        content = response.choices[0].message.content
        if not content:
            msg = "AI Tunnel returned an empty response"
            raise ValueError(msg)
        payload = json.loads(content)
        variants = tuple(
            GeneratedVariant(
                text=_required_string(item, "text"),
                style_id=_required_string(item, "style_id"),
                address_included=_required_bool(item, "address_included"),
            )
            for item in _required_list(payload, "variants")
        )
        usage = response.usage
        return GenerationResponse(
            response_id=response.id,
            model=response.model,
            scenario_spec_id=_required_string(payload, "scenario_spec_id"),
            variants=variants,
            usage=GenerationUsage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
        )


def _required_list(payload: object, key: str) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        msg = "AI Tunnel structured response must be an object"
        raise ValueError(msg)
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        msg = f"AI Tunnel structured response {key} must be an object list"
        raise ValueError(msg)
    return value


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"AI Tunnel structured response {key} must be a non-empty string"
        raise ValueError(msg)
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        msg = f"AI Tunnel structured response {key} must be a boolean"
        raise ValueError(msg)
    return value
