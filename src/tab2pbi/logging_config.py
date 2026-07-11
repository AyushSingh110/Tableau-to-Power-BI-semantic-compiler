"""Shared logging setup for the pipeline."""

import logging

_CONFIGURED = False


def configure(level: int = logging.INFO) -> None:
    """Configure root logging once, with a compact format."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (configuring logging on first use)."""
    configure()
    return logging.getLogger(name)
