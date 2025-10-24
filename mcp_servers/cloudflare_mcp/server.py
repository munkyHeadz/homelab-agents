"""
Cloudflare MCP Server

Provides MCP tools for managing Cloudflare services:
- DNS record management
- Cloudflare Tunnel management
- WAF rules
- Zero Trust policies
- Cache purging
"""

import os
from typing import List, Dict, Any, Optional
import CloudFlare
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

# Initialize MCP server
server = Server("cloudflare-mcp")

# Initialize Cloudflare API client
cf = CloudFlare.CloudFlare(token=CLOUDFLARE_API_TOKEN)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Cloudflare tools"""
    return [
        types.Tool(
            name="list_dns_records",
            description="List all DNS records for the zone",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_type": {
                        "type": "string",
                        "description": "Optional: Filter by record type (A, AAAA, CNAME, TXT, etc.)",
                        "enum": ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "CAA"]
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional: Filter by record name"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="create_dns_record",
            description="Create a new DNS record",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Record type",
                        "enum": ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "CAA"]
                    },
                    "name": {
                        "type": "string",
                        "description": "DNS record name (e.g., 'subdomain' or '@' for root)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Record content (IP address, hostname, etc.)"
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "TTL in seconds (1 = automatic)",
                        "default": 1
                    },
                    "proxied": {
                        "type": "boolean",
                        "description": "Whether to proxy through Cloudflare (orange cloud)",
                        "default": False
                    }
                },
                "required": ["type", "name", "content"]
            }
        ),
        types.Tool(
            name="update_dns_record",
            description="Update an existing DNS record",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "string",
                        "description": "DNS record ID to update"
                    },
                    "type": {"type": "string"},
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                    "ttl": {"type": "integer", "default": 1},
                    "proxied": {"type": "boolean", "default": False}
                },
                "required": ["record_id", "type", "name", "content"]
            }
        ),
        types.Tool(
            name="delete_dns_record",
            description="Delete a DNS record",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "string",
                        "description": "DNS record ID to delete"
                    }
                },
                "required": ["record_id"]
            }
        ),
        types.Tool(
            name="list_cloudflare_tunnels",
            description="List all Cloudflare Tunnels (cloudflared)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_tunnel_status",
            description="Get status of a specific Cloudflare Tunnel",
            inputSchema={
                "type": "object",
                "properties": {
                    "tunnel_id": {
                        "type": "string",
                        "description": "Tunnel ID"
                    }
                },
                "required": ["tunnel_id"]
            }
        ),
        types.Tool(
            name="purge_cache",
            description="Purge Cloudflare cache (everything or specific URLs)",
            inputSchema={
                "type": "object",
                "properties": {
                    "purge_everything": {
                        "type": "boolean",
                        "description": "Purge all cached files",
                        "default": False
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific URLs to purge"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_zone_analytics",
            description="Get zone analytics (traffic, requests, bandwidth)",
            inputSchema={
                "type": "object",
                "properties": {
                    "since": {
                        "type": "string",
                        "description": "Start time (ISO 8601 or relative like '-1440' for last 24h)"
                    },
                    "until": {
                        "type": "string",
                        "description": "End time (ISO 8601 or relative)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_firewall_rules",
            description="List WAF/firewall rules",
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
                    "expression": {
                        "type": "string",
                        "description": "Firewall rule expression (e.g., '(ip.src eq 1.2.3.4)')"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to take",
                        "enum": ["block", "challenge", "js_challenge", "allow", "log"]
                    },
                    "description": {
                        "type": "string",
                        "description": "Rule description"
                    }
                },
                "required": ["expression", "action"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    try:
        if name == "list_dns_records":
            params = {}
            if "record_type" in arguments:
                params["type"] = arguments["record_type"]
            if "name" in arguments:
                params["name"] = arguments["name"]

            records = cf.zones.dns_records.get(CLOUDFLARE_ZONE_ID, params=params)

            if not records:
                return [types.TextContent(type="text", text="No DNS records found")]

            output = f"Found {len(records)} DNS records:\n\n"
            for record in records:
                proxied = "🟠" if record.get("proxied") else "⚪"
                output += f"{proxied} {record['type']} {record['name']} → {record['content']}\n"
                output += f"   ID: {record['id']}, TTL: {record['ttl']}\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "create_dns_record":
            data = {
                "type": arguments["type"],
                "name": arguments["name"],
                "content": arguments["content"],
                "ttl": arguments.get("ttl", 1),
                "proxied": arguments.get("proxied", False)
            }

            result = cf.zones.dns_records.post(CLOUDFLARE_ZONE_ID, data=data)

            return [types.TextContent(
                type="text",
                text=f"✅ DNS record created:\n" +
                     f"Type: {result['type']}\n" +
                     f"Name: {result['name']}\n" +
                     f"Content: {result['content']}\n" +
                     f"ID: {result['id']}"
            )]

        elif name == "update_dns_record":
            record_id = arguments.pop("record_id")
            data = arguments

            result = cf.zones.dns_records.put(CLOUDFLARE_ZONE_ID, record_id, data=data)

            return [types.TextContent(
                type="text",
                text=f"✅ DNS record updated: {result['name']} → {result['content']}"
            )]

        elif name == "delete_dns_record":
            cf.zones.dns_records.delete(CLOUDFLARE_ZONE_ID, arguments["record_id"])

            return [types.TextContent(
                type="text",
                text=f"✅ DNS record {arguments['record_id']} deleted"
            )]

        elif name == "list_cloudflare_tunnels":
            tunnels = cf.accounts.tunnels.get(CLOUDFLARE_ACCOUNT_ID)

            if not tunnels:
                return [types.TextContent(type="text", text="No tunnels found")]

            output = f"Found {len(tunnels)} Cloudflare Tunnels:\n\n"
            for tunnel in tunnels:
                status = "✅ Connected" if tunnel.get("status") == "healthy" else "❌ Disconnected"
                output += f"{status} {tunnel['name']}\n"
                output += f"   ID: {tunnel['id']}\n"
                output += f"   Created: {tunnel.get('created_at', 'N/A')}\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_tunnel_status":
            tunnel = cf.accounts.tunnels.get(
                CLOUDFLARE_ACCOUNT_ID,
                arguments["tunnel_id"]
            )

            output = f"Tunnel: {tunnel['name']}\n" +\
                     f"Status: {tunnel.get('status', 'unknown')}\n" +\
                     f"Connections: {len(tunnel.get('connections', []))}\n" +\
                     f"Created: {tunnel.get('created_at', 'N/A')}"

            return [types.TextContent(type="text", text=output)]

        elif name == "purge_cache":
            if arguments.get("purge_everything"):
                data = {"purge_everything": True}
            else:
                data = {"files": arguments.get("files", [])}

            cf.zones.purge_cache.post(CLOUDFLARE_ZONE_ID, data=data)

            return [types.TextContent(
                type="text",
                text="✅ Cache purged successfully"
            )]

        elif name == "get_zone_analytics":
            params = {}
            if "since" in arguments:
                params["since"] = arguments["since"]
            if "until" in arguments:
                params["until"] = arguments["until"]

            analytics = cf.zones.analytics.dashboard.get(CLOUDFLARE_ZONE_ID, params=params)

            # Extract totals
            totals = analytics.get("totals", {})

            output = "Zone Analytics:\n" +\
                     f"Requests: {totals.get('requests', {}).get('all', 0):,}\n" +\
                     f"Bandwidth: {totals.get('bandwidth', {}).get('all', 0):,} bytes\n" +\
                     f"Threats: {totals.get('threats', {}).get('all', 0):,}\n" +\
                     f"Cached: {totals.get('requests', {}).get('cached', 0):,}\n" +\
                     f"Uncached: {totals.get('requests', {}).get('uncached', 0):,}"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_firewall_rules":
            rules = cf.zones.firewall.rules.get(CLOUDFLARE_ZONE_ID)

            if not rules:
                return [types.TextContent(type="text", text="No firewall rules found")]

            output = f"Found {len(rules)} firewall rules:\n\n"
            for rule in rules:
                action_emoji = {"block": "🚫", "challenge": "❓", "allow": "✅"}.get(rule['action'], "⚙️")
                output += f"{action_emoji} {rule['description']}\n"
                output += f"   Action: {rule['action']}\n"
                output += f"   Expression: {rule.get('filter', {}).get('expression', 'N/A')}\n\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "create_firewall_rule":
            # First create a filter
            filter_data = {
                "expression": arguments["expression"],
                "description": arguments.get("description", "Created via agent")
            }
            filter_result = cf.zones.filters.post(CLOUDFLARE_ZONE_ID, data=filter_data)

            # Then create the firewall rule
            rule_data = {
                "action": arguments["action"],
                "filter": {"id": filter_result["id"]},
                "description": arguments.get("description", "Created via agent")
            }
            rule_result = cf.zones.firewall.rules.post(CLOUDFLARE_ZONE_ID, data=rule_data)

            return [types.TextContent(
                type="text",
                text=f"✅ Firewall rule created:\n" +
                     f"Action: {rule_result['action']}\n" +
                     f"Expression: {arguments['expression']}\n" +
                     f"ID: {rule_result['id']}"
            )]

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
                server_name="cloudflare",
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
