"""Coverage for resident-uploaded report photo attachments (MinIO-backed).

Requires a real MinIO reachable via the ``S3_*``/``MINIO_*`` env vars (bring it up with
``docker compose up -d minio minio-init``) in addition to ``TEST_DATABASE_URL`` - see
``tests/integration/conftest.py`` and ``tests/integration/test_resident_api.py`` for the
shared fixtures/helpers reused here.
"""

import os

import httpx
import pytest
from litestar.testing import TestClient

from tests.integration.test_resident_api import (  # noqa: F401
    _insert_report,
    _resident_token,
    rsa_keypair,
    security_env,
)

JPEG_BYTES = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")


@pytest.fixture(autouse=True)
def s3_env(monkeypatch: pytest.MonkeyPatch) -> None:
    if not os.environ.get("MINIO_ROOT_PASSWORD"):
        pytest.skip("Set MINIO_ROOT_PASSWORD and run `docker compose up -d minio minio-init`")
    # Tests run on the host, not inside the Docker network - override the container-network
    # endpoint (".env"'s ``S3_INTERNAL_ENDPOINT_URL=http://minio:9000``, unreachable here)
    # with the host-published port. ``S3_BUCKET``/``MINIO_ROOT_USER``/``MINIO_ROOT_PASSWORD``
    # come from ".env" as-is, matching the real bucket ``minio-init`` created.
    host_endpoint = f"http://localhost:{os.environ.get('MINIO_PORT', '9000')}"
    monkeypatch.setenv("S3_INTERNAL_ENDPOINT_URL", host_endpoint)
    monkeypatch.setenv("S3_PUBLIC_ENDPOINT_URL", host_endpoint)


def test_upload_valid_jpeg_returns_fetchable_download_url(api_client: TestClient, database_url: str) -> None:
    resident_id, token = _resident_token(api_client)
    report_id = _insert_report(database_url, resident_id=resident_id)

    uploaded = api_client.post(
        f"/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert uploaded.status_code == 201, uploaded.text
    body = uploaded.json()
    assert body["original_name"] == "photo.jpg"
    assert body["mime_type"] == "image/jpeg"
    assert body["size_bytes"] == len(JPEG_BYTES)
    assert body["download_url"]

    fetched = httpx.get(body["download_url"])
    assert fetched.status_code == 200
    assert fetched.content == JPEG_BYTES


def test_upload_to_another_residents_report_is_rejected(api_client: TestClient, database_url: str) -> None:
    owner_id, _owner_token = _resident_token(api_client, display_name="Owner")
    _other_id, other_token = _resident_token(api_client, display_name="Other")
    report_id = _insert_report(database_url, resident_id=owner_id)

    response = api_client.post(
        f"/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {other_token}"},
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert response.status_code == 403


def test_upload_disallowed_content_type_is_rejected(api_client: TestClient, database_url: str) -> None:
    resident_id, token = _resident_token(api_client)
    report_id = _insert_report(database_url, resident_id=resident_id)

    response = api_client.post(
        f"/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", b"just text", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_oversized_file_is_rejected(api_client: TestClient, database_url: str) -> None:
    resident_id, token = _resident_token(api_client)
    report_id = _insert_report(database_url, resident_id=resident_id)

    oversized = b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 + 1)
    response = api_client.post(
        f"/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("big.jpg", oversized, "image/jpeg")},
    )
    assert response.status_code == 413


def test_list_attachments_is_scoped_to_the_owning_resident(api_client: TestClient, database_url: str) -> None:
    owner_id, owner_token = _resident_token(api_client, display_name="Owner")
    _other_id, other_token = _resident_token(api_client, display_name="Other")
    report_id = _insert_report(database_url, resident_id=owner_id)

    first = api_client.post(
        f"/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert first.status_code == 201, first.text
    second = api_client.post(
        f"/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("b.png", JPEG_BYTES, "image/png")},
    )
    assert second.status_code == 201, second.text

    listed = api_client.get(
        f"/reports/{report_id}/attachments", headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert listed.status_code == 200
    names = [item["original_name"] for item in listed.json()]
    assert names == ["a.jpg", "b.png"]

    forbidden = api_client.get(
        f"/reports/{report_id}/attachments", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert forbidden.status_code == 403


def test_upload_to_missing_report_is_not_found(api_client: TestClient) -> None:
    _resident_id, token = _resident_token(api_client)
    missing_report_id = "00000000-0000-0000-0000-000000000000"

    response = api_client.post(
        f"/reports/{missing_report_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert response.status_code == 404
