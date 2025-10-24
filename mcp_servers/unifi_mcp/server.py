"""
Unifi Network MCP Server

Provides MCP tools for managing Unifi Network infrastructure:
- Client management (block/unblock, reconnect)
- Network monitoring
- Device management
- Firewall rules
- Guest network management
- Port forwarding
"""

import os
from typing import List, Dict, Any
from pyunifi.controller import Controller
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
UNIFI_HOST = os.getenv("UNIFI_HOST", "")
UNIFI_PORT = int(os.getenv("UNIFI_PORT", "8443"))
UNIFI_USERNAME = os.getenv("UNIFI_USERNAME", "")
UNIFI_PASSWORD = os.getenv("UNIFI_PASSWORD", "")
UNIFI_SITE = os.getenv("UNIFI_SITE", "default")
UNIFI_VERIFY_SSL = os.getenv("UNIFI_VERIFY_SSL", "false").lower() == "true"

# Initialize MCP server
server = Server("unifi-mcp")

# Initialize Unifi Controller
unifi = Controller(
    UNIFI_HOST,
    UNIFI_USERNAME,
    UNIFI_PASSWORD,
    UNIFI_PORT,
    "v5",
    UNIFI_SITE,
    ssl_verify=UNIFI_VERIFY_SSL
)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Unifi tools"""
    return [
        types.Tool(
            name="list_unifi_clients",
            description="List all connected clients on the network",
            inputSchema={
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "Show only active/connected clients",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_client_details",
            description="Get detailed information about a specific client",
            inputSchema={
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Client MAC address"
                    }
                },
                "required": ["mac"]
            }
        ),
        types.Tool(
            name="block_client",
            description="Block a client from accessing the network",
            inputSchema={
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Client MAC address to block"
                    }
                },
                "required": ["mac"]
            }
        ),
        types.Tool(
            name="unblock_client",
            description="Unblock a previously blocked client",
            inputSchema={
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Client MAC address to unblock"
                    }
                },
                "required": ["mac"]
            }
        ),
        types.Tool(
            name="reconnect_client",
            description="Force reconnect a client (disconnect and let it reconnect)",
            inputSchema={
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Client MAC address"
                    }
                },
                "required": ["mac"]
            }
        ),
        types.Tool(
            name="list_unifi_devices",
            description="List all Unifi devices (APs, switches, gateways)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_device_details",
            description="Get detailed information about a Unifi device",
            inputSchema={
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Device MAC address"
                    }
                },
                "required": ["mac"]
            }
        ),
        types.Tool(
            name="reboot_device",
            description="Reboot a Unifi device",
            inputSchema={
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Device MAC address"
                    }
                },
                "required": ["mac"]
            }
        ),
        types.Tool(
            name="get_network_stats",
            description="Get network statistics (bandwidth, clients, traffic)",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to look back",
                        "default": 24
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="list_firewall_rules",
            description="List all firewall rules",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="create_firewall_rule",
            description="Create a new firewall rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Rule name"},
                    "action": {
                        "type": "string",
                        "description": "Action to take",
                        "enum": ["accept", "drop", "reject"]
                    },
                    "protocol": {
                        "type": "string",
                        "description": "Protocol",
                        "enum": ["all", "tcp", "udp", "icmp"]
                    },
                    "src_address": {
                        "type": "string",
                        "description": "Source IP/CIDR (optional)"
                    },
                    "dst_address": {
                        "type": "string",
                        "description": "Destination IP/CIDR (optional)"
                    },
                    "dst_port": {
                        "type": "string",
                        "description": "Destination port (optional)"
                    }
                },
                "required": ["name", "action", "protocol"]
            }
        ),
        types.Tool(
            name="create_guest_voucher",
            description="Create a guest WiFi voucher",
            inputSchema={
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "integer",
                        "description": "Duration in minutes",
                        "default": 1440
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of vouchers to create",
                        "default": 1
                    },
                    "note": {
                        "type": "string",
                        "description": "Note for the voucher"
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    try:
        if name == "list_unifi_clients":
            clients = unifi.get_clients()

            if arguments.get("active_only", True):
                clients = [c for c in clients if c.get("is_wired") or c.get("is_wireless")]

            if not clients:
                return [types.TextContent(type="text", text="No clients found")]

            output = f"Found {len(clients)} clients:\n\n"
            for client in clients:
                connection = "📶 WiFi" if client.get("is_wireless") else "🔌 Wired"
                ip = client.get("ip", "N/A")
                hostname = client.get("hostname", client.get("name", "Unknown"))
                mac = client.get("mac", "N/A")

                output += f"{connection} {hostname}\n"
                output += f"   IP: {ip}, MAC: {mac}\n"
                output += f"   RX: {client.get('rx_bytes', 0) / 1024 / 1024:.1f} MB, "
                output += f"TX: {client.get('tx_bytes', 0) / 1024 / 1024:.1f} MB\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_client_details":
            clients = unifi.get_clients()
            client = next((c for c in clients if c.get("mac") == arguments["mac"]), None)

            if not client:
                return [types.TextContent(type="text", text=f"Client {arguments['mac']} not found")]

            output = f"Client Details:\n" +\
                     f"Hostname: {client.get('hostname', 'Unknown')}\n" +\
                     f"IP: {client.get('ip', 'N/A')}\n" +\
                     f"MAC: {client.get('mac', 'N/A')}\n" +\
                     f"Connection: {'WiFi' if client.get('is_wireless') else 'Wired'}\n" +\
                     f"Signal: {client.get('signal', 'N/A')} dBm\n" +\
                     f"Channel: {client.get('channel', 'N/A')}\n" +\
                     f"Network: {client.get('essid', client.get('network', 'N/A'))}\n" +\
                     f"RX: {client.get('rx_bytes', 0) / 1024 / 1024:.1f} MB\n" +\
                     f"TX: {client.get('tx_bytes', 0) / 1024 / 1024:.1f} MB"

            return [types.TextContent(type="text", text=output)]

        elif name == "block_client":
            unifi.block_client(arguments["mac"])
            return [types.TextContent(type="text", text=f"✅ Client {arguments['mac']} blocked")]

        elif name == "unblock_client":
            unifi.unblock_client(arguments["mac"])
            return [types.TextContent(type="text", text=f"✅ Client {arguments['mac']} unblocked")]

        elif name == "reconnect_client":
            unifi.reconnect_client(arguments["mac"])
            return [types.TextContent(type="text", text=f"✅ Client {arguments['mac']} reconnecting")]

        elif name == "list_unifi_devices":
            devices = unifi.get_aps()

            if not devices:
                return [types.TextContent(type="text", text="No devices found")]

            output = f"Found {len(devices)} devices:\n\n"
            for device in devices:
                device_type = device.get("type", "unknown")
                emoji = {"uap": "📡", "usw": "🔀", "ugw": "🌐"}.get(device_type, "⚙️")
                name = device.get("name", device.get("hostname", "Unknown"))
                model = device.get("model", "N/A")
                state = "✅" if device.get("state") == 1 else "❌"

                output += f"{emoji} {state} {name} ({model})\n"
                output += f"   IP: {device.get('ip', 'N/A')}, MAC: {device.get('mac', 'N/A')}\n"
                output += f"   Clients: {device.get('num_sta', 0)}\n"
                output += f"   Uptime: {device.get('uptime', 0) / 86400:.1f} days\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_device_details":
            devices = unifi.get_aps()
            device = next((d for d in devices if d.get("mac") == arguments["mac"]), None)

            if not device:
                return [types.TextContent(type="text", text=f"Device {arguments['mac']} not found")]

            output = f"Device Details:\n" +\
                     f"Name: {device.get('name', 'Unknown')}\n" +\
                     f"Model: {device.get('model', 'N/A')}\n" +\
                     f"Type: {device.get('type', 'N/A')}\n" +\
                     f"IP: {device.get('ip', 'N/A')}\n" +\
                     f"MAC: {device.get('mac', 'N/A')}\n" +\
                     f"Version: {device.get('version', 'N/A')}\n" +\
                     f"State: {'Online' if device.get('state') == 1 else 'Offline'}\n" +\
                     f"Clients: {device.get('num_sta', 0)}\n" +\
                     f"Uptime: {device.get('uptime', 0) / 86400:.1f} days"

            return [types.TextContent(type="text", text=output)]

        elif name == "reboot_device":
            unifi.restart_ap(arguments["mac"])
            return [types.TextContent(type="text", text=f"✅ Device {arguments['mac']} rebooting")]

        elif name == "get_network_stats":
            stats = unifi.get_health()

            output = "Network Health:\n\n"
            for stat in stats:
                subsystem = stat.get("subsystem", "unknown")
                status = "✅" if stat.get("status") == "ok" else "❌"
                output += f"{status} {subsystem.upper()}\n"

                if "num_user" in stat:
                    output += f"   Users: {stat['num_user']}\n"
                if "num_guest" in stat:
                    output += f"   Guests: {stat['num_guest']}\n"
                if "num_ap" in stat:
                    output += f"   APs: {stat['num_ap']}\n"
                if "num_adopted" in stat:
                    output += f"   Adopted: {stat['num_adopted']}\n"

                output += "\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "list_firewall_rules":
            rules = unifi.get_firewall_rules()

            if not rules:
                return [types.TextContent(type="text", text="No firewall rules found")]

            output = f"Found {len(rules)} firewall rules:\n\n"
            for rule in rules:
                action_emoji = {"accept": "✅", "drop": "🚫", "reject": "❌"}.get(rule.get("action"), "⚙️")
                enabled = "🟢" if rule.get("enabled") else "🔴"

                output += f"{enabled} {action_emoji} {rule.get('name', 'Unnamed')}\n"
                output += f"   Protocol: {rule.get('protocol', 'all')}\n"
                output += f"   Action: {rule.get('action', 'N/A')}\n"

                if rule.get("src_address"):
                    output += f"   Source: {rule['src_address']}\n"
                if rule.get("dst_address"):
                    output += f"   Destination: {rule['dst_address']}\n"

                output += "\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "create_firewall_rule":
            rule_data = {
                "name": arguments["name"],
                "action": arguments["action"],
                "protocol": arguments["protocol"],
                "enabled": True
            }

            if "src_address" in arguments:
                rule_data["src_address"] = arguments["src_address"]
            if "dst_address" in arguments:
                rule_data["dst_address"] = arguments["dst_address"]
            if "dst_port" in arguments:
                rule_data["dst_port"] = arguments["dst_port"]

            result = unifi.create_firewall_rule(**rule_data)

            return [types.TextContent(
                type="text",
                text=f"✅ Firewall rule created: {arguments['name']}"
            )]

        elif name == "create_guest_voucher":
            duration = arguments.get("duration", 1440)
            count = arguments.get("count", 1)
            note = arguments.get("note", "Created by agent")

            vouchers = unifi.create_voucher(duration, count, note=note)

            output = f"✅ Created {count} guest voucher(s):\n\n"
            for voucher in vouchers:
                output += f"Code: {voucher.get('code', 'N/A')}\n"
                output += f"Duration: {duration} minutes\n"
                output += f"Note: {note}\n\n"

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
                server_name="unifi",
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
