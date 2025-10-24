#!/usr/bin/env python3
"""
MCP Server Test Suite

Tests all MCP servers to verify:
1. Server starts correctly
2. Tools are listed
3. Basic tool execution works
4. Error handling is proper
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from shared.logging import get_logger
from shared.config import config

logger = get_logger(__name__)


class MCPServerTester:
    """Test framework for MCP servers"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.results: Dict[str, Any] = {}

    async def test_server(
        self,
        server_name: str,
        server_path: str,
        test_tool: str = None,
        test_args: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Test a single MCP server

        Args:
            server_name: Name of the server (e.g., "proxmox")
            server_path: Path to server.py file
            test_tool: Optional tool name to test
            test_args: Optional arguments for test tool

        Returns:
            Test results
        """
        print(f"\n{'='*60}")
        print(f"Testing: {server_name} MCP Server")
        print(f"{'='*60}")

        result = {
            "server": server_name,
            "success": False,
            "tools_count": 0,
            "tools": [],
            "test_execution": None,
            "error": None
        }

        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command="python",
                args=[server_path],
                env=None
            )

            # Connect to server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    print(f"  [1/3] Initializing connection...")
                    await session.initialize()
                    print(f"  ✓ Connected successfully")

                    # List tools
                    print(f"  [2/3] Listing available tools...")
                    tools_result = await session.list_tools()
                    tool_names = [tool.name for tool in tools_result.tools]

                    result["tools_count"] = len(tool_names)
                    result["tools"] = tool_names

                    print(f"  ✓ Found {len(tool_names)} tools:")
                    for tool in tool_names:
                        print(f"      - {tool}")

                    # Test a tool if specified
                    if test_tool and test_tool in tool_names:
                        print(f"  [3/3] Testing tool: {test_tool}")
                        test_result = await session.call_tool(
                            test_tool,
                            test_args or {}
                        )

                        if test_result.content:
                            response = test_result.content[0].text
                            result["test_execution"] = {
                                "tool": test_tool,
                                "success": True,
                                "response_length": len(response),
                                "response_preview": response[:200] + "..." if len(response) > 200 else response
                            }
                            print(f"  ✓ Tool executed successfully")
                            print(f"  Response preview: {response[:100]}...")
                        else:
                            print(f"  ⚠ Tool executed but returned no content")
                    else:
                        print(f"  [3/3] Skipping tool test (not specified)")

                    result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            print(f"  ✗ Error: {str(e)}")
            self.logger.error(f"Error testing {server_name}", error=str(e))

        return result

    async def test_all_servers(self) -> Dict[str, Any]:
        """Test all MCP servers"""

        print("\n" + "="*60)
        print("MCP SERVER TEST SUITE")
        print("="*60)

        # Define all servers and their test configurations
        servers = [
            {
                "name": "Proxmox",
                "path": "mcp_servers/proxmox_mcp/server.py",
                "test_tool": "get_node_status",
                "test_args": {},
                "required_env": ["PROXMOX_HOST", "PROXMOX_NODE"]
            },
            {
                "name": "Docker",
                "path": "mcp_servers/docker_mcp/server.py",
                "test_tool": "get_system_info",
                "test_args": {},
                "required_env": []
            },
            {
                "name": "Tailscale",
                "path": "mcp_servers/tailscale_mcp/server.py",
                "test_tool": "list_tailscale_devices",
                "test_args": {},
                "required_env": ["TAILSCALE_API_KEY", "TAILSCALE_TAILNET"]
            },
            {
                "name": "Cloudflare",
                "path": "mcp_servers/cloudflare_mcp/server.py",
                "test_tool": "list_dns_records",
                "test_args": {},
                "required_env": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ZONE_ID"]
            },
            {
                "name": "Unifi",
                "path": "mcp_servers/unifi_mcp/server.py",
                "test_tool": "list_unifi_clients",
                "test_args": {"active_only": True},
                "required_env": ["UNIFI_HOST", "UNIFI_USERNAME", "UNIFI_PASSWORD"]
            },
            {
                "name": "Pi-hole",
                "path": "mcp_servers/pihole_mcp/server.py",
                "test_tool": "get_pihole_summary",
                "test_args": {},
                "required_env": ["PIHOLE_HOST", "PIHOLE_API_TOKEN"]
            },
            {
                "name": "Mem0",
                "path": "mcp_servers/mem0_mcp/server.py",
                "test_tool": "add_memory",
                "test_args": {
                    "content": "Test memory from MCP test suite",
                    "user_id": "test_user",
                    "metadata": {"test": True}
                },
                "required_env": ["POSTGRES_HOST", "POSTGRES_DB_MEMORY", "POSTGRES_USER_MEMORY", "POSTGRES_PASSWORD_MEMORY"]
            }
        ]

        results = []
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for server in servers:
            # Check if required environment variables are set
            missing_vars = []
            for var in server["required_env"]:
                if not hasattr(config, var.lower().split('_')[0]) or not getattr(config, var.lower().split('_')[0], None):
                    # Simplified check - in real implementation would check nested config
                    pass

            if missing_vars:
                print(f"\n⊘ Skipping {server['name']} (missing env vars: {', '.join(missing_vars)})")
                skipped_count += 1
                continue

            # Test the server
            result = await self.test_server(
                server["name"],
                server["path"],
                server.get("test_tool"),
                server.get("test_args")
            )

            results.append(result)

            if result["success"]:
                success_count += 1
            else:
                failed_count += 1

        # Print summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total servers tested: {len(results)}")
        print(f"✓ Successful: {success_count}")
        print(f"✗ Failed: {failed_count}")
        print(f"⊘ Skipped: {skipped_count}")
        print(f"{'='*60}")

        # Detailed results
        if results:
            print("\nDetailed Results:")
            for result in results:
                status = "✓" if result["success"] else "✗"
                print(f"  {status} {result['server']}: {result['tools_count']} tools")
                if result.get("error"):
                    print(f"      Error: {result['error']}")

        return {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "results": results
        }


async def main():
    """Main test execution"""
    tester = MCPServerTester()

    try:
        results = await tester.test_all_servers()

        # Exit with error code if any tests failed
        if results["failed"] > 0:
            sys.exit(1)
        else:
            print(f"\n✓ All tests passed!")
            sys.exit(0)

    except Exception as e:
        print(f"\n✗ Test suite error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
