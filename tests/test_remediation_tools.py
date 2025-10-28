"""Integration tests for remediation tools."""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.integration
@pytest.mark.remediation
class TestProxmoxRemediationTools:
    """Test Proxmox remediation tools."""

    def test_update_lxc_resources_success(self, mock_proxmox):
        """Test successful LXC resource update."""
        from crews.tools.proxmox_tools import update_lxc_resources

        # Mock successful config update
        mock_proxmox.nodes.return_value.lxc.return_value.config.put.return_value = None

        result = update_lxc_resources(vmid=100, memory=4096)

        # Verify success
        assert "successfully" in result.lower() or "✅" in result
        assert "4096" in result

        # Verify API was called correctly
        mock_proxmox.nodes.return_value.lxc.return_value.config.put.assert_called_once()
        call_kwargs = mock_proxmox.nodes.return_value.lxc.return_value.config.put.call_args[1]
        assert call_kwargs['memory'] == 4096

    def test_update_lxc_resources_dry_run(self, mock_proxmox):
        """Test LXC resource update in dry-run mode."""
        from crews.tools.proxmox_tools import update_lxc_resources

        result = update_lxc_resources(vmid=100, cpu=4, memory=8192, dry_run=True)

        # Verify dry-run output
        assert "dry-run" in result.lower() or "🔍" in result
        assert "4" in result  # CPU cores
        assert "8192" in result  # Memory

        # Verify API was NOT called
        mock_proxmox.nodes.return_value.lxc.return_value.config.put.assert_not_called()

    def test_update_lxc_resources_no_changes(self, mock_proxmox):
        """Test LXC resource update with no changes specified."""
        from crews.tools.proxmox_tools import update_lxc_resources

        result = update_lxc_resources(vmid=100)

        # Should return info message
        assert "no changes" in result.lower()

    def test_update_lxc_resources_insufficient_memory(self, mock_proxmox):
        """Test LXC resource update when node has insufficient memory."""
        from crews.tools.proxmox_tools import update_lxc_resources

        # Mock node with limited memory
        mock_proxmox.nodes.return_value.status.get.return_value = {
            'memory': {
                'total': 4 * 1024**3,  # 4GB total
                'used': 3 * 1024**3     # 3GB used (1GB free)
            }
        }

        # Try to allocate 2GB (more than available)
        result = update_lxc_resources(vmid=100, memory=2048)

        # Should fail
        assert "cannot allocate" in result.lower() or "❌" in result

    def test_create_lxc_snapshot_success(self, mock_proxmox):
        """Test successful LXC snapshot creation."""
        from crews.tools.proxmox_tools import create_lxc_snapshot

        # Mock successful snapshot creation
        mock_proxmox.nodes.return_value.lxc.return_value.snapshot.post.return_value = None

        result = create_lxc_snapshot(
            vmid=100,
            name="test-snapshot",
            description="Test snapshot"
        )

        # Verify success
        assert "successfully" in result.lower() or "✅" in result
        assert "test-snapshot" in result

        # Verify API was called correctly
        mock_proxmox.nodes.return_value.lxc.return_value.snapshot.post.assert_called_once_with(
            snapname="test-snapshot",
            description="Test snapshot"
        )

    def test_create_lxc_snapshot_invalid_name(self, mock_proxmox):
        """Test LXC snapshot creation with invalid name."""
        from crews.tools.proxmox_tools import create_lxc_snapshot

        # Invalid name (contains special characters)
        result = create_lxc_snapshot(vmid=100, name="test snapshot!")

        # Should fail validation
        assert "invalid" in result.lower() or "❌" in result

    def test_create_lxc_snapshot_dry_run(self, mock_proxmox):
        """Test LXC snapshot creation in dry-run mode."""
        from crews.tools.proxmox_tools import create_lxc_snapshot

        result = create_lxc_snapshot(
            vmid=100,
            name="test-snapshot",
            dry_run=True
        )

        # Verify dry-run output
        assert "dry-run" in result.lower() or "🔍" in result
        assert "test-snapshot" in result

        # Verify API was NOT called
        mock_proxmox.nodes.return_value.lxc.return_value.snapshot.post.assert_not_called()


@pytest.mark.integration
@pytest.mark.remediation
class TestPostgresRemediationTools:
    """Test PostgreSQL remediation tools."""

    def test_vacuum_postgres_table_success(self, mock_postgres):
        """Test successful VACUUM operation."""
        from crews.tools.postgres_tools import vacuum_postgres_table

        # Mock successful vacuum
        mock_postgres['cursor'].fetchone.side_effect = [
            (True,),  # Table exists
            (2097152,),  # Size before (2MB)
            (1048576,)  # Size after (1MB)
        ]

        result = vacuum_postgres_table(database="test_db", table="test_table")

        # Verify success
        assert "successfully" in result.lower() or "✅" in result
        assert "test_table" in result

        # Verify VACUUM was executed
        execute_calls = mock_postgres['cursor'].execute.call_args_list
        vacuum_executed = any("VACUUM" in str(call) for call in execute_calls)
        assert vacuum_executed

    def test_vacuum_postgres_table_full(self, mock_postgres):
        """Test VACUUM FULL operation."""
        from crews.tools.postgres_tools import vacuum_postgres_table

        # Mock successful vacuum full
        mock_postgres['cursor'].fetchone.side_effect = [
            (True,),  # Table exists
            (4194304,),  # Size before (4MB)
            (2097152,)  # Size after (2MB)
        ]

        with patch('crews.approval.approval_manager.requests.post'):
            with patch('time.sleep'):
                # VACUUM FULL requires approval, will timeout
                with patch('time.time', side_effect=[1730000000, 1730000000, 1730000301]):
                    result = vacuum_postgres_table(
                        database="test_db",
                        table="test_table",
                        full=True
                    )

        # Should be rejected due to approval timeout
        assert "rejected" in result.lower()

    def test_vacuum_postgres_table_dry_run(self, mock_postgres):
        """Test VACUUM in dry-run mode."""
        from crews.tools.postgres_tools import vacuum_postgres_table

        result = vacuum_postgres_table(
            database="test_db",
            table="test_table",
            dry_run=True
        )

        # Verify dry-run output
        assert "dry-run" in result.lower() or "🔍" in result
        assert "test_table" in result

        # Verify no connection was made
        mock_postgres['cursor'].execute.assert_not_called()

    def test_vacuum_postgres_table_not_exists(self, mock_postgres):
        """Test VACUUM on non-existent table."""
        from crews.tools.postgres_tools import vacuum_postgres_table

        # Mock table does not exist
        mock_postgres['cursor'].fetchone.return_value = (False,)

        result = vacuum_postgres_table(database="test_db", table="nonexistent")

        # Should fail
        assert "does not exist" in result.lower() or "❌" in result

    def test_clear_postgres_connections_success(self, mock_postgres):
        """Test successful connection termination."""
        from crews.tools.postgres_tools import clear_postgres_connections

        # Mock active connections
        mock_postgres['cursor'].fetchall.return_value = [
            (12345, 'test_user', 'test_app', 'active', None, None),
            (12346, 'test_user', 'test_app', 'idle', None, None)
        ]

        # Mock successful termination
        mock_postgres['cursor'].execute.return_value = None

        # Non-critical database (auto-approved)
        result = clear_postgres_connections(database="test_db")

        # Verify connections were terminated
        # Should show number of connections terminated
        assert "2" in result or "terminated" in result.lower()

    def test_clear_postgres_connections_no_connections(self, mock_postgres):
        """Test connection termination when no connections exist."""
        from crews.tools.postgres_tools import clear_postgres_connections

        # Mock no active connections
        mock_postgres['cursor'].fetchall.return_value = []

        result = clear_postgres_connections(database="test_db")

        # Should return info message
        assert "no active connections" in result.lower()

    def test_clear_postgres_connections_dry_run(self, mock_postgres):
        """Test connection termination in dry-run mode."""
        from crews.tools.postgres_tools import clear_postgres_connections

        # Mock active connections
        mock_postgres['cursor'].fetchall.return_value = [
            (12345, 'test_user', 'test_app', 'active', None, None)
        ]

        result = clear_postgres_connections(database="test_db", dry_run=True)

        # Verify dry-run output
        assert "dry-run" in result.lower() or "🔍" in result
        assert "12345" in result  # PID


@pytest.mark.integration
@pytest.mark.remediation
class TestDockerRemediationTools:
    """Test Docker remediation tools."""

    def test_update_docker_resources_success(self, mock_docker):
        """Test successful Docker resource update."""
        from crews.tools.docker_tools import update_docker_resources

        result = update_docker_resources(
            container="test-container",
            cpu_limit="2.0",
            memory_limit="2g"
        )

        # Verify success
        assert "successfully" in result.lower() or "✅" in result
        assert "test-container" in result

        # Verify container.update was called
        mock_docker['container'].update.assert_called_once()
        call_kwargs = mock_docker['container'].update.call_args[1]
        assert 'cpu_quota' in call_kwargs
        assert 'mem_limit' in call_kwargs

    def test_update_docker_resources_cpu_only(self, mock_docker):
        """Test Docker CPU limit update."""
        from crews.tools.docker_tools import update_docker_resources

        result = update_docker_resources(container="test-container", cpu_limit="1.5")

        # Verify success
        assert "successfully" in result.lower() or "✅" in result
        assert "1.5" in result

        # Verify only CPU was updated
        call_kwargs = mock_docker['container'].update.call_args[1]
        assert 'cpu_quota' in call_kwargs
        assert 'mem_limit' not in call_kwargs

    def test_update_docker_resources_memory_only(self, mock_docker):
        """Test Docker memory limit update."""
        from crews.tools.docker_tools import update_docker_resources

        result = update_docker_resources(container="test-container", memory_limit="4g")

        # Verify success
        assert "successfully" in result.lower() or "✅" in result
        assert "4g" in result

        # Verify only memory was updated
        call_kwargs = mock_docker['container'].update.call_args[1]
        assert 'mem_limit' in call_kwargs
        assert 'cpu_quota' not in call_kwargs

    def test_update_docker_resources_dry_run(self, mock_docker):
        """Test Docker resource update in dry-run mode."""
        from crews.tools.docker_tools import update_docker_resources

        result = update_docker_resources(
            container="test-container",
            cpu_limit="2.0",
            memory_limit="2g",
            dry_run=True
        )

        # Verify dry-run output
        assert "dry-run" in result.lower() or "🔍" in result

        # Verify container.update was NOT called
        mock_docker['container'].update.assert_not_called()

    def test_update_docker_resources_no_changes(self, mock_docker):
        """Test Docker resource update with no changes specified."""
        from crews.tools.docker_tools import update_docker_resources

        result = update_docker_resources(container="test-container")

        # Should return info message
        assert "no changes" in result.lower()

    def test_update_docker_resources_container_not_found(self, mock_docker):
        """Test Docker resource update when container doesn't exist."""
        from crews.tools.docker_tools import update_docker_resources
        import docker.errors

        # Mock container not found
        mock_docker['client'].containers.get.side_effect = docker.errors.NotFound("Container not found")

        result = update_docker_resources(container="nonexistent", cpu_limit="2.0")

        # Should fail
        assert "not found" in result.lower() or "❌" in result


@pytest.mark.integration
@pytest.mark.slow
def test_end_to_end_approval_workflow(mock_proxmox, mock_telegram):
    """Test complete end-to-end approval workflow."""
    from crews.tools.proxmox_tools import update_lxc_resources

    # Attempt to update critical LXC 200
    with patch('time.sleep'):  # Speed up test
        with patch('time.time', side_effect=[1730000000, 1730000000, 1730000301]):
            result = update_lxc_resources(vmid=200, memory=4096)

    # Should be rejected due to timeout
    assert "rejected" in result.lower()

    # Verify Telegram was called to send approval request
    assert mock_telegram['post'].called

    # Verify message contains critical information
    call_args = mock_telegram['post'].call_args
    message_text = call_args[1]['json']['text']
    assert "APPROVAL REQUIRED" in message_text
    assert "200" in message_text
    assert "4096" in message_text
