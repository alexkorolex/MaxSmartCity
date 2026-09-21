from importlib import import_module

from sqlalchemy import MetaData

from src.common.models import Entity


class ModelRegistry:
    @staticmethod
    def schemas() -> tuple[str, ...]:
        return (
            "identity",
            "geo",
            "reports",
            "incidents",
            "collaboration",
            "audit",
            "infrastructure",
            "ingestion",
        )

    @classmethod
    def load(cls) -> MetaData:
        for domain in cls.schemas():
            import_module(f"src.domains.{domain}.models")
        return Entity.metadata
