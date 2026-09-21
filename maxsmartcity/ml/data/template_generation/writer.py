"""Writers for template preview artifacts."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from maxsmartcity.ml.data.template_generation.models import LocationScope, TemplateExample


def write_template_preview(
    examples: tuple[TemplateExample, ...],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl = "".join(
        json.dumps(asdict(example), ensure_ascii=False, sort_keys=True) + "\n" for example in examples
    )
    jsonl_path = output_dir / "examples.jsonl"
    jsonl_path.write_text(jsonl, encoding="utf-8", newline="\n")
    markdown = _markdown(examples)
    markdown_path = output_dir / "PREVIEW.md"
    markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    manifest = {
        "status": "LOCAL_TEMPLATE_PREVIEW_REQUIRES_REVIEW",
        "example_count": len(examples),
        "frame_count": len({example.frame_id for example in examples}),
        "files": {
            "examples.jsonl": hashlib.sha256(jsonl.encode()).hexdigest(),
            "PREVIEW.md": hashlib.sha256(markdown.encode()).hexdigest(),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def load_template_examples(path: Path) -> tuple[TemplateExample, ...]:
    examples: list[TemplateExample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            msg = f"template examples contain a non-object record: {path}"
            raise ValueError(msg)
        scope = payload.get("location_scope")
        if scope not in ("BUILDING", "OUTDOOR", "NONE"):
            msg = f"invalid location_scope in template examples: {scope}"
            raise ValueError(msg)
        examples.append(
            TemplateExample(
                example_id=_required_string(payload, "example_id"),
                config_version=_required_string(payload, "config_version"),
                frame_id=_required_string(payload, "frame_id"),
                category_ids=_string_tuple(payload, "category_ids"),
                subcategory_id=_required_string(payload, "subcategory_id"),
                context_tags=_string_tuple(payload, "context_tags"),
                danger_signals=_string_tuple(payload, "danger_signals"),
                location_scope=cast(LocationScope, scope),
                address_required=_required_bool(payload, "address_required"),
                street=_string(payload, "street"),
                house_number=_string(payload, "house_number"),
                template_id=_required_string(payload, "template_id"),
                base_problem=_required_string(payload, "base_problem"),
                text=_required_string(payload, "text"),
            )
        )
    return tuple(examples)


def _markdown(examples: tuple[TemplateExample, ...]) -> str:
    lines = [
        "# Template-first preview",
        "",
        "No API calls were used. Review wording and mark issues before LLM paraphrasing.",
        "",
    ]
    for index, example in enumerate(examples, start=1):
        lines.extend(
            (
                f"## {index}. {example.frame_id}",
                "",
                f"- Text: {example.text}",
                f"- Base fact: {example.base_problem}",
                f"- Address: {example.street}, {example.house_number}",
                "",
            )
        )
    return "\n".join(lines)


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string"
        raise ValueError(msg)
    return value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = _string(payload, key)
    if not value:
        msg = f"{key} must be a non-empty string"
        raise ValueError(msg)
    return value


def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean"
        raise ValueError(msg)
    return value
