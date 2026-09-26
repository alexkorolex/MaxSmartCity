from collections.abc import Sequence
from pathlib import Path

import numpy as np
from litestar.testing import TestClient

from src.ml.adapters.baselines import RuleBaselineDecisionModel, RuleIncidentRanker
from src.ml.adapters.extraction import RuleFeatureExtractor
from src.ml.application.decision_service import DecisionService
from src.ml.data.config import load_rule_baseline
from src.ml.inference.category import CategoryArtifact
from src.ml.inference.decision import ArtifactDecisionModel
from src.ml.inference.semantic_grouping import SemanticGroupingService
from src.ml.service import create_app
from src.ml.service.runtime import MLRuntime


class FixedPipeline:
    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return np.array([[0.9, 0.1] for _ in texts])


class FixedEmbeddingProvider:
    model_name = "fixed-semantic-test"

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        assert len(texts) == 1
        return np.array([[1.0, 0.0]], dtype=np.float32)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        assert len(texts) == 1
        return np.array([[0.99, 0.01]], dtype=np.float32)


def _runtime() -> MLRuntime:
    category = CategoryArtifact(
        {
            "pipeline": FixedPipeline(),
            "labels": ["water", "other"],
            "label_threshold": 0.5,
            "abstain_threshold": 0.8,
            "model_version": "test-category-v1",
            "taxonomy_version": "test-taxonomy-v1",
        }
    )
    ranker = RuleIncidentRanker(load_rule_baseline(Path("ml/configs/rule-baseline.v1.json")))
    extractor = RuleFeatureExtractor.from_path(Path("ml/configs/extraction-rules.v1.json"))
    primary = ArtifactDecisionModel(category, ranker, extractor)
    fallback = RuleBaselineDecisionModel(ranker, extractor)
    return MLRuntime(
        category=category,
        artifact_error=None,
        decision_service=DecisionService(primary, fallback),
        model_metadata=(primary.metadata,),
        max_input_characters=20,
        semantic_grouping=SemanticGroupingService(FixedEmbeddingProvider()),
    )


def test_health_readiness_models_and_classification() -> None:
    with TestClient(create_app(_runtime())) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").json() == {"ready": True, "reasons": []}
        assert client.get("/v1/models").json()["models"][0]["version"] == "test-category-v1"

        response = client.post(
            "/v1/classify",
            json={
                "contract_version": "2.0.0-draft",
                "request_id": "REQ-1",
                "text": "нет холодной воды в доме",
                "top_k": 1,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["labels"][0]["label_id"] == "water"
    assert body["input_truncated"] is True
    assert body["abstain"] is False


def test_decide_returns_category_features_and_allowlisted_incident() -> None:
    request = {
        "contract_version": "2.0.0-draft",
        "request_id": "REQ-2",
        "deadline_ms": 1000,
        "report": {
            "report_id": "REP-2",
            "text": "На улице Ленина, дом 7 уже два часа нет воды",
            "created_at": "2026-09-21T12:00:00+03:00",
            "house_id": "HOUSE-7",
        },
        "candidate_incidents": [
            {
                "id": "INC-ALLOWED",
                "started_at": "2026-09-21T11:00:00+03:00",
                "category_id": "water",
                "affected_house_ids": ["HOUSE-7"],
                "fias_guids": [],
                "title": "Нет воды",
                "status": "NEW",
                "priority": "NORMAL",
                "active": True,
            }
        ],
        "candidate_organizations": [],
        "allowed_actions": [],
    }
    with TestClient(create_app(_runtime())) as client:
        response = client.post("/v1/decide", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["category"]["label_id"] == "water"
    assert body["incident_ranking"]["candidates"][0]["id"] == "INC-ALLOWED"
    assert body["requires_manual_review"] is True
    assert body["input_truncated"] is True


def test_invalid_contract_has_stable_error_envelope() -> None:
    with TestClient(create_app(_runtime())) as client:
        response = client.post(
            "/v1/classify",
            json={"contract_version": "1", "request_id": "REQ-3", "text": "нет света"},
        )

    assert response.status_code == 400
    assert response.json()["code"] == "UNKNOWN_CONTRACT_VERSION"


def test_batch_keeps_item_level_errors() -> None:
    with TestClient(create_app(_runtime())) as client:
        response = client.post(
            "/v1/classify:batch",
            json={
                "contract_version": "2.0.0-draft",
                "batch_id": "BATCH-1",
                "items": [
                    {"request_id": "OK", "text": "нет воды", "top_k": 1},
                    {"request_id": "BAD", "text": "нет света", "top_k": 0},
                ],
            },
        )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["response"]["labels"][0]["label_id"] == "water"
    assert items[1]["error"]["code"] == "INVALID_INPUT"


def test_missing_artifact_reports_not_ready_and_decide_uses_rule_fallback(
    tmp_path: Path,
) -> None:
    runtime = MLRuntime.load(
        artifact_dir=tmp_path / "missing",
        rule_config_path=Path("ml/configs/rule-baseline.v1.json"),
        extraction_config_path=Path("ml/configs/extraction-rules.v1.json"),
    )
    request = {
        "contract_version": "2.0.0-draft",
        "request_id": "REQ-FALLBACK",
        "report": {
            "report_id": "REP-FALLBACK",
            "text": "нет воды",
            "created_at": "2026-09-21T12:00:00+03:00",
            "category_hint": "water",
        },
        "candidate_incidents": [],
        "candidate_organizations": [],
        "allowed_actions": [],
    }

    with TestClient(create_app(runtime)) as client:
        assert client.get("/ready").status_code == 503
        unavailable = client.post(
            "/v1/classify",
            json={
                "contract_version": "2.0.0-draft",
                "request_id": "REQ-CLASSIFY",
                "text": "нет воды",
            },
        )
        fallback = client.post("/v1/decide", json=request)

    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "MODEL_NOT_READY"
    assert fallback.status_code == 200
    assert fallback.json()["category"]["label_id"] == "water"
    assert fallback.json()["requires_manual_review"] is True


def test_semantic_grouping_endpoint_returns_advisory_match() -> None:
    payload = {
        "contract_version": "2.0.0-draft",
        "request_id": "REQ-GROUP-1",
        "deadline_ms": 1000,
        "report": {
            "text": "глубокая яма",
            "occurred_at": "2026-09-25T12:00:00+03:00",
        },
        "candidate_incidents": [
            {
                "id": "INC-ROAD",
                "title": "Разбитый асфальт",
                "representative_texts": ["яма у детской площадки"],
                "last_activity_at": "2026-09-25T11:30:00+03:00",
            }
        ],
    }

    with TestClient(create_app(_runtime())) as client:
        response = client.post("/v1/grouping:recommend", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "ATTACH"
    assert body["selected_incident_id"] == "INC-ROAD"
    assert body["model_name"] == "fixed-semantic-test"


def test_disabled_semantic_model_abstains_with_http_200() -> None:
    runtime = MLRuntime.load(
        artifact_dir=Path("ml/artifacts/category-tfidf-logreg-v2"),
        rule_config_path=Path("ml/configs/rule-baseline.v1.json"),
        extraction_config_path=Path("ml/configs/extraction-rules.v1.json"),
    )
    payload = {
        "contract_version": "2.0.0-draft",
        "request_id": "REQ-GROUP-OFF",
        "report": {"text": "яма во дворе", "occurred_at": "2026-09-25T12:00:00+03:00"},
        "candidate_incidents": [
            {
                "id": "INC-ROAD",
                "title": "Разбитый асфальт",
                "representative_texts": [],
                "last_activity_at": "2026-09-25T11:30:00+03:00",
            }
        ],
    }

    with TestClient(create_app(runtime)) as client:
        response = client.post("/v1/grouping:recommend", json=payload)

    assert response.status_code == 200
    assert response.json()["action"] == "ABSTAIN"
    assert response.json()["reason_codes"] == ["SEMANTIC_MODEL_DISABLED"]


def test_semantic_grouping_rejects_text_above_runtime_limit() -> None:
    payload = {
        "contract_version": "2.0.0-draft",
        "request_id": "REQ-GROUP-LONG",
        "report": {
            "text": "x" * 21,
            "occurred_at": "2026-09-25T12:00:00+03:00",
        },
        "candidate_incidents": [],
    }

    with TestClient(create_app(_runtime())) as client:
        response = client.post("/v1/grouping:recommend", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"
