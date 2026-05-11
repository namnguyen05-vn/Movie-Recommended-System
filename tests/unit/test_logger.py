"""
Tests for logging configuration
"""

import logging
from app.utils.logger import get_logger


def test_get_logger_returns_logger():
    """get_logger should return a logger instance"""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__


def test_logger_name_matches():
    """Logger name should match module name"""
    logger = get_logger("test_module")
    assert logger.name == "test_module"

