import logging
from collections.abc import Iterator
from contextlib import contextmanager

from advanced_alchemy.exceptions import RepositoryError


@contextmanager
def database_action(action: str, entity: str) -> Iterator[None]:
    logger = logging.getLogger(__name__)
    details = {"action": action, "entity": entity}
    logger.debug("Database operation started", extra=details)
    try:
        yield
    except RepositoryError:
        logger.exception("Database operation failed", extra=details)
        raise
    logger.info("Database operation completed: %s %s", action, entity, extra=details)
