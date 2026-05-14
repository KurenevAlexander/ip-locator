"""Application logging configuration.

The log level is controlled by the ``LOG_LEVEL`` environment variable
(default: ``INFO``).

Usage::

    from app.core.log import get_logger

    logger = get_logger(__name__)
    logger.info("Provider selected", extra={"provider": "ip_api"})
"""

import logging
import os
import sys


def setup_logging() -> None:
    """Configure application logging.

    Sets a consistent format on the root logger and suppresses noisy
    third-party loggers. Call once at application startup.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Suppress noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
