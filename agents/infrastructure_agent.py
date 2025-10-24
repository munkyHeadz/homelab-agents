"""
Infrastructure Agent - VM, Container, and Resource Management

This agent manages Proxmox VE infrastructure and Docker containers.
It uses MCP servers to interact with Proxmox and Docker APIs.

Responsibilities:
- VM/LXC lifecycle management (create, start, stop, delete)
- Resource monitoring and optimization
- Automated scaling decisions
- Backup coordination
- Container orchestration
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
from shared.metrics import get_metrics_collector

logger = get_logger(__name__)


class InfrastructureAgent:
    """
    Specialized agent for infrastructure management.

    Uses MCP servers:
    - Proxmox MCP: VM/LXC management
    - Docker MCP: Container management
    - Mem0 MCP: Remember infrastructure patterns and decisions
    """

    def __init__(self):
        self.llm_router = LLMRouter()
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector("infrastructure_agent")

        # Use balanced model for infrastructure tasks
        model = self.llm_router.route_task("infrastructure_planning")
        self.llm = ChatAnthropic(
            model=model,
            api_key=config.anthropic.api_key,
            temperature=0.2  # Low temperature for consistent infrastructure decisions
        )

        self.logger.info("Infrastructure agent initialized", model=model)
        self.metrics.set_health_status(True)

    async def _connect_mcp_servers(self):
        """Connect to required MCP servers"""
        # Pass environment variables to MCP servers
        import os
        import sys
        env = os.environ.copy()

        # Use the Python interpreter that's currently running (from venv)
        python_path = sys.executable

        # Proxmox MCP
        proxmox_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/proxmox_mcp/server.py"],
            env=env
        )

        # Docker MCP
        docker_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/docker_mcp/server.py"],
            env=env
        )

        # Mem0 MCP for memory (disabled - needs Qdrant or pgvector setup)
        # mem0_params = StdioServerParameters(
        #     command="python",
        #     args=["mcp_servers/mem0_mcp/server.py"],
        #     env=env
        # )

        return proxmox_params, docker_params

    async def execute(self, objective: str) -> Dict[str, Any]:
        """
        Execute an infrastructure management objective

        Args:
            objective: High-level infrastructure task

        Returns:
            Results of the execution
        """
        import time
        start_time = time.time()

        self.logger.info("Executing infrastructure objective", objective=objective)
        self.metrics.record_task_start("infrastructure_execution")

        try:
            # Connect to MCP servers
            proxmox_params, docker_params = await self._connect_mcp_servers()

            async with stdio_client(proxmox_params) as (p_read, p_write), \
                       stdio_client(docker_params) as (d_read, d_write):

                async with ClientSession(p_read, p_write) as proxmox, \
                           ClientSession(d_read, d_write) as docker:

                    # Initialize all sessions
                    await proxmox.initialize()
                    await docker.initialize()

                    # Record MCP connections
                    self.metrics.record_mcp_connection("proxmox", True)
                    self.metrics.record_mcp_connection("docker", True)

                    # Get available tools
                    proxmox_tools = await proxmox.list_tools()
                    docker_tools = await docker.list_tools()

                    # Build context for LLM
                    system_prompt = f"""You are the Infrastructure Agent for a homelab automation system.

You have access to the following tools via MCP servers:

**Proxmox Tools:**
{self._format_tools(proxmox_tools.tools)}

**Docker Tools:**
{self._format_tools(docker_tools.tools)}

Your objective: {objective}

Analyze the objective and determine which tools to use. Then execute them in the correct order.

IMPORTANT:
- Always check current state before making changes
- For monitoring tasks, gather data from all relevant sources
- Store important observations in memory for future reference
- Return results in a structured format
- If the task is destructive (delete, stop), provide clear warnings

Think step by step:
1. What information do I need to gather first?
2. Which tools should I use?
3. In what order should I execute them?
4. What should I store in memory?
5. What should I return to the user?
"""

                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=f"Execute: {objective}")
                    ]

                    # Get LLM's plan
                    response = await self.llm.ainvoke(messages)
                    plan = response.content

                    self.logger.info("Generated execution plan", plan=plan[:200])

                    # Execute the plan (simplified - real implementation would parse and execute)
                    results = await self._execute_plan(
                        plan, objective, proxmox, docker, mem0=None
                    )

                    # Store outcome in memory (disabled - mem0 needs Qdrant or pgvector)
                    # await mem0.call_tool("add_memory", {
                    #     "content": f"Infrastructure task completed: {objective}. Results: {results.get('summary', 'N/A')}",
                    #     "user_id": "infrastructure_agent",
                    #     "metadata": {
                    #         "timestamp": datetime.now().isoformat(),
                    #         "task_type": "infrastructure",
                    #         "success": results.get("success", False)
                    #     }
                    # })

                    # Record success metrics
                    duration = time.time() - start_time
                    self.metrics.record_task_success("infrastructure_execution", duration)

                    return results

        except Exception as e:
            self.logger.error("Error executing infrastructure task", error=str(e))
            self.metrics.record_task_failure("infrastructure_execution", type(e).__name__)
            self.metrics.set_health_status(False)
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_plan(
        self,
        plan: str,
        objective: str,
        proxmox: ClientSession,
        docker: ClientSession,
        mem0: ClientSession = None
    ) -> Dict[str, Any]:
        """
        Execute the generated plan

        This is a simplified version - a real implementation would:
        1. Parse the plan into discrete steps
        2. Execute each tool call
        3. Handle errors and retries
        4. Chain results between steps
        """

        results = {
            "success": True,
            "actions_taken": [],
            "data_collected": {},
            "summary": ""
        }

        # Example: If objective contains "status" or "list", gather information
        if any(word in objective.lower() for word in ["status", "list", "show", "check"]):
            # List VMs
            vm_result = await proxmox.call_tool("list_vms", {"type": "all"})
            results["data_collected"]["vms"] = vm_result.content[0].text if vm_result.content else "No data"
            results["actions_taken"].append("Listed all VMs and containers")

            # List containers
            container_result = await docker.call_tool("list_containers", {"all": True})
            results["data_collected"]["containers"] = container_result.content[0].text if container_result.content else "No data"
            results["actions_taken"].append("Listed all Docker containers")

            # Get node status
            node_result = await proxmox.call_tool("get_node_status", {})
            results["data_collected"]["node_status"] = node_result.content[0].text if node_result.content else "No data"
            results["actions_taken"].append("Retrieved Proxmox node status")

            results["summary"] = f"Gathered infrastructure status: {len(results['actions_taken'])} actions completed"

        # Example: If objective contains "create" or "deploy"
        elif any(word in objective.lower() for word in ["create", "deploy", "start"]):
            results["summary"] = "Creation/deployment tasks require specific parameters"
            results["success"] = False
            results["error"] = "Need more details: VM ID, container name, resource specs, etc."

        # Default: Return plan for human review
        else:
            results["summary"] = f"Analyzed objective. Recommended plan: {plan[:200]}"
            results["requires_approval"] = True

        return results

    def _format_tools(self, tools: List[Any]) -> str:
        """Format MCP tools for LLM context"""
        formatted = []
        for tool in tools:
            formatted.append(f"- {tool.name}: {tool.description}")
        return "\n".join(formatted)

    async def monitor_resources(self) -> Dict[str, Any]:
        """
        Continuous resource monitoring task

        Returns:
            Current resource usage and recommendations
        """
        self.logger.info("Starting resource monitoring")

        try:
            proxmox_params, docker_params = await self._connect_mcp_servers()

            async with stdio_client(proxmox_params) as (p_read, p_write), \
                       stdio_client(docker_params) as (d_read, d_write):

                async with ClientSession(p_read, p_write) as proxmox, \
                           ClientSession(d_read, d_write) as docker:

                    await proxmox.initialize()
                    await docker.initialize()

                    # Get node status
                    node_status = await proxmox.call_tool("get_node_status", {})

                    # Get cluster resources
                    cluster_resources = await proxmox.call_tool("get_cluster_resources", {})

                    # Get Docker system info
                    docker_info = await docker.call_tool("get_system_info", {})

                    # Analyze and return
                    return {
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "proxmox_node": node_status.content[0].text if node_status.content else "N/A",
                        "cluster": cluster_resources.content[0].text if cluster_resources.content else "N/A",
                        "docker": docker_info.content[0].text if docker_info.content else "N/A"
                    }

        except Exception as e:
            self.logger.error("Error monitoring resources", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def optimize_resources(self) -> Dict[str, Any]:
        """
        Analyze resource usage and suggest optimizations

        Returns:
            Optimization recommendations
        """
        self.logger.info("Analyzing resource optimization opportunities")

        # Get current resource state
        current_state = await self.monitor_resources()

        if not current_state["success"]:
            return current_state

        # Use LLM to analyze and recommend
        system_prompt = """You are analyzing homelab infrastructure resource usage.

Based on the current state, provide recommendations for:
1. Underutilized resources that could be reclaimed
2. Overutilized resources that need scaling
3. Cost optimization opportunities
4. Performance improvements

Be specific and actionable.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Current state:\n{current_state}")
        ]

        response = await self.llm.ainvoke(messages)

        return {
            "success": True,
            "current_state": current_state,
            "recommendations": response.content,
            "timestamp": datetime.now().isoformat()
        }


# Main entry point for testing
async def main():
    """Test the infrastructure agent"""
    agent = InfrastructureAgent()

    # Test: Monitor resources
    print("=== Testing Resource Monitoring ===")
    result = await agent.monitor_resources()
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Proxmox: {result.get('proxmox_node', 'N/A')[:200]}")
        print(f"Docker: {result.get('docker', 'N/A')[:200]}")

    # Test: Execute objective
    print("\n=== Testing Objective Execution ===")
    result = await agent.execute("Check the status of all VMs and containers")
    print(f"Success: {result['success']}")
    print(f"Summary: {result.get('summary', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
