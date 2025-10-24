"""
Pi-hole MCP Server

Provides MCP tools for managing Pi-hole DNS ad blocking:
- Enable/disable blocking
- Whitelist/blacklist management
- Query statistics
- Update gravity database
- Top clients and domains
"""

import os
import requests
from typing import List, Dict, Any, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
PIHOLE_HOST = os.getenv("PIHOLE_HOST", "")
PIHOLE_PORT = int(os.getenv("PIHOLE_PORT", "80"))
PIHOLE_API_TOKEN = os.getenv("PIHOLE_API_TOKEN", "")
PIHOLE_BASE_URL = f"http://{PIHOLE_HOST}:{PIHOLE_PORT}/admin/api.php"

# Initialize MCP server
server = Server("pihole-mcp")


class PiHoleAPI:
    """Wrapper for Pi-hole API"""

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.api_token = api_token

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to Pi-hole"""
        params["auth"] = self.api_token
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        return response.json()

    def get_summary(self) -> Dict[str, Any]:
        """Get Pi-hole summary statistics"""
        return self._request({"summary": ""})

    def enable_blocking(self) -> Dict[str, Any]:
        """Enable ad blocking"""
        return self._request({"enable": ""})

    def disable_blocking(self, duration: int = 0) -> Dict[str, Any]:
        """Disable ad blocking (duration in seconds, 0 = permanent)"""
        return self._request({"disable": duration})

    def get_top_items(self, count: int = 10) -> Dict[str, Any]:
        """Get top domains and clients"""
        return self._request({"topItems": count})

    def get_top_clients(self, count: int = 10) -> Dict[str, Any]:
        """Get top clients"""
        return self._request({"topClients": count})

    def get_forward_destinations(self) -> Dict[str, Any]:
        """Get upstream DNS forward destinations"""
        return self._request({"getForwardDestinations": ""})

    def get_query_types(self) -> Dict[str, Any]:
        """Get query type statistics"""
        return self._request({"getQueryTypes": ""})

    def add_to_whitelist(self, domain: str) -> Dict[str, Any]:
        """Add domain to whitelist"""
        return self._request({"list": "white", "add": domain})

    def add_to_blacklist(self, domain: str) -> Dict[str, Any]:
        """Add domain to blacklist"""
        return self._request({"list": "black", "add": domain})

    def remove_from_whitelist(self, domain: str) -> Dict[str, Any]:
        """Remove domain from whitelist"""
        return self._request({"list": "white", "sub": domain})

    def remove_from_blacklist(self, domain: str) -> Dict[str, Any]:
        """Remove domain from blacklist"""
        return self._request({"list": "black", "sub": domain})

    def update_gravity(self) -> Dict[str, Any]:
        """Update gravity database (blocklists)"""
        return self._request({"updateGravity": ""})

    def get_recent_blocked(self, count: int = 10) -> Dict[str, Any]:
        """Get recently blocked domains"""
        return self._request({"recentBlocked": count})


# Initialize Pi-hole API client
pihole_api = PiHoleAPI(PIHOLE_BASE_URL, PIHOLE_API_TOKEN)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Pi-hole tools"""
    return [
        types.Tool(
            name="get_pihole_summary",
            description="Get Pi-hole summary statistics (queries, blocked, percentage)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="enable_pihole_blocking",
            description="Enable Pi-hole ad blocking",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="disable_pihole_blocking",
            description="Disable Pi-hole ad blocking temporarily or permanently",
            inputSchema={
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "integer",
                        "description": "Duration in seconds (0 = permanent until re-enabled)",
                        "default": 300
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_pihole_top_items",
            description="Get top blocked domains and top queried domains",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of items to return",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_pihole_top_clients",
            description="Get top clients by query count",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of clients to return",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="whitelist_domain",
            description="Add a domain to the whitelist (allow)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to whitelist (e.g., example.com)"
                    }
                },
                "required": ["domain"]
            }
        ),
        types.Tool(
            name="blacklist_domain",
            description="Add a domain to the blacklist (block)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to blacklist (e.g., ads.example.com)"
                    }
                },
                "required": ["domain"]
            }
        ),
        types.Tool(
            name="remove_whitelist_domain",
            description="Remove a domain from the whitelist",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to remove from whitelist"
                    }
                },
                "required": ["domain"]
            }
        ),
        types.Tool(
            name="remove_blacklist_domain",
            description="Remove a domain from the blacklist",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to remove from blacklist"
                    }
                },
                "required": ["domain"]
            }
        ),
        types.Tool(
            name="update_pihole_gravity",
            description="Update Pi-hole gravity database (pull latest blocklists)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_recent_blocked",
            description="Get recently blocked domains",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of recent blocks to return",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_forward_destinations",
            description="Get upstream DNS forward destinations and their usage",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_query_types",
            description="Get DNS query type statistics (A, AAAA, PTR, etc.)",
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
        if name == "get_pihole_summary":
            summary = pihole_api.get_summary()

            output = f"Pi-hole Summary:\\n" +\
                     f"Status: {summary.get('status', 'unknown')}\\n" +\
                     f"Queries today: {summary.get('dns_queries_today', 0):,}\\n" +\
                     f"Blocked today: {summary.get('ads_blocked_today', 0):,}\\n" +\
                     f"Percentage blocked: {summary.get('ads_percentage_today', 0):.2f}%\\n" +\
                     f"Domains on blocklist: {summary.get('domains_being_blocked', 0):,}\\n" +\
                     f"Unique clients: {summary.get('unique_clients', 0)}\\n" +\
                     f"Queries forwarded: {summary.get('queries_forwarded', 0):,}\\n" +\
                     f"Queries cached: {summary.get('queries_cached', 0):,}"

            return [types.TextContent(type="text", text=output)]

        elif name == "enable_pihole_blocking":
            result = pihole_api.enable_blocking()
            return [types.TextContent(
                type="text",
                text=f"✅ Pi-hole blocking enabled: {result.get('status', 'enabled')}"
            )]

        elif name == "disable_pihole_blocking":
            duration = arguments.get("duration", 300)
            result = pihole_api.disable_blocking(duration)

            if duration == 0:
                msg = "⚠️ Pi-hole blocking disabled permanently"
            else:
                msg = f"⚠️ Pi-hole blocking disabled for {duration} seconds"

            return [types.TextContent(type="text", text=msg)]

        elif name == "get_pihole_top_items":
            count = arguments.get("count", 10)
            data = pihole_api.get_top_items(count)

            output = f"Top {count} Domains:\\n\\n"

            # Top queries
            output += "Most Queried:\\n"
            for domain, queries in list(data.get("top_queries", {}).items())[:count]:
                output += f"  {domain}: {queries} queries\\n"

            output += "\\nMost Blocked:\\n"
            for domain, blocks in list(data.get("top_ads", {}).items())[:count]:
                output += f"  {domain}: {blocks} blocks\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_pihole_top_clients":
            count = arguments.get("count", 10)
            data = pihole_api.get_top_clients(count)

            output = f"Top {count} Clients:\\n\\n"
            for client, queries in list(data.get("top_sources", {}).items())[:count]:
                output += f"  {client}: {queries} queries\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "whitelist_domain":
            domain = arguments["domain"]
            result = pihole_api.add_to_whitelist(domain)
            return [types.TextContent(
                type="text",
                text=f"✅ Domain {domain} added to whitelist"
            )]

        elif name == "blacklist_domain":
            domain = arguments["domain"]
            result = pihole_api.add_to_blacklist(domain)
            return [types.TextContent(
                type="text",
                text=f"✅ Domain {domain} added to blacklist"
            )]

        elif name == "remove_whitelist_domain":
            domain = arguments["domain"]
            result = pihole_api.remove_from_whitelist(domain)
            return [types.TextContent(
                type="text",
                text=f"✅ Domain {domain} removed from whitelist"
            )]

        elif name == "remove_blacklist_domain":
            domain = arguments["domain"]
            result = pihole_api.remove_from_blacklist(domain)
            return [types.TextContent(
                type="text",
                text=f"✅ Domain {domain} removed from blacklist"
            )]

        elif name == "update_pihole_gravity":
            result = pihole_api.update_gravity()
            return [types.TextContent(
                type="text",
                text="✅ Pi-hole gravity database update initiated"
            )]

        elif name == "get_recent_blocked":
            count = arguments.get("count", 10)
            result = pihole_api.get_recent_blocked(count)

            output = f"Recently Blocked Domains:\\n"
            for domain in result:
                output += f"  🚫 {domain}\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_forward_destinations":
            data = pihole_api.get_forward_destinations()

            output = "Upstream DNS Forward Destinations:\\n\\n"
            for dest, percentage in data.get("forward_destinations", {}).items():
                output += f"  {dest}: {percentage:.2f}%\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_query_types":
            data = pihole_api.get_query_types()

            output = "DNS Query Types:\\n\\n"
            for query_type, percentage in data.get("querytypes", {}).items():
                output += f"  {query_type}: {percentage:.2f}%\\n"

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
                server_name="pihole",
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
