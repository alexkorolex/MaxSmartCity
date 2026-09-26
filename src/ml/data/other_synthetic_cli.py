"""Plan, generate and materialize the deterministic ``other`` matching dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import ResponseFormat

from src.ml.data.other_synthetic import (
    DEFAULT_SEED,
    build_generation_tasks,
    load_other_references,
    materialize_dataset,
    select_houses,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--houses-source", type=Path, required=True)
    parser.add_argument("--references", type=Path, default=Path("ml/data/gold/v2/reports.jsonl"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"))
    parser.add_argument("--houses-per-city", type=int, default=10)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--model", default="mistral-small-2603")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    houses = select_houses(args.houses_source, per_city=args.houses_per_city, seed=args.seed)
    references = load_other_references(args.references)
    tasks = build_generation_tasks(houses, references, seed=args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "seed": args.seed,
        "house_count": len(houses),
        "api_call_count": len(tasks),
        "event_count": sum(len(task["events"]) for task in tasks),
        "model": args.model,
        "tasks": tasks,
    }
    _write_json(args.output_dir / "generation-plan.json", plan)
    if not args.execute:
        print(
            json.dumps(
                {key: value for key, value in plan.items() if key != "tasks"}, ensure_ascii=False, indent=2
            )
        )
        return
    load_dotenv(args.env_file, override=False)
    api_key = os.getenv("AITUNNEL_API_KEY")
    if not api_key:
        raise RuntimeError(f"AITUNNEL_API_KEY is not configured in {args.env_file}")
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1/"),
        timeout=90,
        max_retries=2,
    )
    progress_path = args.output_dir / "generations.jsonl"
    records = _load_jsonl(progress_path)
    completed = {str(item["task_id"]): item for item in records}
    for task in tasks:
        task_id = str(task["task_id"])
        if task_id in completed:
            continue
        record = _generate_with_rate_limit_retries(client, args.model, task)
        with progress_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        completed[task_id] = record
        print(f"generated {len(completed)}/{len(tasks)} {task_id}", flush=True)
        time.sleep(12)
    generations: dict[str, dict[str, dict[str, str]]] = {}
    for task_id, record in completed.items():
        event_map: dict[str, dict[str, str]] = {}
        for event in record["events"]:
            event_map[str(event["event_id"])] = {
                str(item["style_id"]): str(item["text"]) for item in event["variants"]
            }
        generations[task_id] = event_map
    manifest = materialize_dataset(tasks, generations, args.output_dir)
    input_tokens = sum(int(item["usage"]["input_tokens"]) for item in completed.values())
    output_tokens = sum(int(item["usage"]["output_tokens"]) for item in completed.values())
    manifest["generation"] = {
        "model": args.model,
        "api_call_count": len(tasks),
        "source": "AITUNNEL",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_rub": round((input_tokens * 30 + output_tokens * 120) / 1_000_000, 4),
    }
    manifest["sources"] = {
        "houses_sha256": hashlib.sha256(args.houses_source.read_bytes()).hexdigest(),
        "references_sha256": hashlib.sha256(args.references.read_bytes()).hexdigest(),
    }
    _write_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def _generate_task(client: OpenAI, model: str, task: dict[str, Any]) -> dict[str, Any]:
    schema = _response_schema(task)
    response = client.chat.completions.create(
        model=model,
        messages=cast(
            list[ChatCompletionMessageParam],
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)},
            ],
        ),
        response_format=cast(ResponseFormat, {"type": "json_schema", "json_schema": schema}),
        temperature=0.45,
        top_p=0.9,
        max_completion_tokens=1600,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI Tunnel returned an empty response")
    payload = json.loads(content)
    expected = {str(item["event_id"]) for item in task["events"]}
    received = {str(item.get("event_id")) for item in payload.get("events", [])}
    if received != expected:
        raise ValueError(f"provider changed event ids for {task['task_id']}")
    return {
        "task_id": task["task_id"],
        "response_id": response.id,
        "model": response.model,
        "created_at": datetime.now(UTC).isoformat(),
        "usage": {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        },
        "events": payload["events"],
    }


def _generate_with_rate_limit_retries(client: OpenAI, model: str, task: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(6):
        try:
            return _generate_task(client, model, task)
        except RateLimitError:
            if attempt == 5:
                raise
            delay_seconds = 20 + attempt * 10
            print(
                f"rate limited for {task['task_id']}; retrying in {delay_seconds}s",
                flush=True,
            )
            time.sleep(delay_seconds)
    raise AssertionError("unreachable")


def _response_schema(task: dict[str, Any]) -> dict[str, Any]:
    event_ids = [str(item["event_id"]) for item in task["events"]]
    return {
        "name": "other_incident_paraphrases",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["events"],
            "properties": {
                "events": {
                    "type": "array",
                    "minItems": len(event_ids),
                    "maxItems": len(event_ids),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["event_id", "variants"],
                        "properties": {
                            "event_id": {"type": "string", "enum": event_ids},
                            "variants": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["style_id", "text"],
                                    "properties": {
                                        "style_id": {"type": "string", "enum": ["neutral", "natural"]},
                                        "text": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                }
            },
        },
    }


_SYSTEM_PROMPT = """Ты создаёшь синтетические русскоязычные сообщения жителей.
Они нужны для тестирования поиска похожих инцидентов категории «Другое».

Для каждого события верни ровно два самостоятельных варианта: neutral и natural.
locked_fact — единственный источник фактов. reference_texts показывают только допустимый
стиль реальных примеров: не копируй из них адреса, числа и обстоятельства.

Правила:
1. Сохрани смысл locked_fact и не добавляй причины, сроки, организации, подъезд, этаж или последствия.
2. Не упоминай адрес: backend уже знает house_id.
3. Не называй категорию и не предлагай решение.
4. neutral — спокойная полная формулировка; natural — естественное короткое сообщение в мессенджере.
5. Не объединяй разные event_id и не меняй event_id.
6. Каждый вариант должен быть длиной 8–500 символов.
Верни только объект по JSON Schema."""


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
