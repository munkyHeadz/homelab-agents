"""
Monitoring Agent - Network Monitoring, Alerts, and Incident Response

This agent monitors homelab network infrastructure and responds to issues.
It uses MCP servers to interact with network services and security tools.

Responsibilities:
- Network health monitoring (Unifi, Tailscale, Cloudflare)
- DNS management (Pi-hole, Cloudflare)
- Alert analysis and triage
- Automated incident response
- Security policy enforcement
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from shared.config import config
from shared.logging import get_logger
from shared.llm_router import LLMRouter, TaskType

logger = get_logger(__name__)


class MonitoringAgent:
    """
    Specialized agent for network monitoring and incident response.

    Uses MCP servers:
    - Unifi MCP: Network devices, clients, firewall
    - Tailscale MCP: VPN network status
    - Cloudflare MCP: DNS, CDN, WAF
    - Pi-hole MCP: DNS ad blocking, queries
    - Mem0 MCP: Remember incidents and resolutions
    """

    def __init__(self):
        self.llm_router = LLMRouter()
        self.logger = get_logger(__name__)

        # Use balanced model for monitoring tasks
        model = self.llm_router.route_task("incident_analysis")
        self.llm = ChatAnthropic(
            model=model,
            api_key=config.anthropic.api_key,
            temperature=0.3  # Moderate temperature for analysis
        )

        self.logger.info("Monitoring agent initialized", model=model)

    async def _connect_mcp_servers(self):
        """Connect to required MCP servers"""
        import sys

        # Use the Python interpreter that's currently running (from venv)
        python_path = sys.executable

        # Unifi MCP
        unifi_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/unifi_mcp/server.py"],
            env=None
        )

        # Tailscale MCP
        tailscale_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/tailscale_mcp/server.py"],
            env=None
        )

        # Cloudflare MCP
        cloudflare_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/cloudflare_mcp/server.py"],
            env=None
        )

        # Pi-hole MCP
        pihole_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/pihole_mcp/server.py"],
            env=None
        )

        # Mem0 MCP
        mem0_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/mem0_mcp/server.py"],
            env=None
        )

        return unifi_params, tailscale_params, cloudflare_params, pihole_params, mem0_params

    async def execute(self, objective: str) -> Dict[str, Any]:
        """
        Execute a monitoring/network management objective

        Args:
            objective: High-level monitoring task

        Returns:
            Results of the execution
        """
        self.logger.info("Executing monitoring objective", objective=objective)

        try:
            # Connect to MCP servers
            params = await self._connect_mcp_servers()
            unifi_p, tailscale_p, cloudflare_p, pihole_p, mem0_p = params

            async with stdio_client(unifi_p) as (u_read, u_write), \
                       stdio_client(tailscale_p) as (t_read, t_write), \
                       stdio_client(cloudflare_p) as (c_read, c_write), \
                       stdio_client(pihole_p) as (p_read, p_write), \
                       stdio_client(mem0_p) as (m_read, m_write):

                async with ClientSession(u_read, u_write) as unifi, \
                           ClientSession(t_read, t_write) as tailscale, \
                           ClientSession(c_read, c_write) as cloudflare, \
                           ClientSession(p_read, p_write) as pihole, \
                           ClientSession(m_read, m_write) as mem0:

                    # Initialize all sessions
                    await unifi.initialize()
                    await tailscale.initialize()
                    await cloudflare.initialize()
                    await pihole.initialize()
                    await mem0.initialize()

                    # Execute monitoring task
                    results = await self._execute_monitoring_task(
                        objective, unifi, tailscale, cloudflare, pihole, mem0
                    )

                    # Store outcome in memory
                    await mem0.call_tool("add_memory", {
                        "content": f"Monitoring task completed: {objective}. Results: {results.get('summary', 'N/A')}",
                        "user_id": "monitoring_agent",
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "task_type": "monitoring",
                            "success": results.get("success", False)
                        }
                    })

                    return results

        except Exception as e:
            self.logger.error("Error executing monitoring task", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_monitoring_task(
        self,
        objective: str,
        unifi: ClientSession,
        tailscale: ClientSession,
        cloudflare: ClientSession,
        pihole: ClientSession,
        mem0: ClientSession
    ) -> Dict[str, Any]:
        """Execute monitoring task based on objective"""

        results = {
            "success": True,
            "actions_taken": [],
            "data_collected": {},
            "summary": ""
        }

        # Network health check
        if any(word in objective.lower() for word in ["health", "status", "check", "monitor"]):
            # Unifi network stats
            unifi_stats = await unifi.call_tool("get_network_stats", {})
            results["data_collected"]["unifi"] = unifi_stats.content[0].text if unifi_stats.content else "N/A"
            results["actions_taken"].append("Retrieved Unifi network statistics")

            # Tailscale devices
            tailscale_devices = await tailscale.call_tool("list_tailscale_devices", {})
            results["data_collected"]["tailscale"] = tailscale_devices.content[0].text if tailscale_devices.content else "N/A"
            results["actions_taken"].append("Listed Tailscale devices")

            # Pi-hole summary
            pihole_summary = await pihole.call_tool("get_pihole_summary", {})
            results["data_collected"]["pihole"] = pihole_summary.content[0].text if pihole_summary.content else "N/A"
            results["actions_taken"].append("Retrieved Pi-hole statistics")

            # Cloudflare analytics
            cf_analytics = await cloudflare.call_tool("get_zone_analytics", {})
            results["data_collected"]["cloudflare"] = cf_analytics.content[0].text if cf_analytics.content else "N/A"
            results["actions_taken"].append("Retrieved Cloudflare analytics")

            results["summary"] = f"Network health check completed: {len(results['actions_taken'])} data sources"

        # Client management
        elif any(word in objective.lower() for word in ["client", "device", "user"]):
            # List clients
            clients = await unifi.call_tool("list_unifi_clients", {"active_only": True})
            results["data_collected"]["clients"] = clients.content[0].text if clients.content else "N/A"
            results["actions_taken"].append("Listed active network clients")

            results["summary"] = "Retrieved client information"

        # DNS management
        elif any(word in objective.lower() for word in ["dns", "domain", "resolve"]):
            # Pi-hole stats
            pihole_summary = await pihole.call_tool("get_pihole_summary", {})
            results["data_collected"]["pihole_dns"] = pihole_summary.content[0].text if pihole_summary.content else "N/A"

            # Cloudflare DNS
            cf_dns = await cloudflare.call_tool("list_dns_records", {})
            results["data_collected"]["cloudflare_dns"] = cf_dns.content[0].text if cf_dns.content else "N/A"

            results["actions_taken"].append("Retrieved DNS configuration")
            results["summary"] = "DNS status retrieved from Pi-hole and Cloudflare"

        else:
            results["summary"] = f"Objective '{objective}' requires more specific parameters"

        return results

    async def analyze_incident(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an alert/incident and determine response

        Args:
            alert_data: Alert information from Prometheus/monitoring system

        Returns:
            Analysis and recommended actions
        """
        self.logger.info("Analyzing incident", alert=alert_data.get("alert_name"))

        # Search memory for similar past incidents
        params = await self._connect_mcp_servers()
        mem0_p = params[4]

        async with stdio_client(mem0_p) as (m_read, m_write):
            async with ClientSession(m_read, m_write) as mem0:
                await mem0.initialize()

                # Search for similar incidents
                search_query = f"incident similar to {alert_data.get('alert_name', 'unknown')} {alert_data.get('description', '')}"
                similar_incidents = await mem0.call_tool("search_memories", {
                    "query": search_query,
                    "user_id": "monitoring_agent",
                    "limit": 3
                })

                # Analyze with LLM
                system_prompt = """You are analyzing a network/infrastructure incident.

Based on the alert data and similar past incidents, determine:
1. Severity (critical, high, medium, low)
2. Root cause hypothesis
3. Immediate actions to take
4. Whether to escalate to human operator

Provide a structured analysis with clear action items.
"""

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Alert: {alert_data}\n\nSimilar past incidents: {similar_incidents.content[0].text if similar_incidents.content else 'None found'}")
                ]

                response = await self.llm.ainvoke(messages)

                # Store this incident in memory
                await mem0.call_tool("add_memory", {
                    "content": f"Incident: {alert_data.get('alert_name')}. Analysis: {response.content[:200]}",
                    "user_id": "monitoring_agent",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "alert_name": alert_data.get("alert_name"),
                        "severity": "unknown"  # Would parse from LLM response
                    }
                })

                return {
                    "success": True,
                    "alert": alert_data,
                    "analysis": response.content,
                    "similar_incidents": similar_incidents.content[0].text if similar_incidents.content else "None",
                    "timestamp": datetime.now().isoformat()
                }

    async def auto_remediate(self, incident_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically remediate common issues

        Args:
            incident_analysis: Results from analyze_incident()

        Returns:
            Remediation actions taken
        """
        self.logger.info("Attempting auto-remediation")

        # Parse recommended actions from analysis
        # This is simplified - real implementation would parse structured output

        actions_taken = []

        # Example remediations:
        # 1. Restart failed containers
        # 2. Clear DNS cache
        # 3. Reboot problematic network devices
        # 4. Block malicious IPs
        # 5. Update firewall rules

        # For now, return that remediation would happen
        return {
            "success": True,
            "actions_taken": actions_taken,
            "requires_human_approval": True,  # Most remediations need approval
            "timestamp": datetime.now().isoformat()
        }


# Main entry point for testing
async def main():
    """Test the monitoring agent"""
    agent = MonitoringAgent()

    # Test: Network health check
    print("=== Testing Network Health Check ===")
    result = await agent.execute("Check network health status")
    print(f"Success: {result['success']}")
    print(f"Summary: {result.get('summary', 'N/A')}")
    print(f"Actions: {result.get('actions_taken', [])}")

    # Test: Incident analysis
    print("\n=== Testing Incident Analysis ===")
    alert = {
        "alert_name": "HighMemoryUsage",
        "description": "Node memory usage above 90%",
        "severity": "warning",
        "labels": {"node": "proxmox-01"}
    }
    result = await agent.analyze_incident(alert)
    print(f"Success: {result['success']}")
    print(f"Analysis: {result.get('analysis', 'N/A')[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
