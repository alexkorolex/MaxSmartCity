from pathlib import Path

import httpx

from maxsmartcity.ml.evaluation.benchmark import (
    evaluate_rule_matching,
    run_http_stress_benchmark,
)


def test_rule_matching_benchmark_uses_existing_versioned_fixture() -> None:
    result = evaluate_rule_matching(Path("ml/data/matching/dev-v1"), Path("ml/configs/rule-baseline.v1.json"))

    assert result["dataset_version"] == "matching-dataset-v1"
    assert result["splits"]["all"]["query_count"] == 1100
    assert result["splits"]["all"]["candidate_pair_count"] == 3000
    assert result["splits"]["all"]["abstain_ratio"] == 1.0


def test_http_stress_benchmark_counts_predictions_without_writing_dataset() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={
                "batch_id": payload["batch_id"],
                "items": [
                    {
                        "request_id": item["request_id"],
                        "response": {
                            "labels": [{"label_id": "water", "score": 0.9}],
                            "abstain": False,
                            "model_version": "test-v1",
                        },
                    }
                    for item in payload["items"]
                ],
            },
        )

    with httpx.Client(base_url="http://ml.test", transport=httpx.MockTransport(handler)) as client:
        result = run_http_stress_benchmark(
            base_url="http://ml.test",
            synthetic_config_path=Path("ml/configs/synthetic.v2.json"),
            report_count=7,
            batch_size=3,
            seed=42,
            timeout_seconds=1,
            client=client,
        )

    assert result["report_count"] == 7
    assert result["batch_count"] == 3
    assert result["error_count"] == 0
    assert result["top1_accuracy"] == 1.0
    assert result["abstain_ratio"] == 0.0
    assert result["accepted_count"] == 7
    assert result["accepted_top1_accuracy"] == 1.0
    assert result["generated_in_memory"] is True
