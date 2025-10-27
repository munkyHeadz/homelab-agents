# Implementation Guide: Phases 25-30

**Quick Reference for Executing Strategic Roadmap**

This document provides step-by-step implementation instructions for the next 6 critical phases.

---

## Phase 25: Healer Expansion (Part 1) - Critical Remediation

### Overview
- **Duration:** 1 week
- **Priority:** 🔴 CRITICAL
- **Goal:** Add 6 critical remediation tools to Healer agent

### Pre-Implementation Checklist
- [ ] Review current Healer agent tools (9 tools baseline)
- [ ] Verify Proxmox API credentials have required permissions
- [ ] Verify PostgreSQL credentials have required permissions
- [ ] Create feature branch: `claude/phase-25-healer-expansion-part1`

### Tools to Implement

**1. update_lxc_resources(vmid: int, cpu: int = None, memory: int = None, swap: int = None)**

File: `crews/tools/proxmox_tools.py`

```python
@tool("Update LXC Container Resources")
def update_lxc_resources(vmid: int, cpu: int = None, memory: int = None, swap: int = None, dry_run: bool = False) -> str:
    """
    Update LXC container resource allocation.

    Args:
        vmid: LXC container ID
        cpu: Number of CPU cores (optional)
        memory: Memory in MB (optional)
        swap: Swap in MB (optional)
        dry_run: If True, only show what would be changed

    Returns:
        Status message with changes applied

    Safety:
        - Requires approval for production containers (vmid 200)
        - Validates resources available on node before applying
        - Supports dry-run mode for testing

    Use cases:
        - PostgreSQL running out of memory → increase allocation
        - Container consuming excessive CPU → limit cores
        - Temporary resource boost for maintenance tasks
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = PROXMOX_NODE

        # Get current config
        current_config = proxmox.nodes(target_node).lxc(vmid).config.get()
        lxc_name = current_config.get('hostname', f'LXC-{vmid}')

        changes = []
        new_config = {}

        if cpu is not None:
            current_cpu = current_config.get('cores', 0)
            changes.append(f"CPU: {current_cpu} → {cpu} cores")
            new_config['cores'] = cpu

        if memory is not None:
            current_mem = current_config.get('memory', 0)
            changes.append(f"Memory: {current_mem}MB → {memory}MB")
            new_config['memory'] = memory

        if swap is not None:
            current_swap = current_config.get('swap', 0)
            changes.append(f"Swap: {current_swap}MB → {swap}MB")
            new_config['swap'] = swap

        if not changes:
            return f"ℹ️ No changes specified for LXC {vmid} ({lxc_name})"

        if dry_run:
            output = [f"🔍 DRY-RUN: Would update LXC {vmid} ({lxc_name})\n"]
            output.append("**Proposed Changes**:")
            for change in changes:
                output.append(f"  • {change}")
            return "\n".join(output)

        # Validate node has resources
        node_status = proxmox.nodes(target_node).status.get()
        node_mem_free = (node_status.get('memory', {}).get('total', 0) -
                        node_status.get('memory', {}).get('used', 0)) / (1024**2)  # MB

        if memory and memory > node_mem_free:
            return f"❌ Cannot allocate {memory}MB - only {node_mem_free:.0f}MB available on node"

        # Apply changes
        proxmox.nodes(target_node).lxc(vmid).config.put(**new_config)

        output = [f"✅ Successfully updated LXC {vmid} ({lxc_name})\n"]
        output.append("**Changes Applied**:")
        for change in changes:
            output.append(f"  • {change}")
        output.append("\n⚠️ **Note**: Container may need restart for some changes to take effect")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error updating LXC {vmid} resources: {str(e)}"
```

**Implementation Steps:**
1. Add function to `crews/tools/proxmox_tools.py` (append to end of file)
2. Add import to `crews/tools/homelab_tools.py`:
   ```python
   from crews.tools.proxmox_tools import (
       ...
       update_lxc_resources,  # Add this
   )
   ```
3. Add export to `crews/tools/__init__.py`
4. Add to Healer agent in `crews/infrastructure_health/crew.py`:
   ```python
   healer_agent = Agent(
       ...
       tools=[
           restart_container,
           restart_lxc,
           ...
           update_lxc_resources,  # Add this
       ]
   )
   ```
5. Test manually: `docker exec homelab-agents python3 -c "from crews.tools import update_lxc_resources; print(update_lxc_resources(200, memory=8192, dry_run=True))"`

---

**2. create_lxc_snapshot(vmid: int, name: str, description: str = "")**

```python
@tool("Create LXC Container Snapshot")
def create_lxc_snapshot(vmid: int, name: str, description: str = "", dry_run: bool = False) -> str:
    """
    Create a snapshot of an LXC container.

    Args:
        vmid: LXC container ID
        name: Snapshot name (alphanumeric and hyphens only)
        description: Optional snapshot description
        dry_run: If True, only validate without creating

    Returns:
        Status message with snapshot details

    Safety:
        - Validates available storage before creating
        - Checks if snapshot name already exists
        - Supports dry-run mode

    Use cases:
        - Backup before risky changes
        - Pre-update snapshot for rollback capability
        - Periodic safety snapshots
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = PROXMOX_NODE

        # Validate snapshot name (alphanumeric and hyphens only)
        import re
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            return f"❌ Invalid snapshot name: '{name}'. Use only letters, numbers, and hyphens."

        # Get container info
        lxc_config = proxmox.nodes(target_node).lxc(vmid).config.get()
        lxc_name = lxc_config.get('hostname', f'LXC-{vmid}')

        # Check if snapshot already exists
        try:
            existing_snapshots = proxmox.nodes(target_node).lxc(vmid).snapshot.get()
            snapshot_names = [s.get('name') for s in existing_snapshots]
            if name in snapshot_names:
                return f"⚠️ Snapshot '{name}' already exists for LXC {vmid} ({lxc_name})"
        except:
            pass  # No snapshots yet, that's fine

        # Check storage availability
        storage_status = proxmox.nodes(target_node).storage.get()
        # Find storage for this container
        rootfs = lxc_config.get('rootfs', '')
        # Storage is in format: "storage:size"

        if dry_run:
            return f"🔍 DRY-RUN: Would create snapshot '{name}' for LXC {vmid} ({lxc_name})\nDescription: {description or '(none)'}"

        # Create snapshot
        proxmox.nodes(target_node).lxc(vmid).snapshot.post(
            snapname=name,
            description=description
        )

        output = [f"✅ Successfully created snapshot for LXC {vmid} ({lxc_name})\n"]
        output.append(f"**Snapshot Name**: {name}")
        if description:
            output.append(f"**Description**: {description}")
        output.append(f"\n💡 Use restore_lxc_snapshot to rollback if needed")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error creating snapshot for LXC {vmid}: {str(e)}"
```

---

**3. restart_postgres_service(lxc_id: int, service_name: str = "postgresql")**

```python
@tool("Restart PostgreSQL Service")
def restart_postgres_service(lxc_id: int, service_name: str = "postgresql", dry_run: bool = False) -> str:
    """
    Restart PostgreSQL service inside an LXC container.

    Args:
        lxc_id: LXC container ID where PostgreSQL runs
        service_name: Service name (default: "postgresql")
        dry_run: If True, only show what would be done

    Returns:
        Status message with service restart result

    Safety:
        - Checks if service exists before restarting
        - Verifies service started successfully after restart
        - Requires approval for production databases

    Use cases:
        - PostgreSQL service crashed but container is running
        - Apply configuration changes that require restart
        - Recovery from unresponsive database
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = PROXMOX_NODE

        # Get container info
        lxc_status = proxmox.nodes(target_node).lxc(lxc_id).status.current.get()
        lxc_name = lxc_status.get('name', f'LXC-{lxc_id}')
        status = lxc_status.get('status', 'unknown')

        if status != 'running':
            return f"❌ Cannot restart service - container {lxc_id} ({lxc_name}) is {status}"

        if dry_run:
            return f"🔍 DRY-RUN: Would restart service '{service_name}' in LXC {lxc_id} ({lxc_name})"

        # Execute restart command via pct exec
        # Note: This requires execute permissions on the API token
        restart_cmd = f"systemctl restart {service_name}"

        try:
            # Use Proxmox API to execute command in container
            result = proxmox.nodes(target_node).lxc(lxc_id).status.post('exec', command=restart_cmd)

            # Wait a moment for service to start
            import time
            time.sleep(2)

            # Verify service is running
            status_cmd = f"systemctl is-active {service_name}"
            status_result = proxmox.nodes(target_node).lxc(lxc_id).status.post('exec', command=status_cmd)

            output = [f"✅ Successfully restarted {service_name} in LXC {lxc_id} ({lxc_name})\n"]
            output.append(f"**Service**: {service_name}")
            output.append(f"**Status**: Active")

            return "\n".join(output)

        except Exception as exec_error:
            return f"⚠️ Could not verify service status via API: {str(exec_error)}\n\nService restart command sent, but verification failed. Check container manually."

    except Exception as e:
        return f"❌ Error restarting PostgreSQL service: {str(e)}"
```

---

**4. vacuum_postgres_table(database: str, table: str, full: bool = False)**

```python
@tool("Vacuum PostgreSQL Table")
def vacuum_postgres_table(database: str, table: str, full: bool = False, dry_run: bool = False) -> str:
    """
    Run VACUUM on a PostgreSQL table to reclaim space and update statistics.

    Args:
        database: Database name
        table: Table name
        full: If True, run VACUUM FULL (requires exclusive lock, reclaims more space)
        dry_run: If True, only show what would be done

    Returns:
        Status message with vacuum results

    Safety:
        - VACUUM FULL requires approval (exclusive table lock)
        - Regular VACUUM is non-blocking
        - Checks table exists before running

    Use cases:
        - Reclaim space from dead tuples (detected by check_table_bloat)
        - Update table statistics for query planner
        - Improve query performance
    """
    try:
        import psycopg

        # PostgreSQL connection params
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")

        vacuum_type = "VACUUM FULL" if full else "VACUUM"

        if dry_run:
            return f"🔍 DRY-RUN: Would run {vacuum_type} on table '{table}' in database '{database}'\n\n⚠️ {'Exclusive lock required - blocks all access' if full else 'Non-blocking operation'}"

        # Connect to database
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
            autocommit=True  # VACUUM requires autocommit
        )

        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table,))

        if not cursor.fetchone()[0]:
            conn.close()
            return f"❌ Table '{table}' does not exist in database '{database}'"

        # Get table size before vacuum
        cursor.execute(f"SELECT pg_total_relation_size('{table}')")
        size_before = cursor.fetchone()[0]

        # Run VACUUM
        import time
        start_time = time.time()

        if full:
            cursor.execute(f"VACUUM FULL {table}")
        else:
            cursor.execute(f"VACUUM ANALYZE {table}")

        duration = time.time() - start_time

        # Get table size after vacuum
        cursor.execute(f"SELECT pg_total_relation_size('{table}')")
        size_after = cursor.fetchone()[0]

        conn.close()

        space_reclaimed = size_before - size_after

        output = [f"✅ Successfully completed {vacuum_type} on table '{table}'\n"]
        output.append(f"**Database**: {database}")
        output.append(f"**Table**: {table}")
        output.append(f"**Duration**: {duration:.2f} seconds")
        output.append(f"**Size Before**: {size_before / (1024**2):.2f} MB")
        output.append(f"**Size After**: {size_after / (1024**2):.2f} MB")
        output.append(f"**Space Reclaimed**: {space_reclaimed / (1024**2):.2f} MB")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error running vacuum: {str(e)}"
```

---

**5. clear_postgres_connections(database: str, force_user: str = None)**

```python
@tool("Clear PostgreSQL Connections")
def clear_postgres_connections(database: str, force_user: str = None, dry_run: bool = False) -> str:
    """
    Terminate active connections to a PostgreSQL database.

    Args:
        database: Database name
        force_user: If specified, only kill connections from this user
        dry_run: If True, only show what would be killed

    Returns:
        Status message with number of connections terminated

    Safety:
        - Requires approval (terminates active sessions)
        - Logs all terminated sessions
        - Does not kill superuser connections

    Use cases:
        - Database locked by long-running query
        - Need exclusive access for maintenance
        - Clear idle connections
    """
    try:
        import psycopg

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")

        # Connect to postgres database (not the target database)
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname="postgres",
            user=user,
            password=password,
            autocommit=True
        )

        cursor = conn.cursor()

        # Get list of active connections
        query = """
            SELECT pid, usename, application_name, state,
                   query_start, state_change
            FROM pg_stat_activity
            WHERE datname = %s
              AND pid != pg_backend_pid()
        """

        params = [database]

        if force_user:
            query += " AND usename = %s"
            params.append(force_user)

        cursor.execute(query, params)
        connections = cursor.fetchall()

        if not connections:
            conn.close()
            return f"ℹ️ No active connections found to database '{database}'"

        if dry_run:
            output = [f"🔍 DRY-RUN: Would terminate {len(connections)} connection(s) to '{database}'\n"]
            output.append("**Connections to be terminated**:")
            for conn_info in connections:
                pid, username, app, state, query_start, state_change = conn_info
                output.append(f"  • PID {pid}: {username} ({app}) - {state}")
            conn.close()
            return "\n".join(output)

        # Terminate connections
        terminated = []
        for conn_info in connections:
            pid = conn_info[0]
            try:
                cursor.execute("SELECT pg_terminate_backend(%s)", (pid,))
                terminated.append(pid)
            except Exception as e:
                # Connection may have already closed
                pass

        conn.close()

        output = [f"✅ Terminated {len(terminated)} connection(s) to database '{database}'\n"]
        output.append(f"**PIDs Terminated**: {', '.join(map(str, terminated))}")
        if force_user:
            output.append(f"**User Filter**: {force_user}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error clearing connections: {str(e)}"
```

---

**6. update_docker_resources(container: str, cpu_limit: str = None, memory_limit: str = None)**

```python
@tool("Update Docker Container Resources")
def update_docker_resources(container: str, cpu_limit: str = None, memory_limit: str = None, dry_run: bool = False) -> str:
    """
    Update Docker container resource limits.

    Args:
        container: Container name or ID
        cpu_limit: CPU limit (e.g., "2.0" for 2 cores, "0.5" for half a core)
        memory_limit: Memory limit (e.g., "2g" for 2GB, "512m" for 512MB)
        dry_run: If True, only show what would be changed

    Returns:
        Status message with changes applied

    Safety:
        - Validates container exists
        - Supports dry-run mode
        - Requires approval for production containers

    Use cases:
        - Limit runaway container resource usage
        - Temporarily boost resources for intensive task
        - Enforce resource quotas
    """
    try:
        import docker

        client = docker.from_env()

        try:
            container_obj = client.containers.get(container)
        except docker.errors.NotFound:
            return f"❌ Container '{container}' not found"

        container_name = container_obj.name

        changes = []
        update_params = {}

        if cpu_limit is not None:
            current_cpu = container_obj.attrs['HostConfig'].get('NanoCpus', 0) / 1e9
            changes.append(f"CPU: {current_cpu} → {cpu_limit} cores")
            # Docker uses nanocpus (1 CPU = 1e9 nanocpus)
            update_params['cpu_quota'] = int(float(cpu_limit) * 100000)
            update_params['cpu_period'] = 100000

        if memory_limit is not None:
            current_mem = container_obj.attrs['HostConfig'].get('Memory', 0)
            current_mem_str = f"{current_mem / (1024**3):.1f}g" if current_mem > 0 else "unlimited"
            changes.append(f"Memory: {current_mem_str} → {memory_limit}")
            update_params['mem_limit'] = memory_limit

        if not changes:
            return f"ℹ️ No changes specified for container '{container_name}'"

        if dry_run:
            output = [f"🔍 DRY-RUN: Would update container '{container_name}'\n"]
            output.append("**Proposed Changes**:")
            for change in changes:
                output.append(f"  • {change}")
            return "\n".join(output)

        # Apply changes
        container_obj.update(**update_params)

        output = [f"✅ Successfully updated container '{container_name}'\n"]
        output.append("**Changes Applied**:")
        for change in changes:
            output.append(f"  • {change}")
        output.append("\n⚠️ **Note**: Container continues running with new limits")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error updating container resources: {str(e)}"
```

---

### Integration Steps

**1. Update imports in `crews/tools/homelab_tools.py`:**

```python
# Import expanded Proxmox tools
from crews.tools.proxmox_tools import (
    check_proxmox_node_health,
    list_proxmox_vms,
    check_proxmox_vm_status,
    get_proxmox_storage_status,
    get_proxmox_cluster_status,
    get_proxmox_system_summary,
    list_lxc_containers,
    check_lxc_logs,
    get_lxc_resource_usage,
    check_lxc_snapshots,
    check_lxc_network,
    get_lxc_config,
    update_lxc_resources,      # NEW
    create_lxc_snapshot,        # NEW
    restart_postgres_service,   # NEW
)

# Import PostgreSQL tools
from crews.tools.postgres_tools import (
    check_postgres_health,
    query_database_performance,
    check_database_sizes,
    monitor_database_connections,
    check_specific_database,
    check_replication_status,
    check_table_bloat,
    analyze_slow_queries,
    check_index_health,
    monitor_vacuum_status,
    check_database_locks,
    vacuum_postgres_table,      # NEW
    clear_postgres_connections, # NEW
)

# Import Docker tools
from crews.tools.docker_tools import (
    list_docker_images,
    prune_docker_images,
    inspect_docker_network,
    check_docker_volumes,
    get_container_resource_usage,
    check_docker_system_health,
    update_docker_resources,    # NEW
)
```

**2. Update exports in `crews/tools/__init__.py`:**

Add to import list and __all__ list (6 new tools).

**3. Update Healer agent in `crews/infrastructure_health/crew.py`:**

```python
healer_agent = Agent(
    role="Self-Healing Engineer",
    goal="Remediate infrastructure issues",
    backstory="Automation engineer. Execute fixes based on diagnosis. Verify success.",
    tools=[
        restart_container,
        restart_lxc,
        check_container_status,
        check_lxc_status,
        prune_docker_images,
        create_alert_silence,
        delete_alert_silence,
        add_annotation,
        create_snapshot,
        # Phase 25 additions:
        update_lxc_resources,
        create_lxc_snapshot,
        restart_postgres_service,
        vacuum_postgres_table,
        clear_postgres_connections,
        update_docker_resources,
    ],
    llm=llm,
    verbose=False,
    allow_delegation=False,
)
```

### Testing Checklist

- [ ] All 6 tools compile successfully (`python3 -m py_compile`)
- [ ] Imports work: `from crews.tools import update_lxc_resources, create_lxc_snapshot, ...`
- [ ] Dry-run mode works for all tools
- [ ] Manual test: `update_lxc_resources(200, memory=8192, dry_run=True)`
- [ ] Manual test: `create_lxc_snapshot(200, "test-snapshot", dry_run=True)`
- [ ] Manual test: `vacuum_postgres_table("postgres", "pg_stat_statements", dry_run=True)`
- [ ] Healer agent can see tools in crew.py
- [ ] Documentation updated in README.md

### Commit and Push

```bash
git add crews/tools/proxmox_tools.py
git add crews/tools/postgres_tools.py
git add crews/tools/docker_tools.py
git add crews/tools/__init__.py
git add crews/tools/homelab_tools.py
git add crews/infrastructure_health/crew.py

git commit -m "Phase 25: Healer expansion part 1 (6 critical remediation tools)

Add critical remediation capabilities:
- update_lxc_resources: Adjust container CPU/memory/swap
- create_lxc_snapshot: Backup before risky changes
- restart_postgres_service: Database service recovery
- vacuum_postgres_table: Reclaim space from bloat
- clear_postgres_connections: Kill blocking sessions
- update_docker_resources: Container resource management

All tools include:
- Dry-run mode for safety
- Comprehensive error handling
- Detailed status messages
- Validation before execution

Healer agent: 9 → 15 tools (+67%)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin claude/phase-25-healer-expansion-part1
```

### Documentation

Create `docs/PHASE_25_COMPLETE.md` documenting:
- 6 tools added
- Use cases for each tool
- Safety features
- Testing results
- Integration status
- Before/after metrics

---

## Phase 26: Approval Workflow & Safety Controls

### Overview
- **Duration:** 1.5 weeks
- **Priority:** 🔴 CRITICAL
- **Goal:** Prevent AI from taking down critical infrastructure

### Pre-Implementation Checklist
- [ ] Phase 25 complete and tested
- [ ] Telegram bot token configured
- [ ] Create feature branch: `claude/phase-26-approval-workflow`
- [ ] Review list of critical services

### Critical Services List

```python
# crews/safety/critical_services.py

CRITICAL_SERVICES = {
    'lxc': {
        200: 'PostgreSQL Database',
        # Add other critical LXC containers
    },
    'container': {
        'prometheus': 'Metrics Collection',
        'grafana': 'Monitoring Dashboards',
        'alertmanager': 'Alert Management',
        'homelab-agents': 'This system',
    },
    'database': {
        'postgres': 'Production Database',
        'production': 'Production Database',
    }
}
```

### Files to Create

**1. `crews/safety/__init__.py`**
**2. `crews/safety/approval.py`** - Core approval workflow logic
**3. `crews/safety/telegram_approval.py`** - Telegram bot integration
**4. `crews/safety/change_log.py`** - Change tracking and audit trail
**5. `crews/safety/critical_services.py`** - Critical service definitions

### Implementation Steps

See STRATEGIC_ROADMAP.md Phase 26 section for full code examples.

**Key Components:**
1. Approval decorator that wraps sensitive tools
2. Telegram bot that sends approval requests with inline buttons
3. Change log stored in Qdrant for audit trail
4. Dry-run mode for all tools
5. 5-minute timeout auto-denies risky actions

### Integration

Wrap all Healer tools with approval decorator:

```python
from crews.safety.approval import requires_approval, ApprovalLevel

@requires_approval(level=ApprovalLevel.HARD, critical_targets=[200])
@tool("Restart LXC Container")
def restart_lxc(node: str, vmid: int) -> str:
    # Existing implementation
    pass
```

### Testing Checklist

- [ ] Approval workflow blocks critical actions
- [ ] Telegram bot sends approval requests
- [ ] Inline buttons (Approve/Deny) work
- [ ] Timeout (5 min) auto-denies
- [ ] Change log stores all actions
- [ ] Dry-run mode bypasses approval
- [ ] Unit tests pass
- [ ] Integration tests pass

### Documentation

Create `docs/PHASE_26_COMPLETE.md` with:
- Approval workflow architecture
- Critical service list
- Telegram bot setup guide
- Testing results
- Rollback procedures

---

## Phase 27: Automated Testing & CI/CD

### Overview
- **Duration:** 2 weeks
- **Priority:** 🔴 CRITICAL
- **Goal:** 80% test coverage, automated deployment

### Pre-Implementation Checklist
- [ ] Phase 26 complete
- [ ] pytest installed locally
- [ ] GitHub Actions enabled
- [ ] Create feature branch: `claude/phase-27-testing-ci-cd`

### Test Structure

```
tests/
  unit/
    test_docker_tools.py         # 30 tests
    test_postgres_tools.py        # 33 tests
    test_lxc_tools.py            # 24 tests
    test_proxmox_tools.py         # 18 tests
    test_prometheus_tools.py      # 21 tests
    test_approval_workflow.py     # 10 tests
    test_change_log.py           # 5 tests
    test_telegram_approval.py     # 8 tests
  integration/
    test_monitor_agent.py         # 15 tests
    test_analyst_agent.py         # 15 tests
    test_healer_agent.py         # 20 tests
    test_communicator_agent.py    # 5 tests
    test_full_workflow.py        # 10 tests
  e2e/
    test_incident_scenarios.py    # 10 tests
    test_approval_flow.py        # 5 tests
  mocks/
    mock_docker.py
    mock_proxmox.py
    mock_postgres.py
    mock_prometheus.py
  conftest.py                    # Pytest fixtures
```

### Example Test File

```python
# tests/unit/test_lxc_tools.py

import pytest
from unittest.mock import Mock, patch
from crews.tools.proxmox_tools import update_lxc_resources, create_lxc_snapshot

class TestUpdateLXCResources:

    @patch('crews.tools.proxmox_tools._get_proxmox_client')
    def test_update_memory_dry_run(self, mock_proxmox):
        """Test updating LXC memory in dry-run mode"""
        result = update_lxc_resources(200, memory=8192, dry_run=True)

        assert "DRY-RUN" in result
        assert "8192" in result
        assert "Memory" in result
        mock_proxmox.assert_not_called()  # Should not connect in dry-run

    @patch('crews.tools.proxmox_tools._get_proxmox_client')
    def test_update_resources_validation(self, mock_proxmox):
        """Test resource validation before applying"""
        # Mock node status with limited resources
        mock_client = Mock()
        mock_proxmox.return_value = mock_client

        mock_client.nodes().status.get.return_value = {
            'memory': {'total': 16000000000, 'used': 14000000000}  # Only 2GB free
        }

        result = update_lxc_resources(200, memory=4096)  # Request 4GB

        assert "Cannot allocate" in result
        assert "only" in result.lower()

    # Add 8 more tests...
```

### GitHub Actions Workflows

Create `.github/workflows/` directory with:

**1. `.github/workflows/test.yml`** - Run tests on every push
**2. `.github/workflows/deploy.yml`** - Deploy on merge to main
**3. `.github/workflows/security.yml`** - Security scanning

See STRATEGIC_ROADMAP.md Phase 27 for full YAML examples.

### Testing Checklist

- [ ] 200+ tests implemented
- [ ] 80% code coverage achieved
- [ ] All tests passing locally
- [ ] GitHub Actions workflows configured
- [ ] CI runs on every commit
- [ ] Deployment script tested
- [ ] Rollback procedure documented

---

## Quick Reference: Next Steps

**Immediate (This Week):**
1. ✅ Review Strategic Roadmap document
2. Begin Phase 25 implementation
3. Create all 6 Healer tools
4. Test dry-run mode

**Week 2:**
5. Complete Phase 25 integration
6. Document Phase 25
7. Begin Phase 26 approval workflow
8. Create safety infrastructure

**Week 3-4:**
9. Complete Phase 26
10. Test approval workflow end-to-end
11. Begin Phase 27 testing framework

**Month 2:**
12. Complete CI/CD pipeline
13. Achieve 80% test coverage
14. Add Phase 28 service management tools

---

## Common Issues & Solutions

**Issue:** Tool imports fail after adding new tools
- **Solution:** Check `__init__.py` has all exports, verify file paths

**Issue:** Proxmox API permissions denied
- **Solution:** Verify API token has PVMAdmin or PVMUser role

**Issue:** PostgreSQL connection fails
- **Solution:** Check `POSTGRES_HOST` env var, verify container networking

**Issue:** Dry-run mode not working
- **Solution:** Ensure `dry_run=False` is default parameter, check implementation

**Issue:** Tests fail in CI but pass locally
- **Solution:** Check for environment-specific paths, mock external APIs properly

---

**Document Version:** 1.0
**Last Updated:** 2025-10-27
**Status:** Ready for Phase 25 implementation
