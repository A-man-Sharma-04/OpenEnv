"""Centralized logging configuration for OpenEnv."""

import logging
import sys
from typing import Optional


_CONFIGURED = False

def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup logging configuration."""
    global _CONFIGURED

    if _CONFIGURED:
        return

    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))

    # Clear inherited handlers to avoid duplicate logs when imported repeatedly.
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _CONFIGURED = True

def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    setup_logging()
    return logging.getLogger(name)

# Default setup
setup_logging()
