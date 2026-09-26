import json
from pathlib import Path

from src.ml.data.other_synthetic import (
    build_generation_tasks,
    materialize_dataset,
    select_houses,
)


def test_house_selection_and_labels_are_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "houses.json"
    source.write_text(
        json.dumps(
            {
                "houses": [
                    {
                        "key": f"{city}-{index}",
                        "city": city,
                        "street": "Тестовая улица",
                        "house_number": str(index),
                        "formatted": f"{city}, дом {index}",
                    }
                    for city in ("Брянск", "Бахчисарай")
                    for index in range(4)
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    first = select_houses(source, per_city=2, seed=42)
    second = select_houses(source, per_city=2, seed=42)
    assert first == second
    tasks = build_generation_tasks(first, {})
    generated = {
        task["task_id"]: {
            event["event_id"]: {
                "neutral": f"Нейтральное сообщение о событии {event['issue_code']}",
                "natural": f"Обычное сообщение про событие {event['issue_code']}",
            }
            for event in task["events"]
        }
        for task in tasks
    }
    manifest = materialize_dataset(tasks, generated, tmp_path / "dataset")
    assert manifest["house_count"] == 4
    assert manifest["incident_count"] == 12
    assert manifest["report_count"] == 48
    assert manifest["candidate_set_count"] == 32
    assert manifest["match_query_count"] == 24
    assert manifest["create_new_query_count"] == 8
