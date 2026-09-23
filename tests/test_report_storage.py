from urllib.parse import urlparse

import pytest

from src.domains.reports.storage import S3Settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> S3Settings:
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_INTERNAL_ENDPOINT_URL", "http://minio:9000")
    monkeypatch.setenv("S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    monkeypatch.setenv("MINIO_ROOT_USER", "test-access-key")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test-secret-key")
    return S3Settings.from_environment()


def test_settings_load_from_environment(settings: S3Settings) -> None:
    assert settings.bucket == "test-bucket"
    assert settings.internal_endpoint_url == "http://minio:9000"
    assert settings.public_endpoint_url == "http://localhost:9000"
    assert settings.access_key == "test-access-key"
    assert settings.secret_key == "test-secret-key"


def test_settings_from_environment_requires_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S3_BUCKET", raising=False)
    with pytest.raises(ValueError, match="S3_BUCKET"):
        S3Settings.from_environment()


async def test_presigned_url_is_signed_against_the_public_not_internal_endpoint(
    settings: S3Settings,
) -> None:
    """The internal (container-network-only) endpoint is where the backend uploads bytes;
    a presigned URL must instead resolve on the *public* host, or a browser can never
    reach it - even though the internal endpoint is what our own process would use."""
    url = await settings.presign_get_url("reports/some-report/some-key.jpg")

    parsed = urlparse(url)
    public_parsed = urlparse(settings.public_endpoint_url)
    internal_parsed = urlparse(settings.internal_endpoint_url)

    assert parsed.netloc == public_parsed.netloc
    assert parsed.netloc != internal_parsed.netloc
    # Path-style addressing: bucket is a path segment, not a subdomain.
    assert parsed.path == "/test-bucket/reports/some-report/some-key.jpg"
    assert "Signature" in parsed.query or "X-Amz-Signature" in parsed.query
