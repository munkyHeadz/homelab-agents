"""
Shared utilities for Homelab Agent System

This module provides common functionality used across all agents and MCP servers:
- Configuration management
- LLM routing for cost optimization
- Structured logging
- Prometheus metrics
- Memory client wrapper (to be implemented)
- MCP client utilities (to be implemented)
"""

from .config import config, validate_config
from .llm_router import LLMRouter, llm_router, TaskType
from .logging import get_logger, setup_logging, LogContext

__all__ = [
    # Configuration
    "config",
    "validate_config",

    # LLM Router
    "LLMRouter",
    "llm_router",
    "TaskType",

    # Logging
    "get_logger",
    "setup_logging",
    "LogContext",
]

__version__ = "0.1.0"
