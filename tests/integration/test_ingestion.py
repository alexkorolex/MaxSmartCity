import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.domains.ingestion.importer import import_file


def make_dataset(
    code: str,
    city: str,
    *,
    number: str = "1",
    timestamp: str = "2026-09-22T12:00:00+03:00",
    with_link: bool = True,
) -> dict[str, Any]:
    return {
        "version": 1,
        "source": {"code": code, "data_kind": "DEMO", "retrieved_at": timestamp},
        "houses": [{"key": "house-1", "city": city, "street": "улица Первая", "house_number": number}],
        "organizations": [{"key": "org-1", "name": "Тестовая УК", "type": "MANAGING_COMPANY"}],
        "links": [{"house_key": "house-1", "organization_key": "org-1", "relationship": "MANAGES"}]
        if with_link
        else [],
    }


def save(path: Path, dataset: dict[str, Any]) -> Path:
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    return path


async def rows(database_url: str, sql: str, **params: object) -> list[Row[Any]]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return list((await connection.execute(text(sql), params)).all())
    finally:
        await engine.dispose()


async def house_row(database_url: str, code: str, key: str = "house-1") -> Row[Any]:
    result = await rows(
        database_url,
        "SELECT h.id, h.address_id, a.city, a.street, a.house_number, h.external_id, "
        "ST_Y(h.point::geometry), ST_X(h.point::geometry) "
        "FROM ingestion.house_source hs JOIN ingestion.source s ON s.id=hs.source_id "
        "JOIN geo.house h ON h.id=hs.house_id JOIN geo.address a ON a.id=h.address_id "
        "WHERE s.code=:code AND hs.source_key=:key",
        code=code,
        key=key,
    )
    assert len(result) == 1
    return result[0]


@pytest.mark.anyio
async def test_import_is_repeatable_and_preserves_house_id(database_url: str, tmp_path: Path) -> None:
    code = f"test-ingestion-{uuid4()}"
    city = f"Тестоград-{uuid4().hex}"
    path = tmp_path / "pilot.json"
    dataset = {
        "version": 1,
        "source": {"code": code, "data_kind": "DEMO", "retrieved_at": "2026-09-22T12:00:00+03:00"},
        "houses": [
            {"key": "house-1", "city": city, "street": "улица Первая", "house_number": "101"},
            {"key": "bad-house", "street": "улица Первая", "house_number": "102"},
        ],
        "organizations": [{"key": "org-1", "name": "Тестовая УК", "type": "MANAGING_COMPANY"}],
        "links": [
            {"house_key": "house-1", "organization_key": "org-1", "relationship": "MANAGES"},
            {"house_key": "bad-house", "organization_key": "org-1", "relationship": "MANAGES"},
        ],
    }
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    first = await import_file(path, database_url)
    assert first["houses_created"] == 1
    assert first["organizations_created"] == 1
    assert first["links_created"] == 1
    assert first["error_count"] == 2

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            house_id = (
                await connection.execute(
                    text(
                        "SELECT hs.house_id FROM ingestion.house_source hs "
                        "JOIN ingestion.source s ON s.id=hs.source_id WHERE s.code=:code"
                    ),
                    {"code": code},
                )
            ).scalar_one()
        second = await import_file(path, database_url)
        assert second["houses_created"] == 0
        assert second["links_created"] == 0

        dataset["source"]["retrieved_at"] = "2026-09-23T12:00:00+03:00"
        dataset["houses"][0]["house_number"] = "101А"
        path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
        third = await import_file(path, database_url)
        assert third["houses_updated"] == 1
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT hs.house_id,a.house_number FROM ingestion.house_source hs "
                        "JOIN ingestion.source s ON s.id=hs.source_id "
                        "JOIN geo.house h ON h.id=hs.house_id JOIN geo.address a ON a.id=h.address_id "
                        "WHERE s.code=:code"
                    ),
                    {"code": code},
                )
            ).one()
            assert row == (house_id, "101А")
            assert (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM ingestion.house_organization ho "
                        "JOIN ingestion.source s ON s.id=ho.source_id WHERE s.code=:code"
                    ),
                    {"code": code},
                )
            ).scalar_one() == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_concurrent_sources_reuse_exact_address_but_keep_similar_houses_distinct(
    database_url: str, tmp_path: Path
) -> None:
    city = f"Город-{uuid4().hex}"
    first_code, second_code = f"first-{uuid4()}", f"second-{uuid4()}"
    first = make_dataset(first_code, city)
    second = make_dataset(second_code, city)
    second["houses"][0]["city"] = city.upper()
    second["houses"].append({"key": "house-2", "city": city, "street": "улица Первая", "house_number": "1А"})
    first_result, second_result = await asyncio.gather(
        import_file(save(tmp_path / "first.json", first), database_url),
        import_file(save(tmp_path / "second.json", second), database_url),
    )
    assert int(first_result["houses_created"]) + int(second_result["houses_created"]) == 2
    assert first_result["error_count"] == second_result["error_count"] == 0
    mapped = await rows(
        database_url,
        "SELECT s.code, hs.source_key, hs.house_id FROM ingestion.house_source hs "
        "JOIN ingestion.source s ON s.id=hs.source_id WHERE s.code IN (:first,:second)",
        first=first_code,
        second=second_code,
    )
    ids = {(code, key): house_id for code, key, house_id in mapped}
    assert ids[(first_code, "house-1")] == ids[(second_code, "house-1")]
    assert ids[(first_code, "house-1")] != ids[(second_code, "house-2")]


@pytest.mark.anyio
async def test_report_foreign_key_survives_address_update(database_url: str, tmp_path: Path) -> None:
    code = f"report-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    path = save(tmp_path / "pilot.json", dataset)
    await import_file(path, database_url)
    before = await house_row(database_url, code)
    report_id = uuid4()
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO reports.report(id,source_type,text,house_id,created_at,updated_at) "
                    "VALUES (:id,'MAX','Обращение жителя',:house_id,now(),now())"
                ),
                {"id": report_id, "house_id": before[0]},
            )
        dataset["source"]["retrieved_at"] = "2026-09-23T12:00:00+03:00"
        dataset["houses"][0]["house_number"] = "1А"
        await import_file(save(path, dataset), database_url)
        after = await house_row(database_url, code)
        assert after[0] == before[0]
        assert after[4] == "1А"
        assert await rows(
            database_url, "SELECT house_id,text FROM reports.report WHERE id=:id", id=report_id
        ) == [(before[0], "Обращение жителя")]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_stale_records_cannot_overwrite_house_organization_or_add_link(
    database_url: str, tmp_path: Path
) -> None:
    code = f"stale-{uuid4()}"
    dataset = make_dataset(
        code, f"Город-{uuid4().hex}", timestamp="2026-09-23T12:00:00+03:00", with_link=False
    )
    path = save(tmp_path / "pilot.json", dataset)
    await import_file(path, database_url)
    dataset["source"]["retrieved_at"] = "2026-09-22T12:00:00+03:00"
    dataset["houses"][0]["house_number"] = "9"
    dataset["organizations"][0]["name"] = "Старая УК"
    dataset["links"] = [{"house_key": "house-1", "organization_key": "org-1", "relationship": "MANAGES"}]
    result = await import_file(save(path, dataset), database_url)
    assert result["error_count"] == 3
    assert (await house_row(database_url, code))[4] == "1"
    assert await rows(
        database_url,
        "SELECT o.name FROM ingestion.organization o "
        "JOIN ingestion.organization_source os ON os.organization_id=o.id "
        "JOIN ingestion.source s ON s.id=os.source_id WHERE s.code=:code",
        code=code,
    ) == [("Тестовая УК",)]
    assert await rows(
        database_url,
        "SELECT count(*) FROM ingestion.house_organization ho "
        "JOIN ingestion.source s ON s.id=ho.source_id WHERE s.code=:code",
        code=code,
    ) == [(0,)]


@pytest.mark.anyio
async def test_ambiguous_address_is_quarantined_without_a_wrong_link(
    database_url: str, tmp_path: Path
) -> None:
    city = f"Город-{uuid4().hex}"
    code = f"ambiguous-{uuid4()}"
    address_ids = [uuid4(), uuid4()]
    house_ids = [uuid4(), uuid4()]
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            for address_id, house_id in zip(address_ids, house_ids, strict=True):
                await connection.execute(
                    text(
                        "INSERT INTO geo.address"
                        "(id,formatted,city,street,house_number,created_at,updated_at) "
                        "VALUES (:id,'Дубль',:city,'улица Первая','1',now(),now())"
                    ),
                    {"id": address_id, "city": city},
                )
                await connection.execute(
                    text(
                        "INSERT INTO geo.house(id,address_id,created_at,updated_at) "
                        "VALUES (:id,:address_id,now(),now())"
                    ),
                    {"id": house_id, "address_id": address_id},
                )
        result = await import_file(save(tmp_path / "ambiguous.json", make_dataset(code, city)), database_url)
        assert result["error_count"] == 2
        assert result["houses_created"] == 0
        assert await rows(
            database_url,
            "SELECT count(*) FROM ingestion.house_source hs "
            "JOIN ingestion.source s ON s.id=hs.source_id WHERE s.code=:code",
            code=code,
        ) == [(0,)]
        assert await rows(
            database_url,
            "SELECT count(*) FROM geo.house WHERE id IN (:first,:second)",
            first=house_ids[0],
            second=house_ids[1],
        ) == [(2,)]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_absent_rows_do_not_delete_existing_links(database_url: str, tmp_path: Path) -> None:
    code = f"omission-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    path = save(tmp_path / "pilot.json", dataset)
    await import_file(path, database_url)
    dataset["source"]["retrieved_at"] = "2026-09-23T12:00:00+03:00"
    dataset["links"] = []
    result = await import_file(save(path, dataset), database_url)
    assert result["error_count"] == 0
    assert await rows(
        database_url,
        "SELECT count(*) FROM ingestion.house_organization ho "
        "JOIN ingestion.source s ON s.id=ho.source_id WHERE s.code=:code",
        code=code,
    ) == [(1,)]


@pytest.mark.anyio
async def test_changed_source_classification_is_rejected_before_any_writes(
    database_url: str, tmp_path: Path
) -> None:
    code = f"kind-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    path = save(tmp_path / "pilot.json", dataset)
    await import_file(path, database_url)
    dataset["source"]["data_kind"] = "REAL"
    with pytest.raises(ValueError, match="data_kind cannot change"):
        await import_file(save(path, dataset), database_url)
    assert await rows(
        database_url,
        "SELECT count(*) FROM ingestion.run r JOIN ingestion.source s ON s.id=r.source_id WHERE s.code=:code",
        code=code,
    ) == [(1,)]


@pytest.mark.anyio
async def test_unexpected_failure_rolls_back_entire_run(
    database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = f"rollback-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    path = save(tmp_path / "pilot.json", dataset)
    await import_file(path, database_url)
    dataset["source"]["retrieved_at"] = "2026-09-23T12:00:00+03:00"
    dataset["houses"][0]["house_number"] = "9"

    async def crash(*args: object) -> str:
        raise RuntimeError("unexpected importer failure")

    monkeypatch.setattr("src.domains.ingestion.importer._organization", crash)
    with pytest.raises(RuntimeError, match="unexpected importer failure"):
        await import_file(save(path, dataset), database_url)
    assert (await house_row(database_url, code))[4] == "1"
    assert await rows(
        database_url,
        "SELECT count(*) FROM ingestion.run r JOIN ingestion.source s ON s.id=r.source_id WHERE s.code=:code",
        code=code,
    ) == [(1,)]


@pytest.mark.anyio
async def test_updating_shared_address_does_not_change_another_house(
    database_url: str, tmp_path: Path
) -> None:
    code = f"shared-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    path = save(tmp_path / "pilot.json", dataset)
    await import_file(path, database_url)
    original = await house_row(database_url, code)
    other_house_id = uuid4()
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO geo.house(id,address_id,created_at,updated_at) "
                    "VALUES (:id,:address_id,now(),now())"
                ),
                {"id": other_house_id, "address_id": original[1]},
            )
        dataset["source"]["retrieved_at"] = "2026-09-23T12:00:00+03:00"
        dataset["houses"][0]["house_number"] = "2"
        await import_file(save(path, dataset), database_url)
        updated = await house_row(database_url, code)
        assert updated[0] == original[0]
        assert updated[1] != original[1]
        assert updated[4] == "2"
        assert await rows(
            database_url,
            "SELECT h.address_id,a.house_number FROM geo.house h "
            "JOIN geo.address a ON a.id=h.address_id WHERE h.id=:id",
            id=other_house_id,
        ) == [(original[1], "1")]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_older_second_source_cannot_replace_newer_canonical_address(
    database_url: str, tmp_path: Path
) -> None:
    city = f"Город-{uuid4().hex}"
    first_code, second_code = f"newer-{uuid4()}", f"older-{uuid4()}"
    first = make_dataset(first_code, city, timestamp="2026-09-23T12:00:00+03:00")
    first["houses"][0]["formatted"] = "Новый проверенный адрес"
    second = make_dataset(second_code, city, timestamp="2026-09-22T12:00:00+03:00")
    second["houses"][0]["formatted"] = "Старая версия адреса"
    await import_file(save(tmp_path / "newer.json", first), database_url)
    await import_file(save(tmp_path / "older.json", second), database_url)
    assert (await house_row(database_url, first_code))[0] == (await house_row(database_url, second_code))[0]
    assert await rows(
        database_url,
        "SELECT a.formatted FROM ingestion.house_source hs "
        "JOIN ingestion.source s ON s.id=hs.source_id "
        "JOIN geo.house h ON h.id=hs.house_id JOIN geo.address a ON a.id=h.address_id "
        "WHERE s.code=:code",
        code=first_code,
    ) == [("Новый проверенный адрес",)]


@pytest.mark.anyio
async def test_provenance_external_ids_and_coordinates_are_readable_by_backend(
    database_url: str, tmp_path: Path
) -> None:
    code = f"provenance-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    dataset["source"].update(
        {
            "data_kind": "REAL",
            "url": "https://example.test/catalog/house-1",
        }
    )
    dataset["houses"][0].update(
        {
            "external_id": "external-house-1",
            "latitude": 53.21,
            "longitude": 34.37,
        }
    )
    dataset["organizations"][0]["external_id"] = "external-org-1"
    result = await import_file(save(tmp_path / "pilot.json", dataset), database_url)
    assert result["error_count"] == 0
    house = await house_row(database_url, code)
    assert house[5:] == ("external-house-1", 53.21, 34.37)
    assert await rows(
        database_url,
        "SELECT s.data_kind,s.url,hs.external_id,os.external_id,ho.relationship,"
        "hs.retrieved_at=ho.retrieved_at "
        "FROM ingestion.house_organization ho "
        "JOIN ingestion.source s ON s.id=ho.source_id "
        "JOIN ingestion.house_source hs ON hs.source_id=s.id AND hs.house_id=ho.house_id "
        "JOIN ingestion.organization_source os ON os.source_id=s.id "
        "AND os.organization_id=ho.organization_id WHERE s.code=:code",
        code=code,
    ) == [
        (
            "REAL",
            "https://example.test/catalog/house-1",
            "external-house-1",
            "external-org-1",
            "MANAGES",
            True,
        )
    ]


@pytest.mark.anyio
async def test_duplicate_keys_and_unknown_links_are_quarantined_without_replacing_valid_rows(
    database_url: str, tmp_path: Path
) -> None:
    code = f"duplicates-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    dataset["houses"].append({**dataset["houses"][0], "house_number": "99"})
    dataset["organizations"].append({**dataset["organizations"][0], "name": "Другая УК"})
    dataset["links"].append(
        {"house_key": "house-1", "organization_key": "unknown", "relationship": "MANAGES"}
    )
    result = await import_file(save(tmp_path / "pilot.json", dataset), database_url)
    assert result["houses_created"] == 1
    assert result["organizations_created"] == 1
    assert result["links_created"] == 1
    assert result["error_count"] == 3
    assert (await house_row(database_url, code))[4] == "1"
    errors = await rows(
        database_url,
        "SELECT e.entity_type,e.row_number FROM ingestion.error e "
        "JOIN ingestion.run r ON r.id=e.run_id JOIN ingestion.source s ON s.id=r.source_id "
        "WHERE s.code=:code ORDER BY e.entity_type,e.row_number",
        code=code,
    )
    assert errors == [("house", 2), ("link", 2), ("organization", 2)]


@pytest.mark.anyio
async def test_changed_address_cannot_take_another_houses_address(database_url: str, tmp_path: Path) -> None:
    code = f"conflict-{uuid4()}"
    city = f"Город-{uuid4().hex}"
    dataset = make_dataset(code, city)
    dataset["houses"].append({"key": "house-2", "city": city, "street": "улица Первая", "house_number": "2"})
    path = save(tmp_path / "pilot.json", dataset)
    first = await import_file(path, database_url)
    assert first["houses_created"] == 2
    original = await house_row(database_url, code)
    dataset["source"]["retrieved_at"] = "2026-09-23T12:00:00+03:00"
    dataset["houses"][0]["house_number"] = "2"
    updated = await import_file(save(path, dataset), database_url)
    assert updated["error_count"] == 1
    assert (await house_row(database_url, code)) == original
    assert await rows(
        database_url,
        "SELECT count(DISTINCT h.id) FROM geo.house h JOIN geo.address a ON a.id=h.address_id "
        "WHERE a.city=:city AND a.house_number IN ('1','2')",
        city=city,
    ) == [(2,)]


@pytest.mark.anyio
async def test_database_rejected_row_is_logged_without_losing_good_rows(
    database_url: str, tmp_path: Path
) -> None:
    code = f"bad-character-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    dataset["houses"].insert(
        0,
        {
            "key": "bad",
            "city": dataset["houses"][0]["city"],
            "street": "улица\x00Первая",
            "house_number": "9",
        },
    )
    result = await import_file(save(tmp_path / "pilot.json", dataset), database_url)
    assert result["houses_created"] == 1
    assert result["error_count"] == 1
    assert await rows(
        database_url,
        "SELECT e.entity_type,e.row_number FROM ingestion.error e "
        "JOIN ingestion.run r ON r.id=e.run_id JOIN ingestion.source s ON s.id=r.source_id "
        "WHERE s.code=:code",
        code=code,
    ) == [("house", 1)]
    assert (await house_row(database_url, code))[4] == "1"


@pytest.mark.anyio
async def test_unrepresentable_json_number_is_quarantined_per_row(database_url: str, tmp_path: Path) -> None:
    code = f"huge-number-{uuid4()}"
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    dataset["houses"].insert(
        0,
        {
            "key": "bad",
            "city": dataset["houses"][0]["city"],
            "street": "улица Вторая",
            "house_number": "9",
            "latitude": 0.0,
            "longitude": 0.0,
        },
    )
    path = tmp_path / "pilot.json"
    path.write_text(
        json.dumps(dataset, ensure_ascii=False).replace('"latitude": 0.0', '"latitude": 1e400', 1),
        encoding="utf-8",
    )
    result = await import_file(path, database_url)
    assert result["houses_created"] == 1
    assert result["error_count"] == 1
    assert (await house_row(database_url, code))[4] == "1"


@pytest.mark.anyio
async def test_real_house_attributes_take_priority_over_demo_data(database_url: str, tmp_path: Path) -> None:
    city = f"Город-{uuid4().hex}"
    demo_code, real_code = f"demo-{uuid4()}", f"real-{uuid4()}"
    demo = make_dataset(demo_code, city, timestamp="2026-09-23T12:00:00+03:00")
    demo["houses"][0]["formatted"] = "Демо адрес"
    real = make_dataset(real_code, city, timestamp="2026-09-22T12:00:00+03:00")
    real["source"]["data_kind"] = "REAL"
    real["houses"][0]["formatted"] = "Подтверждённый адрес"
    await import_file(save(tmp_path / "demo.json", demo), database_url)
    await import_file(save(tmp_path / "real.json", real), database_url)
    assert (await house_row(database_url, demo_code))[0] == (await house_row(database_url, real_code))[0]
    assert await rows(
        database_url,
        "SELECT a.formatted FROM ingestion.house_source hs "
        "JOIN ingestion.source s ON s.id=hs.source_id "
        "JOIN geo.house h ON h.id=hs.house_id JOIN geo.address a ON a.id=h.address_id "
        "WHERE s.code=:code",
        code=real_code,
    ) == [("Подтверждённый адрес",)]
    demo["source"]["retrieved_at"] = "2026-09-24T12:00:00+03:00"
    demo["houses"][0]["formatted"] = "Новый демо адрес"
    await import_file(save(tmp_path / "demo.json", demo), database_url)
    assert await rows(
        database_url,
        "SELECT a.formatted FROM ingestion.house_source hs "
        "JOIN ingestion.source s ON s.id=hs.source_id "
        "JOIN geo.house h ON h.id=hs.house_id JOIN geo.address a ON a.id=h.address_id "
        "WHERE s.code=:code",
        code=real_code,
    ) == [("Подтверждённый адрес",)]
