from advanced_alchemy.extensions.litestar import SQLAlchemyDTO

from src.domains.audit.models import AuditLog


class AuditLogReadDTO(SQLAlchemyDTO[AuditLog]):
    """Read contract; audit has no public create, update or delete contract."""
