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
