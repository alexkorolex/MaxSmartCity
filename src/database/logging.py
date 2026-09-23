import logging
from collections.abc import Iterator
from contextlib import contextmanager

from advanced_alchemy.exceptions import RepositoryError
from opentelemetry import trace

_tracer = trace.get_tracer(__name__)


@contextmanager
def database_action(action: str, entity: str) -> Iterator[None]:
    logger = logging.getLogger(__name__)
    details = {"action": action, "entity": entity}
    logger.debug("Database operation started", extra=details)
    with _tracer.start_as_current_span(
        f"{entity}.{action}",
        attributes={"app.domain.entity": entity, "app.domain.action": action},
    ) as span:
        try:
            yield
        except RepositoryError as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            logger.exception("Database operation failed", extra=details)
            raise
        logger.info("Database operation completed: %s %s", action, entity, extra=details)
