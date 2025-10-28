"""Unit tests for approval workflow."""

import pytest
import os
import json
import time
from unittest.mock import Mock, patch, MagicMock
from crews.approval import ApprovalManager, get_approval_manager, CRITICAL_SERVICES


@pytest.mark.unit
@pytest.mark.approval
class TestApprovalManager:
    """Test ApprovalManager class."""

    def test_initialization(self, approval_manager):
        """Test ApprovalManager initializes correctly."""
        assert approval_manager.bot_token == "test_token"
        assert approval_manager.chat_id == "test_chat"
        assert approval_manager.pending_approvals == {}

    def test_initialization_without_credentials(self):
        """Test ApprovalManager handles missing credentials."""
        manager = ApprovalManager(bot_token=None, chat_id=None)
        assert manager.bot_token is None
        assert manager.chat_id is None

    def test_is_critical_service_lxc(self, approval_manager):
        """Test critical service detection for LXC."""
        # LXC 200 is critical
        assert approval_manager.is_critical_service("lxc", 200) is True

        # LXC 100 is not critical
        assert approval_manager.is_critical_service("lxc", 100) is False

        # Unknown service type
        assert approval_manager.is_critical_service("unknown", 200) is False

    def test_is_critical_service_database(self, approval_manager):
        """Test critical service detection for databases."""
        # Production databases are critical
        assert approval_manager.is_critical_service("databases", "production") is True
        assert approval_manager.is_critical_service("databases", "postgres") is True

        # Case insensitive
        assert approval_manager.is_critical_service("databases", "PRODUCTION") is True

        # Test database is not critical
        assert approval_manager.is_critical_service("databases", "test_db") is False

    def test_is_critical_service_docker(self, approval_manager):
        """Test critical service detection for Docker containers."""
        # Critical containers
        assert approval_manager.is_critical_service("docker", "postgres") is True
        assert approval_manager.is_critical_service("docker", "prometheus") is True
        assert approval_manager.is_critical_service("docker", "grafana") is True
        assert approval_manager.is_critical_service("docker", "alertmanager") is True

        # Non-critical container
        assert approval_manager.is_critical_service("docker", "test-app") is False

    def test_send_approval_request_without_telegram(self, approval_manager):
        """Test approval request when Telegram is not configured."""
        manager = ApprovalManager(bot_token=None, chat_id=None)

        result = manager.send_approval_request(
            action="Test action",
            details="Test details",
            severity="warning"
        )

        assert result["approved"] is True
        assert result["approver"] == "auto (no telegram)"
        assert result["response_time"] == 0

    @patch('requests.post')
    @patch('time.time')
    @patch('time.sleep')
    def test_send_approval_request_timeout(self, mock_sleep, mock_time, mock_post, approval_manager):
        """Test approval request timeout behavior."""
        # Mock successful Telegram message send
        mock_post.return_value = Mock(
            ok=True,
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 123}}
        )

        # Mock time progression
        start_time = 1730000000.0
        mock_time.side_effect = [
            start_time,  # Initial timestamp
            start_time + 5,  # After 5 seconds
            start_time + 10,  # After 10 seconds (timeout)
            start_time + 10   # Final timestamp
        ]

        result = approval_manager.send_approval_request(
            action="Test action",
            details="Test details",
            timeout=10
        )

        # Should auto-reject on timeout
        assert result["approved"] is False
        assert result["approver"] == "auto (timeout)"
        assert "timeout" in result["reason"].lower()

    @patch('requests.post')
    def test_send_approval_request_telegram_error(self, mock_post, approval_manager):
        """Test approval request when Telegram API fails."""
        # Mock Telegram API error
        mock_post.side_effect = Exception("Telegram API error")

        result = approval_manager.send_approval_request(
            action="Test action",
            details="Test details"
        )

        # Should auto-reject on error
        assert result["approved"] is False
        assert result["approver"] == "auto (error)"
        assert "error" in result["reason"].lower()

    def test_audit_log(self, approval_manager):
        """Test audit logging functionality."""
        # Clear any existing audit log
        if os.path.exists("/tmp/test_remediation_audit.log"):
            os.remove("/tmp/test_remediation_audit.log")

        approval_manager.audit_log(
            action="Test action",
            details="Test details",
            approved=True,
            approver="human",
            outcome="success"
        )

        # Verify log file was created
        assert os.path.exists("/tmp/test_remediation_audit.log")

        # Verify log contents
        with open("/tmp/test_remediation_audit.log", "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["action"] == "Test action"
        assert log_entry["approved"] is True
        assert log_entry["approver"] == "human"
        assert log_entry["outcome"] == "success"
        assert "timestamp" in log_entry

    def test_audit_log_multiple_entries(self, approval_manager):
        """Test multiple audit log entries."""
        # Clear any existing audit log
        if os.path.exists("/tmp/test_remediation_audit.log"):
            os.remove("/tmp/test_remediation_audit.log")

        # Log multiple entries
        for i in range(3):
            approval_manager.audit_log(
                action=f"Action {i}",
                details=f"Details {i}",
                approved=i % 2 == 0,  # Alternate approved/rejected
                approver="human",
                outcome="success"
            )

        # Verify all entries logged
        with open("/tmp/test_remediation_audit.log", "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify first and last entries
        first_entry = json.loads(lines[0])
        assert first_entry["action"] == "Action 0"
        assert first_entry["approved"] is True

        last_entry = json.loads(lines[2])
        assert last_entry["action"] == "Action 2"
        assert last_entry["approved"] is True


@pytest.mark.unit
@pytest.mark.approval
class TestApprovalIntegration:
    """Test approval workflow integration with tools."""

    @patch('crews.approval.approval_manager.requests.post')
    @patch('crews.approval.approval_manager.requests.get')
    def test_critical_lxc_requires_approval(self, mock_get, mock_post, mock_proxmox):
        """Test that critical LXC requires approval."""
        from crews.tools.proxmox_tools import update_lxc_resources

        # Mock Telegram approval timeout (no response)
        mock_post.return_value = Mock(ok=True, json=lambda: {"ok": True})
        mock_get.return_value = Mock(ok=True, json=lambda: {"ok": True, "result": []})

        # Attempt to update critical LXC 200
        with patch('time.sleep'):  # Speed up timeout
            with patch('time.time', side_effect=[1730000000, 1730000000, 1730000301]):
                result = update_lxc_resources(vmid=200, memory=4096)

        # Should be rejected due to timeout
        assert "rejected" in result.lower()
        assert "200" in result

    @patch('crews.approval.approval_manager.requests.post')
    @patch('crews.approval.approval_manager.requests.get')
    def test_non_critical_lxc_auto_approved(self, mock_get, mock_post, mock_proxmox):
        """Test that non-critical LXC is auto-approved."""
        from crews.tools.proxmox_tools import update_lxc_resources

        # Mock successful config update
        mock_proxmox.nodes.return_value.lxc.return_value.config.put.return_value = None

        # Update non-critical LXC 100
        result = update_lxc_resources(vmid=100, memory=4096)

        # Should succeed without approval
        assert "successfully" in result.lower() or "✅" in result
        # Telegram should NOT be called for non-critical
        mock_post.assert_not_called()

    @patch('crews.approval.approval_manager.requests.post')
    def test_dry_run_bypasses_approval(self, mock_post, mock_proxmox):
        """Test that dry-run mode bypasses approval."""
        from crews.tools.proxmox_tools import update_lxc_resources

        # Dry-run on critical LXC 200
        result = update_lxc_resources(vmid=200, memory=4096, dry_run=True)

        # Should return dry-run output
        assert "dry-run" in result.lower() or "🔍" in result
        # Telegram should NOT be called for dry-run
        mock_post.assert_not_called()

    @patch('crews.approval.approval_manager.requests.post')
    @patch('crews.approval.approval_manager.requests.get')
    def test_vacuum_full_requires_approval(self, mock_get, mock_post, mock_postgres):
        """Test that VACUUM FULL requires approval."""
        from crews.tools.postgres_tools import vacuum_postgres_table

        # Mock Telegram approval timeout
        mock_post.return_value = Mock(ok=True, json=lambda: {"ok": True})
        mock_get.return_value = Mock(ok=True, json=lambda: {"ok": True, "result": []})

        # VACUUM FULL on any database should require approval
        with patch('time.sleep'):
            with patch('time.time', side_effect=[1730000000, 1730000000, 1730000301]):
                result = vacuum_postgres_table(
                    database="test_db",
                    table="test_table",
                    full=True
                )

        # Should be rejected
        assert "rejected" in result.lower()

    @patch('crews.approval.approval_manager.requests.post')
    def test_regular_vacuum_on_non_critical_auto_approved(self, mock_post, mock_postgres):
        """Test that regular VACUUM on non-critical DB is auto-approved."""
        from crews.tools.postgres_tools import vacuum_postgres_table

        # Mock successful vacuum
        mock_postgres['cursor'].fetchone.side_effect = [
            (True,),  # Table exists
            (1048576,),  # Size before
            (524288,)  # Size after
        ]

        # Regular VACUUM on non-critical database
        result = vacuum_postgres_table(database="test_db", table="test_table", full=False)

        # Should succeed without approval
        # Telegram should NOT be called
        mock_post.assert_not_called()


@pytest.mark.unit
def test_get_approval_manager_singleton():
    """Test that get_approval_manager returns singleton instance."""
    from crews.approval import get_approval_manager

    manager1 = get_approval_manager()
    manager2 = get_approval_manager()

    # Should be the same instance
    assert manager1 is manager2


@pytest.mark.unit
def test_critical_services_configuration():
    """Test that CRITICAL_SERVICES is properly configured."""
    from crews.approval import CRITICAL_SERVICES

    # Verify structure
    assert isinstance(CRITICAL_SERVICES, dict)
    assert "lxc" in CRITICAL_SERVICES
    assert "databases" in CRITICAL_SERVICES
    assert "docker" in CRITICAL_SERVICES

    # Verify critical LXC
    assert 200 in CRITICAL_SERVICES["lxc"]

    # Verify critical databases
    assert "production" in CRITICAL_SERVICES["databases"]
    assert "postgres" in CRITICAL_SERVICES["databases"]

    # Verify critical Docker containers
    critical_docker = CRITICAL_SERVICES["docker"]
    assert "postgres" in critical_docker
    assert "prometheus" in critical_docker
    assert "grafana" in critical_docker
    assert "alertmanager" in critical_docker
