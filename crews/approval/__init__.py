"""Approval workflow for critical remediation actions."""

from .approval_manager import (
    ApprovalManager,
    get_approval_manager,
    CRITICAL_SERVICES,
)

__all__ = [
    "ApprovalManager",
    "get_approval_manager",
    "CRITICAL_SERVICES",
]
