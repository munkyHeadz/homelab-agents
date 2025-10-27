"""Expanded Proxmox monitoring tools for AI agents."""

import os
from crewai.tools import tool
from proxmoxer import ProxmoxAPI
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Proxmox Configuration
PROXMOX_HOST = os.getenv("PROXMOX_HOST", "192.168.1.99")
PROXMOX_PORT = os.getenv("PROXMOX_PORT", "8006")
PROXMOX_USER = os.getenv("PROXMOX_USER", "root@pam")
PROXMOX_TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID", "root@pam!full-access")
PROXMOX_TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET", "")
PROXMOX_NODE = os.getenv("PROXMOX_NODE", "fjeld")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"


def _get_proxmox_client() -> ProxmoxAPI:
    """
    Get authenticated Proxmox API client.

    Returns:
        ProxmoxAPI client instance

    Raises:
        Exception: If connection or authentication fails
    """
    try:
        # Extract token name and user from token_id
        if "!" in PROXMOX_TOKEN_ID:
            token_user, token_name = PROXMOX_TOKEN_ID.split("!")
        else:
            raise Exception("Invalid PROXMOX_TOKEN_ID format. Expected format: user@realm!tokenname")

        proxmox = ProxmoxAPI(
            PROXMOX_HOST,
            user=token_user,
            token_name=token_name,
            token_value=PROXMOX_TOKEN_SECRET,
            verify_ssl=PROXMOX_VERIFY_SSL,
            port=int(PROXMOX_PORT)
        )

        # Test connection
        proxmox.version.get()
        return proxmox

    except Exception as e:
        raise Exception(f"Failed to connect to Proxmox at {PROXMOX_HOST}:{PROXMOX_PORT}: {str(e)}")


@tool("Check Proxmox Node Health")
def check_proxmox_node_health(node: Optional[str] = None) -> str:
    """
    Check the health and resource usage of Proxmox node(s).

    Args:
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with node health information including:
        - Node status (online/offline)
        - CPU usage percentage
        - Memory usage (used/total)
        - Storage usage
        - Uptime
        - Load average
        - PVE version

    Use cases:
    - Monitor node resource utilization
    - Detect node overload
    - Track node availability
    - Capacity planning
    - Performance troubleshooting
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        node_status = proxmox.nodes(target_node).status.get()

        output = [f"🖥️ Proxmox Node: **{target_node}**\n"]

        # Overall status
        status = node_status.get('status', 'unknown')
        if status == 'online':
            output.append("**Status**: ✅ Online")
        else:
            output.append(f"**Status**: ❌ {status.title()}")

        # PVE Version
        pve_version = node_status.get('pveversion', 'Unknown')
        output.append(f"**Version**: {pve_version}")

        # Uptime
        uptime_seconds = node_status.get('uptime', 0)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        output.append(f"**Uptime**: {days}d {hours}h")

        # CPU Usage
        cpu_usage = node_status.get('cpu', 0) * 100
        cpu_count = node_status.get('cpuinfo', {}).get('cpus', 0)

        if cpu_usage > 90:
            cpu_emoji = "🔴"
        elif cpu_usage > 70:
            cpu_emoji = "⚠️"
        else:
            cpu_emoji = "✅"

        output.append(f"\n**CPU Usage**: {cpu_emoji} {cpu_usage:.1f}% ({cpu_count} cores)")

        # Memory Usage
        memory_info = node_status.get('memory', {})
        mem_used = memory_info.get('used', 0) / (1024**3)  # Convert to GB
        mem_total = memory_info.get('total', 1) / (1024**3)
        mem_percentage = (memory_info.get('used', 0) / memory_info.get('total', 1)) * 100 if memory_info.get('total', 1) > 0 else 0

        if mem_percentage > 90:
            mem_emoji = "🔴"
        elif mem_percentage > 70:
            mem_emoji = "⚠️"
        else:
            mem_emoji = "✅"

        output.append(f"**Memory Usage**: {mem_emoji} {mem_used:.1f}GB / {mem_total:.1f}GB ({mem_percentage:.1f}%)")

        # Storage (root filesystem)
        rootfs = node_status.get('rootfs', {})
        storage_used = rootfs.get('used', 0) / (1024**3)
        storage_total = rootfs.get('total', 1) / (1024**3)
        storage_percentage = (rootfs.get('used', 0) / rootfs.get('total', 1)) * 100 if rootfs.get('total', 1) > 0 else 0

        if storage_percentage > 90:
            storage_emoji = "🔴"
        elif storage_percentage > 80:
            storage_emoji = "⚠️"
        else:
            storage_emoji = "✅"

        output.append(f"**Storage (root)**: {storage_emoji} {storage_used:.1f}GB / {storage_total:.1f}GB ({storage_percentage:.1f}%)")

        # Load Average
        loadavg = node_status.get('loadavg', [0, 0, 0])
        output.append(f"**Load Average**: {loadavg[0]:.2f}, {loadavg[1]:.2f}, {loadavg[2]:.2f}")

        # Warnings
        warnings = []
        if cpu_usage > 80:
            warnings.append("⚠️ High CPU usage")
        if mem_percentage > 80:
            warnings.append("⚠️ High memory usage")
        if storage_percentage > 80:
            warnings.append("⚠️ High storage usage")

        if warnings:
            output.append("\n**Warnings**:")
            for warning in warnings:
                output.append(f"  {warning}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking Proxmox node health: {str(e)}"


@tool("List Proxmox Virtual Machines")
def list_proxmox_vms(node: Optional[str] = None, status_filter: Optional[str] = None) -> str:
    """
    List all virtual machines (VMs) on Proxmox node.

    Args:
        node: Optional specific node name. If None, uses configured node.
        status_filter: Optional filter by status (running, stopped, paused)

    Returns:
        Formatted string with VM information including:
        - VM ID and name
        - Status (running/stopped/paused)
        - CPU cores and usage
        - Memory allocation and usage
        - Uptime (for running VMs)

    Use cases:
    - Inventory all VMs
    - Check VM status
    - Monitor VM resource usage
    - Identify stopped or paused VMs
    - Troubleshoot VM issues
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        vms = proxmox.nodes(target_node).qemu.get()

        if status_filter:
            vms = [vm for vm in vms if vm.get('status', '').lower() == status_filter.lower()]

        if not vms:
            return f"ℹ️ No VMs found on node {target_node}" + (f" with status '{status_filter}'" if status_filter else "")

        output = [f"🖥️ Proxmox Virtual Machines on **{target_node}** ({len(vms)} total)\n"]

        # Group by status
        running = [vm for vm in vms if vm.get('status') == 'running']
        stopped = [vm for vm in vms if vm.get('status') == 'stopped']
        other = [vm for vm in vms if vm.get('status') not in ['running', 'stopped']]

        output.append(f"**Running**: {len(running)} | **Stopped**: {len(stopped)}" + (f" | **Other**: {len(other)}" if other else ""))

        # Show running VMs first
        if running:
            output.append("\n**Running VMs**:")
            for vm in sorted(running, key=lambda x: x.get('vmid', 0)):
                vmid = vm.get('vmid', 'Unknown')
                name = vm.get('name', 'Unknown')
                cpu_usage = vm.get('cpu', 0) * 100
                mem_usage = vm.get('mem', 0) / (1024**3) if vm.get('mem') else 0
                mem_max = vm.get('maxmem', 0) / (1024**3) if vm.get('maxmem') else 0
                cpus = vm.get('cpus', 0)
                uptime = vm.get('uptime', 0)

                uptime_str = f"{uptime // 3600}h" if uptime > 0 else "Starting"

                output.append(f"\n  ✅ **VM {vmid}**: {name}")
                output.append(f"     CPU: {cpu_usage:.1f}% ({cpus} cores) | RAM: {mem_usage:.1f}/{mem_max:.1f}GB")
                output.append(f"     Uptime: {uptime_str}")

        # Show stopped VMs
        if stopped:
            output.append("\n**Stopped VMs**:")
            for vm in sorted(stopped, key=lambda x: x.get('vmid', 0)):
                vmid = vm.get('vmid', 'Unknown')
                name = vm.get('name', 'Unknown')
                cpus = vm.get('cpus', 0)
                mem_max = vm.get('maxmem', 0) / (1024**3) if vm.get('maxmem') else 0

                output.append(f"  ⏹️ **VM {vmid}**: {name} (CPU: {cpus} cores, RAM: {mem_max:.1f}GB)")

        # Show other status VMs
        if other:
            output.append("\n**Other Status VMs**:")
            for vm in sorted(other, key=lambda x: x.get('vmid', 0)):
                vmid = vm.get('vmid', 'Unknown')
                name = vm.get('name', 'Unknown')
                status = vm.get('status', 'unknown')

                output.append(f"  ⚠️ **VM {vmid}**: {name} - Status: {status}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error listing Proxmox VMs: {str(e)}"


@tool("Check Proxmox VM Status")
def check_proxmox_vm_status(vmid: int, node: Optional[str] = None) -> str:
    """
    Check detailed status of a specific Proxmox virtual machine.

    Args:
        vmid: VM ID to check
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with detailed VM information including:
        - Status (running/stopped/paused)
        - CPU usage and allocation
        - Memory usage and allocation
        - Disk usage
        - Network interfaces and traffic
        - Uptime
        - OS type and version

    Use cases:
    - Detailed VM health check
    - Troubleshoot specific VM
    - Monitor VM resources
    - Verify VM configuration
    - Performance analysis
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        vm_status = proxmox.nodes(target_node).qemu(vmid).status.current.get()
        vm_config = proxmox.nodes(target_node).qemu(vmid).config.get()

        output = [f"🖥️ VM {vmid} Status\n"]

        name = vm_config.get('name', 'Unknown')
        output.append(f"**Name**: {name}")

        # Status
        status = vm_status.get('status', 'unknown')
        if status == 'running':
            output.append(f"**Status**: ✅ Running")
        elif status == 'stopped':
            output.append(f"**Status**: ⏹️ Stopped")
        else:
            output.append(f"**Status**: ⚠️ {status.title()}")

        # Only show runtime stats if running
        if status == 'running':
            # Uptime
            uptime = vm_status.get('uptime', 0)
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            minutes = (uptime % 3600) // 60
            output.append(f"**Uptime**: {days}d {hours}h {minutes}m")

            # CPU
            cpu_usage = vm_status.get('cpu', 0) * 100
            cpus = vm_status.get('cpus', 0)
            output.append(f"\n**CPU**: {cpu_usage:.1f}% ({cpus} cores)")

            # Memory
            mem_used = vm_status.get('mem', 0) / (1024**3)
            mem_max = vm_status.get('maxmem', 0) / (1024**3)
            mem_percentage = (vm_status.get('mem', 0) / vm_status.get('maxmem', 1)) * 100 if vm_status.get('maxmem', 1) > 0 else 0
            output.append(f"**Memory**: {mem_used:.1f}GB / {mem_max:.1f}GB ({mem_percentage:.1f}%)")

            # Disk I/O
            disk_read = vm_status.get('diskread', 0) / (1024**2)  # MB
            disk_write = vm_status.get('diskwrite', 0) / (1024**2)  # MB
            output.append(f"**Disk I/O**: Read: {disk_read:.1f}MB | Write: {disk_write:.1f}MB")

            # Network I/O
            net_in = vm_status.get('netin', 0) / (1024**2)  # MB
            net_out = vm_status.get('netout', 0) / (1024**2)  # MB
            output.append(f"**Network I/O**: In: {net_in:.1f}MB | Out: {net_out:.1f}MB")
        else:
            # Configuration for stopped VM
            cpus = vm_config.get('cores', 0)
            mem_max = vm_config.get('memory', 0) / 1024  # GB
            output.append(f"\n**Configuration**: {cpus} cores, {mem_max:.1f}GB RAM")

        # OS Type
        ostype = vm_config.get('ostype', 'Unknown')
        output.append(f"**OS Type**: {ostype}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking VM {vmid} status: {str(e)}"


@tool("Get Proxmox Storage Status")
def get_proxmox_storage_status(node: Optional[str] = None) -> str:
    """
    Get storage status and usage across all storage pools.

    Args:
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with storage information including:
        - Storage pool names and types
        - Total capacity and used space
        - Available space
        - Usage percentage
        - Storage health warnings

    Use cases:
    - Monitor storage capacity
    - Detect low storage space
    - Plan storage expansion
    - Track storage growth
    - Troubleshoot storage issues
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        storages = proxmox.nodes(target_node).storage.get()

        if not storages:
            return f"ℹ️ No storage found on node {target_node}"

        output = [f"💾 Storage Status on **{target_node}** ({len(storages)} pools)\n"]

        total_used = 0
        total_capacity = 0
        warnings = []

        for storage in sorted(storages, key=lambda x: x.get('storage', '')):
            storage_name = storage.get('storage', 'Unknown')
            storage_type = storage.get('type', 'Unknown')

            # Only process active storage
            if storage.get('active', 0) != 1:
                continue

            used = storage.get('used', 0) / (1024**3)  # GB
            total = storage.get('total', 1) / (1024**3)  # GB
            avail = storage.get('avail', 0) / (1024**3)  # GB
            percentage = (storage.get('used', 0) / storage.get('total', 1)) * 100 if storage.get('total', 1) > 0 else 0

            total_used += used
            total_capacity += total

            # Status emoji based on usage
            if percentage > 90:
                emoji = "🔴"
                warnings.append(f"{storage_name} ({percentage:.1f}% full)")
            elif percentage > 80:
                emoji = "⚠️"
            else:
                emoji = "✅"

            output.append(f"{emoji} **{storage_name}** ({storage_type})")
            output.append(f"  Used: {used:.1f}GB / {total:.1f}GB ({percentage:.1f}%)")
            output.append(f"  Available: {avail:.1f}GB\n")

        # Summary
        overall_percentage = (total_used / total_capacity * 100) if total_capacity > 0 else 0
        output.append(f"**Total**: {total_used:.1f}GB / {total_capacity:.1f}GB ({overall_percentage:.1f}%)")

        # Warnings
        if warnings:
            output.append("\n**⚠️ Storage Warnings**:")
            for warning in warnings:
                output.append(f"  • {warning}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting storage status: {str(e)}"


@tool("Get Proxmox Cluster Status")
def get_proxmox_cluster_status() -> str:
    """
    Get Proxmox cluster status and node list.

    Returns:
        Formatted string with cluster information including:
        - Cluster name
        - Number of nodes
        - Node statuses (online/offline)
        - Quorum status
        - Cluster health

    Note: Returns single-node status if not in a cluster.

    Use cases:
    - Monitor cluster health
    - Verify quorum
    - Check node connectivity
    - Troubleshoot cluster issues
    - Detect split-brain scenarios
    """
    try:
        proxmox = _get_proxmox_client()

        # Try to get cluster status
        try:
            cluster_status = proxmox.cluster.status.get()

            output = ["🔗 Proxmox Cluster Status\n"]

            nodes = [item for item in cluster_status if item.get('type') == 'node']
            quorum_item = next((item for item in cluster_status if item.get('type') == 'cluster'), None)

            if quorum_item:
                cluster_name = quorum_item.get('name', 'Unknown')
                quorum = quorum_item.get('quorate', 0)

                output.append(f"**Cluster**: {cluster_name}")
                output.append(f"**Quorum**: {'✅ Yes' if quorum else '❌ No'}")
                output.append(f"**Nodes**: {len(nodes)}\n")

                # Node statuses
                for node in sorted(nodes, key=lambda x: x.get('name', '')):
                    node_name = node.get('name', 'Unknown')
                    online = node.get('online', 0)
                    local = node.get('local', 0)

                    status_emoji = "✅" if online else "❌"
                    local_str = " (local)" if local else ""

                    output.append(f"{status_emoji} **{node_name}**{local_str}")

                if not quorum:
                    output.append("\n⚠️ **Warning**: Cluster has lost quorum!")
            else:
                output.append("**Cluster**: Not configured (single node)")
                output.append(f"**Node**: {PROXMOX_NODE}")

            return "\n".join(output)

        except:
            # Not in a cluster
            return f"🖥️ Proxmox Single Node\n\n**Node**: {PROXMOX_NODE}\n**Status**: ✅ Standalone (not clustered)"

    except Exception as e:
        return f"❌ Error getting cluster status: {str(e)}"


@tool("Get Proxmox System Summary")
def get_proxmox_system_summary(node: Optional[str] = None) -> str:
    """
    Get comprehensive summary of Proxmox system status.

    Args:
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with system summary including:
        - Node health overview
        - VM count and status
        - LXC count and status
        - Storage usage summary
        - Resource utilization
        - Any warnings or issues

    Use cases:
    - Quick system health check
    - Dashboard overview
    - Incident detection
    - Status reporting
    - Capacity planning
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        output = [f"📊 Proxmox System Summary: **{target_node}**\n"]

        # Node Status
        node_status = proxmox.nodes(target_node).status.get()
        cpu_usage = node_status.get('cpu', 0) * 100
        mem_usage = (node_status.get('memory', {}).get('used', 0) / node_status.get('memory', {}).get('total', 1)) * 100 if node_status.get('memory', {}).get('total', 1) > 0 else 0

        if cpu_usage > 80 or mem_usage > 80:
            node_health = "⚠️ Under Load"
        else:
            node_health = "✅ Healthy"

        output.append(f"**Node Health**: {node_health}")
        output.append(f"  CPU: {cpu_usage:.1f}% | Memory: {mem_usage:.1f}%")

        # VMs
        vms = proxmox.nodes(target_node).qemu.get()
        vm_running = len([vm for vm in vms if vm.get('status') == 'running'])
        vm_stopped = len([vm for vm in vms if vm.get('status') == 'stopped'])

        output.append(f"\n**Virtual Machines**: {len(vms)} total")
        output.append(f"  Running: {vm_running} | Stopped: {vm_stopped}")

        # LXCs
        lxcs = proxmox.nodes(target_node).lxc.get()
        lxc_running = len([lxc for lxc in lxcs if lxc.get('status') == 'running'])
        lxc_stopped = len([lxc for lxc in lxcs if lxc.get('status') == 'stopped'])

        output.append(f"\n**LXC Containers**: {len(lxcs)} total")
        output.append(f"  Running: {lxc_running} | Stopped: {lxc_stopped}")

        # Storage
        storages = proxmox.nodes(target_node).storage.get()
        active_storage = [s for s in storages if s.get('active', 0) == 1]

        total_used = sum(s.get('used', 0) for s in active_storage) / (1024**3)
        total_capacity = sum(s.get('total', 0) for s in active_storage) / (1024**3)
        storage_percentage = (total_used / total_capacity * 100) if total_capacity > 0 else 0

        if storage_percentage > 80:
            storage_health = "⚠️"
        else:
            storage_health = "✅"

        output.append(f"\n**Storage**: {storage_health} {len(active_storage)} pools")
        output.append(f"  Used: {total_used:.1f}GB / {total_capacity:.1f}GB ({storage_percentage:.1f}%)")

        # Overall Assessment
        issues = []
        if cpu_usage > 80:
            issues.append("High CPU usage")
        if mem_usage > 80:
            issues.append("High memory usage")
        if storage_percentage > 80:
            issues.append("High storage usage")
        if vm_stopped > 0 or lxc_stopped > 0:
            issues.append(f"{vm_stopped + lxc_stopped} stopped VM/containers")

        if issues:
            output.append("\n**⚠️ Issues Detected**:")
            for issue in issues:
                output.append(f"  • {issue}")
        else:
            output.append("\n✅ **All systems operational**")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting system summary: {str(e)}"

@tool("List LXC Containers")
def list_lxc_containers(node: Optional[str] = None, status_filter: Optional[str] = None) -> str:
    """
    List all LXC containers on Proxmox node.

    Args:
        node: Optional specific node name. If None, uses configured node.
        status_filter: Optional filter by status (running, stopped, paused)

    Returns:
        Formatted string with LXC container information including:
        - Container ID and name
        - Status (running/stopped/paused)
        - CPU cores and usage
        - Memory allocation and usage
        - Uptime (for running containers)
        - Root filesystem usage

    Use cases:
    - Inventory all LXC containers
    - Check container status quickly
    - Monitor container resource usage
    - Identify stopped or problematic containers
    - Compare with Docker containers
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        lxcs = proxmox.nodes(target_node).lxc.get()

        if status_filter:
            lxcs = [lxc for lxc in lxcs if lxc.get('status', '').lower() == status_filter.lower()]

        if not lxcs:
            return f"ℹ️ No LXC containers found on node {target_node}" + (f" with status '{status_filter}'" if status_filter else "")

        output = [f"📦 LXC Containers on **{target_node}** ({len(lxcs)} total)\n"]

        # Group by status
        running = [lxc for lxc in lxcs if lxc.get('status') == 'running']
        stopped = [lxc for lxc in lxcs if lxc.get('status') == 'stopped']
        other = [lxc for lxc in lxcs if lxc.get('status') not in ['running', 'stopped']]

        output.append(f"**Running**: {len(running)} | **Stopped**: {len(stopped)}" + (f" | **Other**: {len(other)}" if other else ""))

        # Show running containers first
        if running:
            output.append("\n**Running Containers**:")
            for lxc in sorted(running, key=lambda x: x.get('vmid', 0)):
                vmid = lxc.get('vmid', 'Unknown')
                name = lxc.get('name', 'Unknown')
                cpu_usage = lxc.get('cpu', 0) * 100
                mem_usage = lxc.get('mem', 0) / (1024**3) if lxc.get('mem') else 0
                mem_max = lxc.get('maxmem', 0) / (1024**3) if lxc.get('maxmem') else 0
                cpus = lxc.get('cpus', 0)
                uptime = lxc.get('uptime', 0)

                uptime_str = f"{uptime // 86400}d {(uptime % 86400) // 3600}h" if uptime > 0 else "Starting"

                output.append(f"\n  ✅ **LXC {vmid}**: {name}")
                output.append(f"     CPU: {cpu_usage:.1f}% ({cpus} cores) | RAM: {mem_usage:.1f}/{mem_max:.1f}GB")
                output.append(f"     Uptime: {uptime_str}")

        # Show stopped containers
        if stopped:
            output.append("\n**Stopped Containers**:")
            for lxc in sorted(stopped, key=lambda x: x.get('vmid', 0)):
                vmid = lxc.get('vmid', 'Unknown')
                name = lxc.get('name', 'Unknown')
                cpus = lxc.get('cpus', 0)
                mem_max = lxc.get('maxmem', 0) / (1024**3) if lxc.get('maxmem') else 0

                output.append(f"  ⏹️ **LXC {vmid}**: {name} (CPU: {cpus} cores, RAM: {mem_max:.1f}GB)")

        # Show other status containers
        if other:
            output.append("\n**Other Status Containers**:")
            for lxc in sorted(other, key=lambda x: x.get('vmid', 0)):
                vmid = lxc.get('vmid', 'Unknown')
                name = lxc.get('name', 'Unknown')
                status = lxc.get('status', 'unknown')

                output.append(f"  ⚠️ **LXC {vmid}**: {name} - Status: {status}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error listing LXC containers: {str(e)}"


@tool("Check LXC Container Logs")
def check_lxc_logs(vmid: int, node: Optional[str] = None, lines: int = 50) -> str:
    """
    Retrieve recent log entries from an LXC container.

    Args:
        vmid: LXC container ID
        node: Optional specific node name. If None, uses configured node.
        lines: Number of log lines to retrieve (default: 50, max: 200)

    Returns:
        Formatted string with recent container log entries from syslog

    Use cases:
    - Troubleshoot container startup issues
    - Investigate application errors
    - Monitor container activity
    - Debug service failures
    - Check for security events
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        # Limit lines to prevent excessive output
        lines = min(lines, 200)

        # Get container status first
        lxc_status = proxmox.nodes(target_node).lxc(vmid).status.current.get()
        status = lxc_status.get('status', 'unknown')
        name = lxc_status.get('name', f'LXC {vmid}')

        if status != 'running':
            return f"⚠️ Container {vmid} ({name}) is {status}. Cannot retrieve logs from stopped container.\n\nTip: Use Proxmox syslog or check task logs for startup issues."

        # Execute command to get logs from container
        try:
            # Read syslog from container
            log_result = proxmox.nodes(target_node).lxc(vmid).log.get(limit=lines)
            
            if not log_result:
                return f"ℹ️ No logs available for container {vmid} ({name})"

            output = [f"📜 LXC Container {vmid} ({name}) - Last {lines} log entries\n"]
            
            # Parse log entries
            for entry in log_result[-lines:]:
                line_num = entry.get('n', '')
                text = entry.get('t', '')
                output.append(f"{line_num}: {text}")

            return "\n".join(output)

        except Exception as log_err:
            # Fallback to rrddata or status info if logs unavailable
            return f"⚠️ Unable to retrieve container logs: {str(log_err)}\n\nContainer {vmid} ({name}) is {status}. Logs may not be available through API."

    except Exception as e:
        return f"❌ Error checking LXC logs for container {vmid}: {str(e)}"


@tool("Get LXC Resource Usage")
def get_lxc_resource_usage(vmid: int, node: Optional[str] = None) -> str:
    """
    Get real-time resource usage statistics for an LXC container.

    Args:
        vmid: LXC container ID
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with detailed resource usage including:
        - CPU usage percentage and allocation
        - Memory usage (used/total/percentage)
        - Swap usage
        - Disk I/O (read/write)
        - Network I/O (in/out)
        - Root filesystem usage
        - Uptime

    Use cases:
    - Monitor container performance
    - Detect resource exhaustion
    - Identify resource-hungry containers
    - Capacity planning
    - Performance troubleshooting
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        lxc_status = proxmox.nodes(target_node).lxc(vmid).status.current.get()
        lxc_config = proxmox.nodes(target_node).lxc(vmid).config.get()

        name = lxc_config.get('hostname', f'LXC {vmid}')
        status = lxc_status.get('status', 'unknown')

        output = [f"📊 LXC Container {vmid} ({name}) - Resource Usage\n"]

        if status != 'running':
            output.append(f"**Status**: ⏹️ {status.title()}")
            output.append("\nℹ️ Container is not running. No resource usage data available.")
            
            # Show configured resources
            cpus = lxc_config.get('cores', 0)
            mem_max = lxc_config.get('memory', 0) / 1024  # GB
            swap_max = lxc_config.get('swap', 0) / 1024  # GB
            
            output.append(f"\n**Configured Resources**:")
            output.append(f"  CPU Cores: {cpus}")
            output.append(f"  Memory: {mem_max:.1f}GB")
            output.append(f"  Swap: {swap_max:.1f}GB")
            
            return "\n".join(output)

        output.append(f"**Status**: ✅ Running")

        # Uptime
        uptime = lxc_status.get('uptime', 0)
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        output.append(f"**Uptime**: {days}d {hours}h {minutes}m")

        # CPU Usage
        cpu_usage = lxc_status.get('cpu', 0) * 100
        cpus = lxc_status.get('cpus', lxc_config.get('cores', 0))

        if cpu_usage > 80:
            cpu_emoji = "🔴"
        elif cpu_usage > 60:
            cpu_emoji = "⚠️"
        else:
            cpu_emoji = "✅"

        output.append(f"\n**CPU**: {cpu_emoji} {cpu_usage:.1f}% ({cpus} cores)")

        # Memory Usage
        mem_used = lxc_status.get('mem', 0) / (1024**3)  # GB
        mem_max = lxc_status.get('maxmem', 0) / (1024**3)  # GB
        mem_percentage = (lxc_status.get('mem', 0) / lxc_status.get('maxmem', 1)) * 100 if lxc_status.get('maxmem', 1) > 0 else 0

        if mem_percentage > 90:
            mem_emoji = "🔴"
        elif mem_percentage > 75:
            mem_emoji = "⚠️"
        else:
            mem_emoji = "✅"

        output.append(f"**Memory**: {mem_emoji} {mem_used:.2f}GB / {mem_max:.2f}GB ({mem_percentage:.1f}%)")

        # Swap Usage (if available)
        swap_used = lxc_status.get('swap', 0) / (1024**3)  # GB
        max_swap = lxc_status.get('maxswap', 0) / (1024**3)  # GB
        
        if max_swap > 0:
            swap_percentage = (lxc_status.get('swap', 0) / lxc_status.get('maxswap', 1)) * 100 if lxc_status.get('maxswap', 1) > 0 else 0
            swap_emoji = "⚠️" if swap_percentage > 50 else "✅"
            output.append(f"**Swap**: {swap_emoji} {swap_used:.2f}GB / {max_swap:.2f}GB ({swap_percentage:.1f}%)")

        # Disk I/O
        disk_read = lxc_status.get('diskread', 0) / (1024**3)  # GB
        disk_write = lxc_status.get('diskwrite', 0) / (1024**3)  # GB
        output.append(f"\n**Disk I/O**: Read: {disk_read:.2f}GB | Write: {disk_write:.2f}GB")

        # Root filesystem usage
        disk_used = lxc_status.get('disk', 0) / (1024**3)  # GB
        disk_max = lxc_status.get('maxdisk', 0) / (1024**3)  # GB
        
        if disk_max > 0:
            disk_percentage = (lxc_status.get('disk', 0) / lxc_status.get('maxdisk', 1)) * 100 if lxc_status.get('maxdisk', 1) > 0 else 0
            
            if disk_percentage > 90:
                disk_emoji = "🔴"
            elif disk_percentage > 80:
                disk_emoji = "⚠️"
            else:
                disk_emoji = "✅"
            
            output.append(f"**Root FS**: {disk_emoji} {disk_used:.2f}GB / {disk_max:.2f}GB ({disk_percentage:.1f}%)")

        # Network I/O
        net_in = lxc_status.get('netin', 0) / (1024**3)  # GB
        net_out = lxc_status.get('netout', 0) / (1024**3)  # GB
        output.append(f"**Network I/O**: In: {net_in:.2f}GB | Out: {net_out:.2f}GB")

        # Resource warnings
        warnings = []
        if cpu_usage > 80:
            warnings.append("High CPU usage")
        if mem_percentage > 85:
            warnings.append("High memory usage")
        if max_swap > 0 and swap_percentage > 50:
            warnings.append("Swap being used (potential memory pressure)")
        if disk_max > 0 and disk_percentage > 85:
            warnings.append("High disk usage")

        if warnings:
            output.append("\n**⚠️ Warnings**:")
            for warning in warnings:
                output.append(f"  • {warning}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting LXC resource usage for container {vmid}: {str(e)}"


@tool("Check LXC Snapshots")
def check_lxc_snapshots(vmid: int, node: Optional[str] = None) -> str:
    """
    List and check snapshots for an LXC container.

    Args:
        vmid: LXC container ID
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with snapshot information including:
        - Snapshot names and descriptions
        - Creation timestamps
        - Snapshot sizes
        - Total number of snapshots
        - Backup status

    Use cases:
    - Verify backup schedules
    - Check snapshot availability before changes
    - Identify old snapshots for cleanup
    - Validate disaster recovery readiness
    - Monitor snapshot storage usage
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        # Get container config to check for snapshots
        lxc_config = proxmox.nodes(target_node).lxc(vmid).config.get()
        name = lxc_config.get('hostname', f'LXC {vmid}')

        # Get snapshots
        try:
            snapshots = proxmox.nodes(target_node).lxc(vmid).snapshot.get()
            
            # Filter out 'current' pseudo-snapshot
            real_snapshots = [s for s in snapshots if s.get('name') != 'current']
            
            if not real_snapshots:
                return f"ℹ️ No snapshots found for container {vmid} ({name})\n\n💡 Tip: Create snapshots before making configuration changes or updates."

            output = [f"📸 LXC Container {vmid} ({name}) - Snapshots ({len(real_snapshots)} total)\n"]

            # Sort by creation time (most recent first)
            sorted_snapshots = sorted(real_snapshots, key=lambda x: x.get('snaptime', 0), reverse=True)

            for snap in sorted_snapshots:
                snap_name = snap.get('name', 'Unknown')
                snap_desc = snap.get('description', 'No description')
                snap_time = snap.get('snaptime', 0)
                
                # Convert timestamp to readable format
                from datetime import datetime
                if snap_time:
                    snap_date = datetime.fromtimestamp(snap_time).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    snap_date = 'Unknown'

                output.append(f"📸 **{snap_name}**")
                output.append(f"   Created: {snap_date}")
                if snap_desc and snap_desc != 'No description':
                    output.append(f"   Description: {snap_desc}")
                output.append("")

            # Show backup recommendation
            if len(real_snapshots) == 0:
                output.append("⚠️ **No snapshots found** - Consider creating regular snapshots")
            elif len(real_snapshots) > 10:
                output.append(f"💡 **{len(real_snapshots)} snapshots** - Consider cleaning up old snapshots")

            return "\n".join(output)

        except Exception as snap_err:
            return f"ℹ️ No snapshots available for container {vmid} ({name}): {str(snap_err)}"

    except Exception as e:
        return f"❌ Error checking LXC snapshots for container {vmid}: {str(e)}"


@tool("Check LXC Network Configuration")
def check_lxc_network(vmid: int, node: Optional[str] = None) -> str:
    """
    Check network configuration and connectivity for an LXC container.

    Args:
        vmid: LXC container ID
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with network information including:
        - Network interfaces and configuration
        - IP addresses (IPv4 and IPv6)
        - MAC addresses
        - Bridge connections
        - Network statistics (if running)
        - Firewall settings

    Use cases:
    - Troubleshoot network connectivity
    - Verify IP address assignments
    - Check bridge configuration
    - Diagnose network isolation issues
    - Validate firewall rules
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        lxc_config = proxmox.nodes(target_node).lxc(vmid).config.get()
        lxc_status = proxmox.nodes(target_node).lxc(vmid).status.current.get()

        name = lxc_config.get('hostname', f'LXC {vmid}')
        status = lxc_status.get('status', 'unknown')

        output = [f"🌐 LXC Container {vmid} ({name}) - Network Configuration\n"]
        output.append(f"**Status**: {'✅ Running' if status == 'running' else f'⏹️ {status.title()}'}")

        # Parse network interfaces from config
        network_found = False
        
        for key, value in lxc_config.items():
            if key.startswith('net'):
                network_found = True
                # Parse network configuration (format: name=eth0,bridge=vmbr0,ip=dhcp,...)
                output.append(f"\n**Interface {key}**:")
                
                # Split configuration into key-value pairs
                config_parts = value.split(',')
                for part in config_parts:
                    if '=' in part:
                        k, v = part.split('=', 1)
                        
                        # Format common fields
                        if k == 'name':
                            output.append(f"  Name: {v}")
                        elif k == 'bridge':
                            output.append(f"  Bridge: {v}")
                        elif k == 'hwaddr':
                            output.append(f"  MAC: {v}")
                        elif k == 'ip':
                            output.append(f"  IPv4: {v}")
                        elif k == 'ip6':
                            output.append(f"  IPv6: {v}")
                        elif k == 'gw':
                            output.append(f"  Gateway: {v}")
                        elif k == 'gw6':
                            output.append(f"  Gateway6: {v}")
                        elif k == 'rate':
                            output.append(f"  Rate Limit: {v} MB/s")
                        elif k == 'tag':
                            output.append(f"  VLAN Tag: {v}")
                        elif k == 'firewall':
                            firewall_status = "✅ Enabled" if v == '1' else "❌ Disabled"
                            output.append(f"  Firewall: {firewall_status}")

        if not network_found:
            output.append("\n⚠️ No network interfaces configured")
            return "\n".join(output)

        # Show network statistics if container is running
        if status == 'running':
            net_in = lxc_status.get('netin', 0) / (1024**2)  # MB
            net_out = lxc_status.get('netout', 0) / (1024**2)  # MB
            
            output.append(f"\n**Network Statistics** (since boot):")
            output.append(f"  Received: {net_in:.2f} MB")
            output.append(f"  Transmitted: {net_out:.2f} MB")

        # Firewall status
        firewall_enabled = lxc_config.get('firewall', '0') == '1'
        output.append(f"\n**Container Firewall**: {'✅ Enabled' if firewall_enabled else '⚠️ Disabled'}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking LXC network for container {vmid}: {str(e)}"


@tool("Get LXC Container Configuration")
def get_lxc_config(vmid: int, node: Optional[str] = None) -> str:
    """
    Get and validate LXC container configuration.

    Args:
        vmid: LXC container ID
        node: Optional specific node name. If None, uses configured node.

    Returns:
        Formatted string with container configuration including:
        - Hostname and OS template
        - Resource allocations (CPU, memory, swap, disk)
        - Startup configuration (boot order, autostart)
        - Security features (unprivileged, nesting, keyctl)
        - Mount points and storage
        - Configuration warnings and recommendations

    Use cases:
    - Validate container configuration
    - Review security settings
    - Check resource allocations
    - Verify startup configuration
    - Audit container settings
    - Troubleshoot container issues
    """
    try:
        proxmox = _get_proxmox_client()
        target_node = node or PROXMOX_NODE

        lxc_config = proxmox.nodes(target_node).lxc(vmid).config.get()
        lxc_status = proxmox.nodes(target_node).lxc(vmid).status.current.get()

        hostname = lxc_config.get('hostname', f'LXC-{vmid}')
        status = lxc_status.get('status', 'unknown')

        output = [f"⚙️ LXC Container {vmid} ({hostname}) - Configuration\n"]
        output.append(f"**Status**: {'✅ Running' if status == 'running' else f'⏹️ {status.title()}'}")

        # OS Template
        ostemplate = lxc_config.get('ostemplate', 'Unknown')
        if ostemplate != 'Unknown':
            output.append(f"**OS Template**: {ostemplate}")

        # Container Type
        unprivileged = lxc_config.get('unprivileged', '0') == '1'
        container_type = "Unprivileged (Secure)" if unprivileged else "Privileged"
        security_emoji = "✅" if unprivileged else "⚠️"
        output.append(f"**Type**: {security_emoji} {container_type}")

        # Resource Allocation
        output.append(f"\n**Resource Allocation**:")
        cores = lxc_config.get('cores', 'Unlimited')
        memory = lxc_config.get('memory', 'N/A')
        if memory != 'N/A':
            memory_gb = int(memory) / 1024
            output.append(f"  CPU Cores: {cores}")
            output.append(f"  Memory: {memory_gb:.1f}GB")
        
        swap = lxc_config.get('swap', '0')
        if int(swap) > 0:
            swap_gb = int(swap) / 1024
            output.append(f"  Swap: {swap_gb:.1f}GB")
        else:
            output.append(f"  Swap: Disabled")

        # Storage
        rootfs = lxc_config.get('rootfs', '')
        if rootfs:
            # Parse rootfs (format: storage:size)
            output.append(f"\n**Root Filesystem**: {rootfs}")

        # Mount points
        mount_count = 0
        for key in lxc_config.keys():
            if key.startswith('mp'):
                mount_count += 1
        
        if mount_count > 0:
            output.append(f"**Mount Points**: {mount_count} configured")

        # Startup Configuration
        output.append(f"\n**Startup Configuration**:")
        onboot = lxc_config.get('onboot', '0') == '1'
        output.append(f"  Autostart: {'✅ Enabled' if onboot else '❌ Disabled'}")
        
        startup_order = lxc_config.get('startup', 'Default')
        if startup_order != 'Default':
            output.append(f"  Startup Order: {startup_order}")

        # Security Features
        output.append(f"\n**Security Features**:")
        
        nesting = lxc_config.get('features', '').find('nesting=1') != -1
        output.append(f"  Nesting: {'✅ Enabled' if nesting else '❌ Disabled'}")
        
        keyctl = lxc_config.get('features', '').find('keyctl=1') != -1
        output.append(f"  Keyctl: {'✅ Enabled' if keyctl else '❌ Disabled'}")

        # Configuration Warnings and Recommendations
        warnings = []
        recommendations = []

        if not unprivileged:
            warnings.append("⚠️ Privileged container - security risk")
            recommendations.append("Consider migrating to unprivileged container")

        if not onboot:
            recommendations.append("Enable autostart for critical services")

        if int(swap) == 0:
            recommendations.append("Consider enabling swap for memory stability")

        if warnings:
            output.append(f"\n**⚠️ Warnings**:")
            for warning in warnings:
                output.append(f"  {warning}")

        if recommendations:
            output.append(f"\n**💡 Recommendations**:")
            for rec in recommendations:
                output.append(f"  • {rec}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting LXC configuration for container {vmid}: {str(e)}"
