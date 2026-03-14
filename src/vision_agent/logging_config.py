"""Logging configuration for Vision Agent.

Call configure_logging() once at application startup.
Outputs structured logs with consistent format.
"""

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def configure_logging(level: LogLevel = "INFO") -> None:
    """Set up root logger with console handler.

    Args:
        level: Log level string (DEBUG/INFO/WARNING/ERROR).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level))

    # Avoid adding duplicate handlers on repeated calls
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_FORMATTER)
        root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "langsmith"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).debug("Logging configured at level: %s", level)
