"""
Proxmox VE MCP Server

Provides MCP tools for managing Proxmox Virtual Environment:
- VM/LXC lifecycle management (create, start, stop, delete)
- Resource monitoring (CPU, memory, disk usage)
- Storage management
- Backup operations
- Cluster status
- Network configuration
"""

import os
from typing import List, Dict, Any, Optional
from proxmoxer import ProxmoxAPI
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
PROXMOX_HOST = os.getenv("PROXMOX_HOST", "")
PROXMOX_PORT = int(os.getenv("PROXMOX_PORT", "8006"))
PROXMOX_USER = os.getenv("PROXMOX_USER", "root@pam")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD", "")
PROXMOX_TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID", "")
PROXMOX_TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET", "")
PROXMOX_NODE = os.getenv("PROXMOX_NODE", "fjeld")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"

# Initialize MCP server
server = Server("proxmox-mcp")

# Initialize Proxmox API client
if PROXMOX_TOKEN_ID and PROXMOX_TOKEN_SECRET:
    # Use API token (recommended)
    # PROXMOX_TOKEN_ID format: root@pam!agent-token
    user_part, token_name = PROXMOX_TOKEN_ID.rsplit("!", 1)
    proxmox = ProxmoxAPI(
        PROXMOX_HOST,
        user=user_part,
        token_name=token_name,
        token_value=PROXMOX_TOKEN_SECRET,
        verify_ssl=PROXMOX_VERIFY_SSL,
        port=PROXMOX_PORT
    )
else:
    # Fall back to password authentication
    proxmox = ProxmoxAPI(
        PROXMOX_HOST,
        user=PROXMOX_USER,
        password=PROXMOX_PASSWORD,
        verify_ssl=PROXMOX_VERIFY_SSL,
        port=PROXMOX_PORT
    )


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Proxmox tools"""
    return [
        types.Tool(
            name="list_vms",
            description="List all VMs and containers on the Proxmox node",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Filter by type: all, qemu (VMs), or lxc (containers)",
                        "enum": ["all", "qemu", "lxc"],
                        "default": "all"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_vm_status",
            description="Get detailed status of a specific VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "integer",
                        "description": "VM/Container ID"
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="start_vm",
            description="Start a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "integer",
                        "description": "VM/Container ID to start"
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="stop_vm",
            description="Stop a VM or container gracefully",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "integer",
                        "description": "VM/Container ID to stop"
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="reboot_vm",
            description="Reboot a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "integer",
                        "description": "VM/Container ID to reboot"
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="shutdown_vm",
            description="Shutdown a VM or container (more forceful than stop)",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "integer",
                        "description": "VM/Container ID to shutdown"
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="create_lxc",
            description="Create a new LXC container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {"type": "integer", "description": "Container ID"},
                    "hostname": {"type": "string", "description": "Container hostname"},
                    "ostemplate": {"type": "string", "description": "OS template (e.g., local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst)"},
                    "memory": {"type": "integer", "description": "Memory in MB", "default": 512},
                    "cores": {"type": "integer", "description": "CPU cores", "default": 1},
                    "rootfs": {"type": "string", "description": "Root filesystem size (e.g., 'local-lvm:8')", "default": "local-lvm:8"},
                    "net0": {"type": "string", "description": "Network config (e.g., 'name=eth0,bridge=vmbr0,ip=dhcp')", "default": "name=eth0,bridge=vmbr0,ip=dhcp"},
                    "password": {"type": "string", "description": "Root password"}
                },
                "required": ["vmid", "hostname", "ostemplate", "password"]
            }
        ),
        types.Tool(
            name="delete_vm",
            description="Delete a VM or container (destructive!)",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "integer",
                        "description": "VM/Container ID to delete"
                    },
                    "purge": {
                        "type": "boolean",
                        "description": "Purge all data (cannot be recovered)",
                        "default": True
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="get_node_status",
            description="Get Proxmox node status (CPU, memory, disk usage)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="list_storage",
            description="List all storage devices and their usage",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="list_backups",
            description="List all backups on the node",
            inputSchema={
                "type": "object",
                "properties": {
                    "storage": {
                        "type": "string",
                        "description": "Storage ID to filter backups (optional)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="create_backup",
            description="Create a backup of a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {"type": "integer", "description": "VM/Container ID to backup"},
                    "storage": {"type": "string", "description": "Storage ID for backup", "default": "local"},
                    "mode": {
                        "type": "string",
                        "description": "Backup mode",
                        "enum": ["snapshot", "suspend", "stop"],
                        "default": "snapshot"
                    },
                    "compress": {
                        "type": "string",
                        "description": "Compression algorithm",
                        "enum": ["0", "1", "gzip", "lzo", "zstd"],
                        "default": "zstd"
                    }
                },
                "required": ["vmid"]
            }
        ),
        types.Tool(
            name="restore_backup",
            description="Restore a VM or container from backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {"type": "integer", "description": "Target VM/Container ID"},
                    "archive": {"type": "string", "description": "Backup archive path"},
                    "storage": {"type": "string", "description": "Storage for restored VM"}
                },
                "required": ["vmid", "archive"]
            }
        ),
        types.Tool(
            name="get_cluster_resources",
            description="Get cluster-wide resource overview",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    try:
        node = proxmox.nodes(PROXMOX_NODE)

        if name == "list_vms":
            vm_type = arguments.get("type", "all")

            vms = []
            if vm_type in ["all", "qemu"]:
                vms.extend([(vm, "VM") for vm in node.qemu.get()])
            if vm_type in ["all", "lxc"]:
                vms.extend([(vm, "CT") for vm in node.lxc.get()])

            if not vms:
                return [types.TextContent(type="text", text="No VMs/containers found")]

            output = f"Found {len(vms)} {'VM/containers' if vm_type == 'all' else vm_type.upper()}:\\n\\n"
            for vm, vm_type_label in vms:
                status_emoji = "✅" if vm.get("status") == "running" else "⭕"
                output += f"{status_emoji} [{vm_type_label}] {vm['vmid']}: {vm.get('name', 'unnamed')}\\n"
                output += f"   Status: {vm.get('status', 'unknown')}\\n"
                output += f"   CPU: {vm.get('cpu', 0) * 100:.1f}%\\n"
                output += f"   Memory: {vm.get('mem', 0) / 1024 / 1024:.0f} MB / {vm.get('maxmem', 0) / 1024 / 1024:.0f} MB\\n"
                output += f"   Uptime: {vm.get('uptime', 0) / 86400:.1f} days\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_vm_status":
            vmid = arguments["vmid"]

            # Try to get as QEMU VM first
            try:
                vm = node.qemu(vmid).status.current.get()
                vm_type = "VM"
            except:
                # Fall back to LXC container
                vm = node.lxc(vmid).status.current.get()
                vm_type = "Container"

            output = f"{vm_type} Status (ID: {vmid}):\\n" +\
                     f"Name: {vm.get('name', 'unnamed')}\\n" +\
                     f"Status: {vm.get('status', 'unknown')}\\n" +\
                     f"CPU: {vm.get('cpu', 0) * 100:.1f}%\\n" +\
                     f"Memory: {vm.get('mem', 0) / 1024 / 1024:.0f} MB / {vm.get('maxmem', 0) / 1024 / 1024:.0f} MB\\n" +\
                     f"Disk: {vm.get('disk', 0) / 1024 / 1024 / 1024:.1f} GB / {vm.get('maxdisk', 0) / 1024 / 1024 / 1024:.1f} GB\\n" +\
                     f"Uptime: {vm.get('uptime', 0) / 86400:.1f} days"

            return [types.TextContent(type="text", text=output)]

        elif name == "start_vm":
            vmid = arguments["vmid"]

            try:
                node.qemu(vmid).status.start.post()
            except:
                node.lxc(vmid).status.start.post()

            return [types.TextContent(type="text", text=f"✅ VM/Container {vmid} starting")]

        elif name == "stop_vm":
            vmid = arguments["vmid"]

            try:
                node.qemu(vmid).status.stop.post()
            except:
                node.lxc(vmid).status.stop.post()

            return [types.TextContent(type="text", text=f"✅ VM/Container {vmid} stopping")]

        elif name == "reboot_vm":
            vmid = arguments["vmid"]

            try:
                node.qemu(vmid).status.reboot.post()
            except:
                node.lxc(vmid).status.reboot.post()

            return [types.TextContent(type="text", text=f"✅ VM/Container {vmid} rebooting")]

        elif name == "shutdown_vm":
            vmid = arguments["vmid"]

            try:
                node.qemu(vmid).status.shutdown.post()
            except:
                node.lxc(vmid).status.shutdown.post()

            return [types.TextContent(type="text", text=f"✅ VM/Container {vmid} shutting down")]

        elif name == "create_lxc":
            vmid = arguments["vmid"]
            config = {
                "vmid": vmid,
                "hostname": arguments["hostname"],
                "ostemplate": arguments["ostemplate"],
                "password": arguments["password"],
                "memory": arguments.get("memory", 512),
                "cores": arguments.get("cores", 1),
                "rootfs": arguments.get("rootfs", "local-lvm:8"),
                "net0": arguments.get("net0", "name=eth0,bridge=vmbr0,ip=dhcp")
            }

            node.lxc.create(**config)

            return [types.TextContent(
                type="text",
                text=f"✅ LXC container {vmid} ({arguments['hostname']}) created successfully"
            )]

        elif name == "delete_vm":
            vmid = arguments["vmid"]
            purge = arguments.get("purge", True)

            try:
                node.qemu(vmid).delete(purge=1 if purge else 0)
            except:
                node.lxc(vmid).delete(purge=1 if purge else 0)

            return [types.TextContent(
                type="text",
                text=f"✅ VM/Container {vmid} deleted {'(purged)' if purge else ''}"
            )]

        elif name == "get_node_status":
            status = node.status.get()

            output = f"Node Status ({PROXMOX_NODE}):\\n" +\
                     f"CPU: {status.get('cpu', 0) * 100:.1f}%\\n" +\
                     f"Memory: {status.get('memory', {}).get('used', 0) / 1024 / 1024 / 1024:.1f} GB / " +\
                     f"{status.get('memory', {}).get('total', 0) / 1024 / 1024 / 1024:.1f} GB\\n" +\
                     f"Swap: {status.get('swap', {}).get('used', 0) / 1024 / 1024 / 1024:.1f} GB / " +\
                     f"{status.get('swap', {}).get('total', 0) / 1024 / 1024 / 1024:.1f} GB\\n" +\
                     f"Root FS: {status.get('rootfs', {}).get('used', 0) / 1024 / 1024 / 1024:.1f} GB / " +\
                     f"{status.get('rootfs', {}).get('total', 0) / 1024 / 1024 / 1024:.1f} GB\\n" +\
                     f"Uptime: {status.get('uptime', 0) / 86400:.1f} days"

            return [types.TextContent(type="text", text=output)]

        elif name == "list_storage":
            storage = node.storage.get()

            output = "Storage Devices:\\n\\n"
            for store in storage:
                if store.get("enabled", 0) == 1:
                    output += f"📦 {store['storage']} ({store.get('type', 'unknown')})\\n"
                    if "avail" in store and "total" in store:
                        used = store["total"] - store["avail"]
                        percent = (used / store["total"] * 100) if store["total"] > 0 else 0
                        output += f"   Used: {used / 1024 / 1024 / 1024:.1f} GB / {store['total'] / 1024 / 1024 / 1024:.1f} GB ({percent:.1f}%)\\n"
                    output += f"   Status: {store.get('status', 'unknown')}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "list_backups":
            storage_id = arguments.get("storage")

            if storage_id:
                backups = node.storage(storage_id).content.get(content="backup")
            else:
                # Get backups from all storage
                backups = []
                for store in node.storage.get():
                    try:
                        backups.extend(node.storage(store["storage"]).content.get(content="backup"))
                    except:
                        pass

            if not backups:
                return [types.TextContent(type="text", text="No backups found")]

            output = f"Found {len(backups)} backups:\\n\\n"
            for backup in backups:
                output += f"💾 {backup.get('volid', 'unknown')}\\n"
                output += f"   Size: {backup.get('size', 0) / 1024 / 1024 / 1024:.2f} GB\\n"
                output += f"   Format: {backup.get('format', 'unknown')}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "create_backup":
            vmid = arguments["vmid"]
            storage = arguments.get("storage", "local")
            mode = arguments.get("mode", "snapshot")
            compress = arguments.get("compress", "zstd")

            try:
                task = node.qemu(vmid).backup.post(
                    storage=storage,
                    mode=mode,
                    compress=compress
                )
            except:
                task = node.lxc(vmid).backup.post(
                    storage=storage,
                    mode=mode,
                    compress=compress
                )

            return [types.TextContent(
                type="text",
                text=f"✅ Backup task started for VM/Container {vmid}\\nTask ID: {task}"
            )]

        elif name == "get_cluster_resources":
            resources = proxmox.cluster.resources.get()

            vms = [r for r in resources if r.get("type") in ["qemu", "lxc"]]
            nodes = [r for r in resources if r.get("type") == "node"]

            output = f"Cluster Resources:\\n\\n"
            output += f"Nodes: {len(nodes)}\\n"
            output += f"VMs/Containers: {len(vms)}\\n\\n"

            running = len([v for v in vms if v.get("status") == "running"])
            stopped = len([v for v in vms if v.get("status") == "stopped"])

            output += f"Running: {running}\\n"
            output += f"Stopped: {stopped}\\n"

            return [types.TextContent(type="text", text=output)]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="proxmox",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
