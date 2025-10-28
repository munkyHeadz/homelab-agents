"""Approval workflow for critical remediation actions."""

from .approval_manager import (
    ApprovalManager,
    requires_approval,
    CRITICAL_SERVICES,
)

__all__ = [
    "ApprovalManager",
    "requires_approval",
    "CRITICAL_SERVICES",
]
