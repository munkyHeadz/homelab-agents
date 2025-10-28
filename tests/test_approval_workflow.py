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
