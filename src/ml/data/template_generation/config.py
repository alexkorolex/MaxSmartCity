"""Configuration loader for grounded template examples."""

from pathlib import Path
from typing import Any

from src.ml.data.config import load_json_object, required_string
from src.ml.data.template_generation.models import (
    IssueFrame,
    LocationScope,
    TemplateGenerationConfig,
    TextTemplate,
)


def load_template_generation_config(path: Path) -> TemplateGenerationConfig:
    payload = load_json_object(path)
    raw_frames = payload.get("frames")
    if not isinstance(raw_frames, list) or not raw_frames:
        msg = "template generation frames must be a non-empty list"
        raise ValueError(msg)
    frames = tuple(_parse_frame(item) for item in raw_frames)
    frame_ids = [frame.id for frame in frames]
    if len(frame_ids) != len(set(frame_ids)):
        msg = "template generation frame ids must be unique"
        raise ValueError(msg)
    raw_templates = payload.get("templates")
    if not isinstance(raw_templates, list) or not raw_templates:
        msg = "templates must be a non-empty object list"
        raise ValueError(msg)
    templates = tuple(_parse_template(item) for item in raw_templates)
    template_ids = [template.id for template in templates]
    if len(template_ids) != len(set(template_ids)):
        msg = "template ids must be unique"
        raise ValueError(msg)
    unknown_template_ids = {
        template_id
        for frame in frames
        for template_id in frame.allowed_template_ids
        if template_id not in template_ids
    }
    if unknown_template_ids:
        msg = f"frames reference unknown templates: {sorted(unknown_template_ids)}"
        raise ValueError(msg)
    return TemplateGenerationConfig(
        version=required_string(payload, "version"),
        seed=_positive_int(payload, "seed"),
        variants_per_frame=_positive_int(payload, "variants_per_frame"),
        templates=templates,
        frames=frames,
    )


def _parse_frame(raw: object) -> IssueFrame:
    if not isinstance(raw, dict):
        msg = "every template generation frame must be an object"
        raise ValueError(msg)
    return IssueFrame(
        id=required_string(raw, "id"),
        category_ids=_string_tuple(raw, "category_ids"),
        subcategory_id=required_string(raw, "subcategory_id"),
        problem_variants=_string_tuple(raw, "problem_variants"),
        context_tags=_optional_string_tuple(raw, "context_tags"),
        danger_signals=_optional_string_tuple(raw, "danger_signals"),
        location_scope=_location_scope(raw),
        allowed_template_ids=_string_tuple(raw, "allowed_template_ids"),
    )


def _parse_template(raw: object) -> TextTemplate:
    if not isinstance(raw, dict):
        msg = "every template must be an object"
        raise ValueError(msg)
    return TextTemplate(
        id=required_string(raw, "id"),
        text=required_string(raw, "text"),
    )


def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        msg = f"{key} must be a non-empty string list"
        raise ValueError(msg)
    return tuple(value)


def _optional_string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive integer"
        raise ValueError(msg)
    return value


def _location_scope(payload: dict[str, Any]) -> LocationScope:
    value = payload.get("location_scope")
    if value not in ("BUILDING", "OUTDOOR", "NONE"):
        msg = "location_scope must be BUILDING, OUTDOOR or NONE"
        raise ValueError(msg)
    return value
