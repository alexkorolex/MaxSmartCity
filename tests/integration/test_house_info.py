"""``GET /geo/houses/{id}/info`` - what a resident sees about the house they picked:
its management company with contacts from open sources, and whether that company is
connected to Smart City."""

import asyncio
from pathlib import Path
from uuid import uuid4

from litestar.testing import TestClient

from src.domains.ingestion.importer import import_file
from tests.integration.test_housing_organizations import random_inn, random_ogrn
from tests.integration.test_ingestion import make_dataset, rows, save
from tests.integration.test_resident_api import run_sql


def test_house_info_shows_managing_company_contacts_and_platform_connection(
    api_client: TestClient, database_url: str, tmp_path: Path
) -> None:
    code = f"house-info-{uuid4()}"
    inn = random_inn()
    dataset = make_dataset(code, f"Город-{uuid4().hex}")
    dataset["organizations"][0].update(
        {
            "inn": inn,
            "ogrn": random_ogrn(),
            "phones": ["+7 (962) 140-30-18"],
            "email": "Dispatch@UK.example",
            "website": "https://uk.example",
            "provenance": {"contact_source": "https://www.cian.ru/dom/example/"},
        }
    )
    asyncio.run(import_file(save(tmp_path / "house-info.json", dataset), database_url))
    (house,) = asyncio.run(
        rows(
            database_url,
            "SELECT hs.house_id FROM ingestion.house_source hs "
            "JOIN ingestion.source s ON s.id = hs.source_id WHERE s.code = :code",
            code=code,
        )
    )
    house_id = str(house.house_id)

    info = api_client.get(f"/geo/houses/{house_id}/info")
    assert info.status_code == 200, info.text
    body = info.json()
    assert body["house"]["house_id"] == house_id
    assert body["platform_manager"] is None
    (company,) = body["managing_organizations"]
    assert company["name"] == "Тестовая УК"
    assert company["inn"] == inn
    assert company["phones"] == ["+79621403018"]
    assert company["email"] == "dispatch@uk.example"
    assert company["website"] == "https://uk.example"
    assert company["is_platform_manager"] is False
    assert company["sources"][0]["url"] == "https://www.cian.ru/dom/example/"
    assert company["sources"][0]["data_kind"] == "DEMO"

    # The same company (by INN) joins Smart City and takes the house.
    organization_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO identity.organization"
        "(id, code, name, type, inn, license_number, created_at, updated_at) "
        "VALUES (:id, :code, 'УК на платформе', 'MANAGEMENT_COMPANY', :inn, '077-1', now(), now())",
        id=organization_id,
        code=uuid4().hex,
        inn=inn,
    )
    run_sql(
        database_url,
        "INSERT INTO geo.house_management(id, house_id, organization_id, basis, created_at, updated_at) "
        "VALUES (:id, :house_id, :organization_id, 'Договор', now(), now())",
        id=str(uuid4()),
        house_id=house_id,
        organization_id=organization_id,
    )
    connected = api_client.get(f"/geo/houses/{house_id}/info").json()
    assert connected["platform_manager"]["organization_id"] == organization_id
    assert connected["managing_organizations"][0]["is_platform_manager"] is True

    assert api_client.get(f"/geo/houses/{uuid4()}/info").status_code == 404
