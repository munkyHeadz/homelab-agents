"""
Structured logging for Homelab Agent System

Provides JSON and text logging with context enrichment.
Integrates with Prometheus metrics and external log aggregation (Loki).
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import structlog
from pythonjsonlogger import jsonlogger
from .config import config

# Ensure logs directory exists
LOG_DIR = Path(config.logging.file).parent
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None
):
    """
    Configure structured logging for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Path to log file
    """
    log_level = log_level or config.logging.level
    log_format = log_format or config.logging.format
    log_file = log_file or config.logging.file

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create formatters
    if log_format == "json":
        # JSON formatter for machine-readable logs
        formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s %(agent_id)s %(task_type)s"
        )
    else:
        # Text formatter for human-readable logs
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)

    return root_logger


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding contextual information to logs

    Usage:
        with LogContext(agent_id="infrastructure", task_id="vm-create-123"):
            logger.info("Creating VM")
    """

    def __init__(self, **kwargs):
        self.context = kwargs

    def __enter__(self):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.clear_contextvars()


# Initialize logging on import
setup_logging()


if __name__ == "__main__":
    # Test logging
    logger = get_logger(__name__)

    print("🧪 Testing logging system\n")

    logger.debug("Debug message", extra={"test": "value"})
    logger.info("Info message", extra={"agent_id": "test", "task_type": "test"})
    logger.warning("Warning message")
    logger.error("Error message", extra={"error_code": 500})

    # Test context manager
    print("\nTesting LogContext:")
    with LogContext(agent_id="orchestrator", task_id="task-123"):
        logger.info("Message with context")
        logger.info("Another message with same context")

    logger.info("Message without context")

    print(f"\nLogs are being written to: {config.logging.file}")
