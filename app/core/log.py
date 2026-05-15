"""Application logging configuration.

The log level is controlled by the ``LOG_LEVEL`` environment variable
(default: ``INFO``). Call :func:`setup_logging` once at application startup.
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
