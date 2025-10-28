"""Approval workflow manager for critical remediation actions.

This module provides approval workflow functionality to ensure critical
infrastructure changes require human approval before execution.
"""

import json
import logging
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Critical services that require approval for remediation
CRITICAL_SERVICES = {
    "lxc": [200],  # LXC 200 is production PostgreSQL
    "databases": ["production", "postgres"],  # Production databases
    "docker": [
        "postgres",
        "prometheus",
        "grafana",
        "alertmanager",
    ],  # Critical containers
}

# Approval timeout in seconds (default: 5 minutes)
APPROVAL_TIMEOUT = int(os.getenv("APPROVAL_TIMEOUT", "300"))

# Audit log file
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", "/tmp/remediation_audit.log")


class ApprovalManager:
    """Manages approval workflow for critical remediation actions."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize the approval manager.

        Args:
            bot_token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat ID (defaults to TELEGRAM_CHAT_ID env var)
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.pending_approvals = {}  # Store pending approval requests

        if not self.bot_token or not self.chat_id:
            logger.warning(
                "Telegram credentials not configured - approval workflow disabled"
            )

    def is_critical_service(self, service_type: str, service_id: Any) -> bool:
        """
        Check if a service is marked as critical.

        Args:
            service_type: Type of service (lxc, database, docker)
            service_id: Service identifier (vmid, database name, container name)

        Returns:
            True if service is critical, False otherwise
        """
        if service_type not in CRITICAL_SERVICES:
            return False

        critical_list = CRITICAL_SERVICES[service_type]

        # Handle integer IDs (LXC vmids)
        if isinstance(service_id, int):
            return service_id in critical_list

        # Handle string IDs (database names, container names)
        return str(service_id).lower() in [str(s).lower() for s in critical_list]

    def send_approval_request(
        self,
        action: str,
        details: str,
        severity: str = "warning",
        timeout: int = APPROVAL_TIMEOUT,
    ) -> dict:
        """
        Send approval request via Telegram and wait for response.

        Args:
            action: Description of the action requiring approval
            details: Detailed information about the action
            severity: Severity level (info, warning, critical)
            timeout: Timeout in seconds (default: 300)

        Returns:
            dict with keys: approved (bool), response_time (int), approver (str)
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured - auto-approving action")
            return {
                "approved": True,
                "response_time": 0,
                "approver": "auto (no telegram)",
                "reason": "Telegram not configured",
            }

        # Generate unique approval ID
        approval_id = f"approval_{int(time.time())}_{hash(action) % 10000}"

        # Create approval message
        severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        emoji = severity_emoji.get(severity, "❓")

        message = f"""{emoji} **APPROVAL REQUIRED** {emoji}

**Action:** {action}

**Details:**
{details}

**Severity:** {severity.upper()}
**Timeout:** {timeout}s

Reply with:
✅ `/approve {approval_id}` to allow
❌ `/reject {approval_id}` to deny

Auto-rejects in {timeout}s if no response."""

        try:
            # Send approval request
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Approval request sent: {approval_id}")

            # Store pending approval
            self.pending_approvals[approval_id] = {
                "action": action,
                "details": details,
                "severity": severity,
                "timestamp": time.time(),
                "approved": None,
            }

            # Wait for approval with timeout
            start_time = time.time()
            poll_interval = 2  # Poll every 2 seconds

            while (time.time() - start_time) < timeout:
                # Check if approval status changed
                if self.pending_approvals[approval_id]["approved"] is not None:
                    approved = self.pending_approvals[approval_id]["approved"]
                    response_time = int(time.time() - start_time)

                    # Clean up
                    del self.pending_approvals[approval_id]

                    return {
                        "approved": approved,
                        "response_time": response_time,
                        "approver": "human",
                        "reason": "Manual approval" if approved else "Manual rejection",
                    }

                # Poll for updates (check for /approve or /reject commands)
                self._check_for_response(approval_id)
                time.sleep(poll_interval)

            # Timeout - auto-reject for safety
            logger.warning(f"Approval timeout for {approval_id} - auto-rejecting")
            del self.pending_approvals[approval_id]

            # Send timeout notification
            timeout_msg = f"❌ **APPROVAL TIMEOUT**\n\nAction auto-rejected: {action}"
            requests.post(
                url, json={"chat_id": self.chat_id, "text": timeout_msg}, timeout=10
            )

            return {
                "approved": False,
                "response_time": timeout,
                "approver": "auto (timeout)",
                "reason": "No response within timeout",
            }

        except Exception as e:
            logger.error(f"Error sending approval request: {e}")
            # On error, reject for safety
            return {
                "approved": False,
                "response_time": 0,
                "approver": "auto (error)",
                "reason": f"Error: {str(e)}",
            }

    def _check_for_response(self, approval_id: str):
        """
        Check Telegram for approval/rejection commands.

        Args:
            approval_id: The approval ID to check for
        """
        try:
            # Get recent updates
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {"offset": -10, "timeout": 1}
            response = requests.get(url, params=params, timeout=5)

            if not response.ok:
                return

            data = response.json()
            if not data.get("ok"):
                return

            # Check for /approve or /reject commands
            for update in data.get("result", []):
                message = update.get("message", {})
                text = message.get("text", "")

                if f"/approve {approval_id}" in text:
                    logger.info(f"Approval received for {approval_id}")
                    self.pending_approvals[approval_id]["approved"] = True
                    return

                if f"/reject {approval_id}" in text:
                    logger.info(f"Rejection received for {approval_id}")
                    self.pending_approvals[approval_id]["approved"] = False
                    return

        except Exception as e:
            logger.error(f"Error checking for response: {e}")

    def audit_log(
        self,
        action: str,
        details: str,
        approved: bool,
        approver: str,
        outcome: str = "pending",
    ):
        """
        Log remediation action to audit file.

        Args:
            action: Description of the action
            details: Detailed information
            approved: Whether action was approved
            approver: Who approved (human, auto, etc.)
            outcome: Outcome of the action (success, failure, pending)
        """
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "details": details,
                "approved": approved,
                "approver": approver,
                "outcome": outcome,
            }

            # Append to audit log file
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(json.dumps(audit_entry) + "\n")

            logger.info(f"Audit log entry created: {action}")

        except Exception as e:
            logger.error(f"Error writing to audit log: {e}")


# Global approval manager instance
_approval_manager = None


def get_approval_manager() -> ApprovalManager:
    """Get or create global approval manager instance."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


def requires_approval(
    service_type: str,
    get_service_id: Optional[Callable] = None,
    action_name: Optional[str] = None,
):
    """
    Decorator to require approval for critical service operations.

    Args:
        service_type: Type of service (lxc, database, docker)
        get_service_id: Function to extract service ID from function args
        action_name: Custom action name (defaults to function name)

    Usage:
        @requires_approval(service_type="lxc", get_service_id=lambda vmid, **kw: vmid)
        def update_lxc_resources(vmid: int, cpu: int = None, ...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_approval_manager()

            # Extract service ID
            service_id = None
            if get_service_id:
                try:
                    service_id = get_service_id(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Could not extract service ID: {e}")

            # Check if service is critical
            is_critical = False
            if service_id:
                is_critical = manager.is_critical_service(service_type, service_id)

            # If not critical, execute without approval
            if not is_critical:
                logger.info(
                    f"Non-critical service {service_id} - executing without approval"
                )
                result = func(*args, **kwargs)

                # Audit log
                manager.audit_log(
                    action=action_name or func.__name__,
                    details=f"Non-critical {service_type}: {service_id}",
                    approved=True,
                    approver="auto (non-critical)",
                    outcome="success",
                )

                return result

            # Critical service - request approval
            action = action_name or func.__name__
            details = f"Service Type: {service_type}\nService ID: {service_id}\nArguments: {kwargs}"

            # Check for dry_run parameter
            if kwargs.get("dry_run", False):
                logger.info(f"Dry-run mode - executing without approval")
                result = func(*args, **kwargs)

                manager.audit_log(
                    action=action,
                    details=details,
                    approved=True,
                    approver="auto (dry-run)",
                    outcome="success (dry-run)",
                )

                return result

            # Request approval
            approval_result = manager.send_approval_request(
                action=f"{action} on {service_type} {service_id}",
                details=details,
                severity=(
                    "critical"
                    if service_type == "lxc" and service_id == 200
                    else "warning"
                ),
            )

            # Log approval request
            manager.audit_log(
                action=action,
                details=details,
                approved=approval_result["approved"],
                approver=approval_result["approver"],
                outcome="pending",
            )

            # If approved, execute
            if approval_result["approved"]:
                logger.info(
                    f"Action approved by {approval_result['approver']} - executing"
                )

                try:
                    result = func(*args, **kwargs)

                    # Log success
                    manager.audit_log(
                        action=action,
                        details=details,
                        approved=True,
                        approver=approval_result["approver"],
                        outcome="success",
                    )

                    return result

                except Exception as e:
                    # Log failure
                    manager.audit_log(
                        action=action,
                        details=details,
                        approved=True,
                        approver=approval_result["approver"],
                        outcome=f"failure: {str(e)}",
                    )
                    raise
            else:
                # Rejected - do not execute
                logger.warning(
                    f"Action rejected by {approval_result['approver']} - not executing"
                )

                rejection_msg = (
                    f"❌ Action rejected: {action}\nReason: {approval_result['reason']}"
                )
                return rejection_msg

        return wrapper

    return decorator
