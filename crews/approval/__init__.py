"""Approval workflow for critical remediation actions."""

from .approval_manager import (CRITICAL_SERVICES, ApprovalManager,
                               get_approval_manager)

__all__ = [
    "ApprovalManager",
    "get_approval_manager",
    "CRITICAL_SERVICES",
]
