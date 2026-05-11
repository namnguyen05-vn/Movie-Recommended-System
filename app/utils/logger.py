"""
Structured logging configuration.

Uses JSON formatter for structured logs that can be parsed
by log aggregation systems (ELK, DataDog, etc).

Usage:
    logger = get_logger(__name__)
    logger.info("User registered", extra={"user_id": 123, "username": "john"})
    
Output:
    {"message": "User registered", "user_id": 123, "username": "john", ...}
"""

import logging
import json
from typing import Optional

# Try to use python-json-logger if available, fallback to standard formatter
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


class JSONFormatter(logging.Formatter):
    """
    Fallback JSON formatter if python-json-logger not available
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Include extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ("name", "msg", "args", "created", "filename", 
                              "funcName", "levelname", "levelno", "lineno",
                              "module", "msecs", "message", "pathname", "process",
                              "processName", "relativeCreated", "thread", "threadName"):
                    log_obj[key] = value
        
        return json.dumps(log_obj)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger with JSON formatter
    
    Call once at app startup
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Use python-json-logger if available, else fallback
    if HAS_JSON_LOGGER:
        formatter = jsonlogger.JsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = JSONFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance for a module
    
    Usage in any module:
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"user_id": 123})
    
    Args:
        name: __name__ of calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

