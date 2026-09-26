from uuid import UUID, uuid4

from src.domains.ml.report_grouping import _ranked_scores


def test_semantic_recommendations_are_bounded_filtered_and_sorted() -> None:
    allowed = [uuid4() for _ in range(5)]
    foreign = uuid4()
    body = {
        "candidates": [
            {"incident_id": str(allowed[0]), "score": 0.89},
            {"incident_id": str(allowed[1]), "score": 0.97},
            {"incident_id": str(foreign), "score": 0.99},
            {"incident_id": str(allowed[2]), "score": 0.87},
            {"incident_id": str(allowed[3]), "score": 0.91},
            {"incident_id": str(allowed[4]), "score": 0.90},
            {"incident_id": str(allowed[1]), "score": 0.96},
        ]
    }

    result = _ranked_scores(body, allowed_ids=set(allowed))

    assert result == [
        (allowed[1], 0.97),
        (allowed[3], 0.91),
        (allowed[4], 0.90),
    ]


def test_semantic_recommendations_fail_closed_on_invalid_payload() -> None:
    allowed = uuid4()
    body = {
        "candidates": [
            {"incident_id": "not-a-uuid", "score": 0.99},
            {"incident_id": str(allowed), "score": "not-a-score"},
            None,
        ]
    }

    assert _ranked_scores(body, allowed_ids={allowed}) == []
    assert _ranked_scores({"candidates": {}}, allowed_ids={UUID(int=0)}) == []
