"""
Tailscale MCP Server

Provides MCP tools for managing Tailscale VPN network:
- Device management
- ACL configuration
- DNS settings
- Subnet routing
- Network monitoring
"""

import os
import requests
from typing import List, Dict, Any, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
TAILSCALE_API_KEY = os.getenv("TAILSCALE_API_KEY", "")
TAILSCALE_TAILNET = os.getenv("TAILSCALE_TAILNET", "")
TAILSCALE_API_BASE = "https://api.tailscale.com/api/v2"

# Initialize MCP server
server = Server("tailscale-mcp")


class TailscaleAPI:
    """Wrapper for Tailscale API"""

    def __init__(self, api_key: str, tailnet: str):
        self.api_key = api_key
        self.tailnet = tailnet
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request to Tailscale"""
        url = f"{TAILSCALE_API_BASE}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json() if response.text else {}

    def list_devices(self) -> List[Dict[str, Any]]:
        """List all devices in the tailnet"""
        return self._request("GET", f"/tailnet/{self.tailnet}/devices")

    def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get specific device details"""
        return self._request("GET", f"/device/{device_id}")

    def delete_device(self, device_id: str) -> Dict[str, Any]:
        """Remove device from tailnet"""
        return self._request("DELETE", f"/device/{device_id}")

    def authorize_device(self, device_id: str) -> Dict[str, Any]:
        """Authorize a device"""
        return self._request("POST", f"/device/{device_id}/authorized", json={"authorized": True})

    def get_acl(self) -> Dict[str, Any]:
        """Get current ACL policy"""
        return self._request("GET", f"/tailnet/{self.tailnet}/acl")

    def update_acl(self, acl_policy: Dict[str, Any]) -> Dict[str, Any]:
        """Update ACL policy"""
        return self._request("POST", f"/tailnet/{self.tailnet}/acl", json=acl_policy)

    def get_dns_settings(self) -> Dict[str, Any]:
        """Get DNS configuration"""
        return self._request("GET", f"/tailnet/{self.tailnet}/dns/nameservers")

    def update_dns_settings(self, nameservers: List[str]) -> Dict[str, Any]:
        """Update DNS nameservers"""
        return self._request("POST", f"/tailnet/{self.tailnet}/dns/nameservers", json={"dns": nameservers})

    def enable_subnet_routes(self, device_id: str, routes: List[str]) -> Dict[str, Any]:
        """Enable subnet routes for a device"""
        return self._request("POST", f"/device/{device_id}/routes", json={"routes": routes})


# Initialize Tailscale API client
ts_api = TailscaleAPI(TAILSCALE_API_KEY, TAILSCALE_TAILNET)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Tailscale tools"""
    return [
        types.Tool(
            name="list_tailscale_devices",
            description="List all devices in the Tailscale network",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_tailscale_device",
            description="Get details for a specific Tailscale device",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device ID or hostname"}
                },
                "required": ["device_id"]
            }
        ),
        types.Tool(
            name="authorize_tailscale_device",
            description="Authorize a new device in the tailnet",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device ID to authorize"}
                },
                "required": ["device_id"]
            }
        ),
        types.Tool(
            name="remove_tailscale_device",
            description="Remove a device from the tailnet",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device ID to remove"}
                },
                "required": ["device_id"]
            }
        ),
        types.Tool(
            name="get_tailscale_acl",
            description="Get current Tailscale ACL (Access Control List) policy",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="update_tailscale_acl",
            description="Update Tailscale ACL policy (use with caution!)",
            inputSchema={
                "type": "object",
                "properties": {
                    "acl_policy": {
                        "type": "object",
                        "description": "New ACL policy in JSON format"
                    }
                },
                "required": ["acl_policy"]
            }
        ),
        types.Tool(
            name="get_tailscale_dns",
            description="Get Tailscale DNS configuration",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="update_tailscale_dns",
            description="Update Tailscale DNS nameservers",
            inputSchema={
                "type": "object",
                "properties": {
                    "nameservers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of DNS nameserver IPs"
                    }
                },
                "required": ["nameservers"]
            }
        ),
        types.Tool(
            name="enable_subnet_routes",
            description="Enable subnet routing for a device (exit node or subnet router)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device ID"},
                    "routes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of CIDR routes to advertise (e.g., 192.168.1.0/24)"
                    }
                },
                "required": ["device_id", "routes"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    try:
        if name == "list_tailscale_devices":
            devices = ts_api.list_devices()
            return [types.TextContent(
                type="text",
                text=f"Found {len(devices.get('devices', []))} devices:\n" +
                     "\n".join([f"- {d.get('hostname')} ({d.get('addresses', [])[0] if d.get('addresses') else 'no IP'})"
                               for d in devices.get('devices', [])])
            )]

        elif name == "get_tailscale_device":
            device = ts_api.get_device(arguments["device_id"])
            return [types.TextContent(
                type="text",
                text=f"Device details:\n" +
                     f"Hostname: {device.get('hostname')}\n" +
                     f"IP: {device.get('addresses', [])[0] if device.get('addresses') else 'N/A'}\n" +
                     f"Online: {device.get('online', False)}\n" +
                     f"OS: {device.get('os', 'Unknown')}\n" +
                     f"Last seen: {device.get('lastSeen', 'Unknown')}"
            )]

        elif name == "authorize_tailscale_device":
            result = ts_api.authorize_device(arguments["device_id"])
            return [types.TextContent(
                type="text",
                text=f"Device {arguments['device_id']} authorized successfully"
            )]

        elif name == "remove_tailscale_device":
            ts_api.delete_device(arguments["device_id"])
            return [types.TextContent(
                type="text",
                text=f"Device {arguments['device_id']} removed from tailnet"
            )]

        elif name == "get_tailscale_acl":
            acl = ts_api.get_acl()
            import json
            return [types.TextContent(
                type="text",
                text=f"Current ACL policy:\n{json.dumps(acl, indent=2)}"
            )]

        elif name == "update_tailscale_acl":
            result = ts_api.update_acl(arguments["acl_policy"])
            return [types.TextContent(
                type="text",
                text="ACL policy updated successfully"
            )]

        elif name == "get_tailscale_dns":
            dns = ts_api.get_dns_settings()
            return [types.TextContent(
                type="text",
                text=f"DNS nameservers: {', '.join(dns.get('dns', []))}"
            )]

        elif name == "update_tailscale_dns":
            result = ts_api.update_dns_settings(arguments["nameservers"])
            return [types.TextContent(
                type="text",
                text=f"DNS updated to: {', '.join(arguments['nameservers'])}"
            )]

        elif name == "enable_subnet_routes":
            result = ts_api.enable_subnet_routes(
                arguments["device_id"],
                arguments["routes"]
            )
            return [types.TextContent(
                type="text",
                text=f"Subnet routes enabled: {', '.join(arguments['routes'])}"
            )]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

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
                server_name="tailscale",
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
