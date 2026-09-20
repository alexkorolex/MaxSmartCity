import json
from datetime import UTC, datetime
from pathlib import Path

from maxsmartcity.ml.application.input_policy import InputPolicy
from maxsmartcity.ml.domain.api import BatchDecisionRequest, ErrorCode, ErrorResponse
from maxsmartcity.ml.domain.events import FeedbackType
from maxsmartcity.ml.domain.requests import DecisionRequest, ReportInput


def test_input_policy_truncates_deterministically() -> None:
    request = DecisionRequest(
        request_id="REQ-1",
        report=ReportInput("REP-1", "abcdefgh", datetime(2026, 9, 20, tzinfo=UTC)),
    )

    truncated, changed = InputPolicy(max_characters=5).apply(request)

    assert changed is True
    assert truncated.report.text == "abcde"
    assert request.report.text == "abcdefgh"


def test_batch_and_error_contracts_allow_per_item_failure() -> None:
    request = DecisionRequest(
        request_id="REQ-1",
        report=ReportInput("REP-1", "текст", datetime(2026, 9, 20, tzinfo=UTC)),
    )
    batch = BatchDecisionRequest("BATCH-1", (request,), deadline_ms=5_000)
    error = ErrorResponse("REQ-1", ErrorCode.MODEL_UNAVAILABLE, "offline", retryable=True)

    assert batch.items[0].request_id == error.request_id
    assert FeedbackType.OVERRIDDEN.value == "OVERRIDDEN"


def test_all_wire_contract_files_are_valid_json() -> None:
    paths = tuple(Path("ml/contracts").rglob("*.json"))

    documents = [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    assert len(documents) >= 8
    assert all(document.get("$schema") for document in documents)


def test_local_schema_references_resolve_to_existing_files() -> None:
    for path in Path("ml/contracts").rglob("*.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        for reference in _collect_references(document):
            if reference.startswith("#") or "://" in reference:
                continue
            target = reference.split("#", maxsplit=1)[0]
            assert (path.parent / target).is_file(), f"Broken $ref in {path}: {reference}"


def _collect_references(value: object) -> list[str]:
    if isinstance(value, dict):
        references = [value["$ref"]] if isinstance(value.get("$ref"), str) else []
        return references + [
            reference for nested in value.values() for reference in _collect_references(nested)
        ]
    if isinstance(value, list):
        return [reference for nested in value for reference in _collect_references(nested)]
    return []
