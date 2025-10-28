"""Pytest configuration and shared fixtures."""

import os
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


# Environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_bot_token_123456789"
    os.environ["TELEGRAM_CHAT_ID"] = "test_chat_id_123456789"
    os.environ["APPROVAL_TIMEOUT"] = "10"  # Short timeout for tests
    os.environ["AUDIT_LOG_FILE"] = "/tmp/test_remediation_audit.log"

    # Proxmox test env
    os.environ["PROXMOX_HOST"] = "test.proxmox.local"
    os.environ["PROXMOX_TOKEN_SECRET"] = "test_secret"
    os.environ["PROXMOX_NODE"] = "test-node"

    # PostgreSQL test env
    os.environ["POSTGRES_HOST"] = "test.postgres.local"
    os.environ["POSTGRES_USER"] = "test_user"
    os.environ["POSTGRES_PASSWORD"] = "test_password"

    yield

    # Cleanup
    if os.path.exists("/tmp/test_remediation_audit.log"):
        os.remove("/tmp/test_remediation_audit.log")


# Mock Telegram API
@pytest.fixture
def mock_telegram():
    """Mock Telegram API responses."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:

        # Mock successful message send
        mock_post.return_value = Mock(
            ok=True,
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 123}},
        )

        # Mock getUpdates (no approval yet)
        mock_get.return_value = Mock(
            ok=True, status_code=200, json=lambda: {"ok": True, "result": []}
        )

        yield {"post": mock_post, "get": mock_get}


# Mock Proxmox API
@pytest.fixture
def mock_proxmox():
    """Mock Proxmox API client."""
    mock_client = MagicMock()

    # Mock LXC config
    mock_client.nodes.return_value.lxc.return_value.config.get.return_value = {
        "hostname": "test-lxc",
        "cores": 2,
        "memory": 2048,
        "swap": 512,
    }

    # Mock node status
    mock_client.nodes.return_value.status.get.return_value = {
        "memory": {"total": 16 * 1024**3, "used": 8 * 1024**3}  # 16GB  # 8GB
    }

    # Mock LXC list
    mock_client.nodes.return_value.lxc.get.return_value = [
        {"vmid": 100, "name": "test-lxc-1", "status": "running"},
        {"vmid": 200, "name": "postgres-prod", "status": "running"},
    ]

    # Mock snapshots
    mock_client.nodes.return_value.lxc.return_value.snapshot.get.return_value = []

    with patch(
        "crews.tools.proxmox_tools._get_proxmox_client", return_value=mock_client
    ):
        yield mock_client


# Mock PostgreSQL connection
@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Mock cursor methods
    mock_cursor.fetchone.return_value = (True,)  # Table exists
    mock_cursor.fetchall.return_value = [
        (12345, "test_user", "test_app", "active", datetime.now(), datetime.now())
    ]

    mock_conn.cursor.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        yield {"conn": mock_conn, "cursor": mock_cursor}


# Mock Docker client
@pytest.fixture
def mock_docker():
    """Mock Docker client."""
    mock_client = MagicMock()
    mock_container = MagicMock()

    mock_container.name = "test-container"
    mock_container.attrs = {
        "HostConfig": {"NanoCpus": 2000000000, "Memory": 2147483648}  # 2 cores  # 2GB
    }

    mock_client.containers.get.return_value = mock_container

    with patch("docker.from_env", return_value=mock_client):
        yield {"client": mock_client, "container": mock_container}


# Approval Manager fixture
@pytest.fixture
def approval_manager():
    """Create approval manager instance for testing."""
    from crews.approval import ApprovalManager

    manager = ApprovalManager(bot_token="test_token", chat_id="test_chat")
    return manager


# Mock time to speed up timeout tests
@pytest.fixture
def mock_time():
    """Mock time.time() and time.sleep() for faster tests."""
    with patch("time.time") as mock_time_time, patch("time.sleep") as mock_sleep:

        # Start at a fixed timestamp
        mock_time_time.return_value = 1730000000.0

        def advance_time(seconds):
            """Helper to advance mocked time."""
            mock_time_time.return_value += seconds

        yield {"time": mock_time_time, "sleep": mock_sleep, "advance": advance_time}


# Critical service test data
@pytest.fixture
def critical_services():
    """Critical services configuration for testing."""
    return {
        "lxc": [200],
        "databases": ["production", "postgres"],
        "docker": ["postgres", "prometheus", "grafana", "alertmanager"],
    }
