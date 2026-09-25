from typing import Any

import pytest

from src.domains.geo.services import organization_name_key
from src.domains.ingestion.bulk import only_linked, split_dataset, validate_rows


def dataset(houses: int, organizations: int, links: int) -> dict[str, Any]:
    return {
        "version": 1,
        "source": {"code": "test", "data_kind": "DEMO", "retrieved_at": "2026-09-20T00:00:00+03:00"},
        "houses": [
            {"key": f"h{index}", "city": "Брянск", "street": "улица Мира", "house_number": str(index)}
            for index in range(houses)
        ],
        "organizations": [
            {"key": f"o{index}", "name": f"УК {index}", "type": "MANAGING_COMPANY"}
            for index in range(organizations)
        ],
        "links": [
            {"house_key": f"h{index}", "organization_key": "o0", "relationship": "MANAGES"}
            for index in range(links)
        ],
    }


def test_batches_go_organizations_then_houses_then_links() -> None:
    batches = list(split_dataset(dataset(houses=5, organizations=2, links=3), batch_size=2))
    assert [label for label, _batch in batches] == [
        "organizations 1-2/2",
        "houses 1-2/5",
        "houses 3-4/5",
        "houses 5-5/5",
        "links 1-2/3",
        "links 3-3/3",
    ]
    for label, batch in batches:
        kind = label.split(" ", 1)[0]
        assert batch["source"]["code"] == "test"
        assert all(batch[other] == [] for other in ("houses", "organizations", "links") if other != kind)
    assert sum(len(batch["houses"]) for _label, batch in batches) == 5


def test_batch_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        list(split_dataset(dataset(1, 1, 1), batch_size=0))


def test_only_linked_keeps_houses_with_a_managing_organization() -> None:
    filtered = only_linked(dataset(houses=5, organizations=1, links=2))
    assert [house["key"] for house in filtered["houses"]] == ["h0", "h1"]
    assert len(filtered["links"]) == 2


def test_dry_run_validation_reports_invalid_rows_and_keys_duplicated_across_batches() -> None:
    data = dataset(houses=3, organizations=1, links=1)
    data["houses"].append(dict(data["houses"][0]))
    data["houses"].append({"key": "broken", "city": "Брянск"})
    report = validate_rows(data)
    assert report["houses"]["duplicate_keys"] == 1
    assert report["houses"]["invalid"] == 1
    assert report["organizations"] == {"invalid": 0, "duplicate_keys": 0, "reasons": {}}


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("ООО ДОМ-ПЛЮС", 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ДОМ-ПЛЮС"'),
        (
            "ООО УК Домовладение",
            'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "УПРАВЛЯЮЩАЯ КОМПАНИЯ "ДОМОВЛАДЕНИЕ"',
        ),
        ("ТСЖ «Тухачевский»", 'ТОВАРИЩЕСТВО СОБСТВЕННИКОВ ЖИЛЬЯ "ТУХАЧЕВСКИЙ"'),
    ],
)
def test_organization_names_from_different_sources_match(first: str, second: str) -> None:
    assert organization_name_key(first) == organization_name_key(second)


def test_different_organizations_do_not_match() -> None:
    assert organization_name_key('ООО "ЖЭУ-12"') != organization_name_key('ООО "ЖЭУ-13"')
    assert organization_name_key("ООО УК") == "ООО УК"
