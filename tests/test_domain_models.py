from typing import cast

from sqlalchemy import DateTime, Table
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from src.database.registry import ModelRegistry
from src.domains.collaboration.models import Assignment, IncidentComment, WorkItem
from src.domains.incidents.models import Incident, IncidentReportLink


def test_models_have_domain_schemas_and_resolvable_foreign_keys() -> None:
    metadata = ModelRegistry.load()

    assert len(metadata.tables) == 51
    assert {table.schema for table in metadata.tables.values()} == set(ModelRegistry.schemas())
    for table in metadata.sorted_tables:
        assert isinstance(table, Table)
        assert str(CreateTable(table).compile(dialect=dialect()))
        for foreign_key in table.foreign_keys:
            assert foreign_key.column.table.schema in ModelRegistry.schemas()
            assert foreign_key.ondelete != "CASCADE"


def test_all_persisted_timestamps_are_timezone_aware() -> None:
    for table in ModelRegistry.load().tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone, f"{table.fullname}.{column.name}"


def test_versioned_aggregates_use_optimistic_locking() -> None:
    for model in (Incident, Assignment, WorkItem):
        assert model.__mapper__.version_id_col is model.__table__.c.version


def test_only_active_report_links_are_unique() -> None:
    table = cast(Table, IncidentReportLink.__table__)
    index = next(index for index in table.indexes if index.name == "uq_incident_report_active")

    assert index.unique
    assert [column.name for column in index.columns] == ["report_id"]
    assert "WHERE is_active = true" in str(CreateIndex(index).compile(dialect=dialect()))


def test_only_active_assignments_are_unique_per_role() -> None:
    table = cast(Table, Assignment.__table__)
    index = next(index for index in table.indexes if index.name == "uq_assignment_active_role")

    assert index.unique
    assert [column.name for column in index.columns] == [
        "incident_id",
        "organization_id",
        "role",
    ]
    compiled = str(CreateIndex(index).compile(dialect=dialect()))
    assert "WHERE status IN ('PROPOSED','ACCEPTED','IN_PROGRESS','BLOCKED','MONITORING')" in compiled


def test_internal_comment_visibility_is_database_default() -> None:
    default = IncidentComment.__table__.c.visibility.server_default

    assert default is not None
    assert str(default.arg) == "INTERNAL"
