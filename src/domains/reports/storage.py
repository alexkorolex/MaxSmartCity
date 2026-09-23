"""S3-compatible object storage (MinIO) for report attachments.

Two distinct endpoints are involved, on purpose:

- ``internal_endpoint_url`` is the in-network address the backend itself uses to actually
  upload bytes (``put_object``) - reachable only from inside the Docker network.
- ``public_endpoint_url`` is the address a browser can reach, used *only* when signing
  presigned GET URLs - the signature is computed against the host the request will
  actually be sent to, so signing against the internal endpoint would produce a URL a
  browser can never resolve.

Both clients force path-style addressing (``http://host/bucket/key``) since MinIO sits
behind a path-based reverse proxy rather than resolving virtual-hosted-style
(``http://bucket.host/key``) requests.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import aioboto3
from botocore.config import Config

S3_REGION = "us-east-1"
"""MinIO does not enforce a region; boto3 just requires some value to be set."""

PRESIGNED_URL_EXPIRY_SECONDS = 3600

_ADDRESSING_STYLE_CONFIG = Config(s3={"addressing_style": "path"})


@dataclass(frozen=True, slots=True)
class S3Settings:
    bucket: str
    internal_endpoint_url: str
    public_endpoint_url: str
    access_key: str
    secret_key: str

    @classmethod
    def from_environment(cls) -> "S3Settings":
        bucket = os.environ.get("S3_BUCKET")
        if not bucket:
            raise ValueError("S3_BUCKET is required; see .env.example")
        internal_endpoint_url = os.environ.get("S3_INTERNAL_ENDPOINT_URL")
        if not internal_endpoint_url:
            raise ValueError("S3_INTERNAL_ENDPOINT_URL is required; see .env.example")
        public_endpoint_url = os.environ.get("S3_PUBLIC_ENDPOINT_URL")
        if not public_endpoint_url:
            raise ValueError("S3_PUBLIC_ENDPOINT_URL is required; see .env.example")
        access_key = os.environ.get("MINIO_ROOT_USER")
        if not access_key:
            raise ValueError("MINIO_ROOT_USER is required; see .env.example")
        secret_key = os.environ.get("MINIO_ROOT_PASSWORD")
        if not secret_key:
            raise ValueError("MINIO_ROOT_PASSWORD is required; see .env.example")
        return cls(
            bucket=bucket,
            internal_endpoint_url=internal_endpoint_url,
            public_endpoint_url=public_endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
        )

    def _session(self) -> aioboto3.Session:
        return aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=S3_REGION,
        )

    @asynccontextmanager
    async def internal_client(self) -> AsyncIterator[Any]:
        """Client used to actually upload bytes from the backend process."""
        session = self._session()
        async with session.client(
            "s3", endpoint_url=self.internal_endpoint_url, config=_ADDRESSING_STYLE_CONFIG
        ) as client:
            yield client

    async def presign_get_url(self, key: str, *, expires_in: int = PRESIGNED_URL_EXPIRY_SECONDS) -> str:
        """Generate a presigned GET URL signed against the public endpoint, so the
        signature matches the host a browser will actually hit."""
        session = self._session()
        async with session.client(
            "s3", endpoint_url=self.public_endpoint_url, config=_ADDRESSING_STYLE_CONFIG
        ) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
