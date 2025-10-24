"""
Learning Agent - Self-Improvement and Pattern Recognition

This agent implements self-improvement through memory analysis and reflection.
It uses Mem0 to store and retrieve past experiences, then improves decision-making.

Responsibilities:
- Analyze past agent actions and outcomes
- Identify patterns and inefficiencies
- Generate improved strategies
- Update agent knowledge base
- Implement RLSR (Reinforcement Learning from Self Reward)
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from shared.config import config
from shared.logging import get_logger
from shared.llm_router import LLMRouter, TaskType

logger = get_logger(__name__)


class LearningAgent:
    """
    Specialized agent for continuous learning and self-improvement.

    Uses MCP servers:
    - Mem0 MCP: Store and retrieve agent memories

    Implements:
    - RLSR (Reinforcement Learning from Self Reward)
    - Pattern recognition across agent actions
    - Knowledge base updates
    - Performance optimization recommendations
    """

    def __init__(self):
        self.llm_router = LLMRouter()
        self.logger = get_logger(__name__)

        # Use flagship model for complex analysis and reflection
        model = self.llm_router.route_task("policy_generation")
        self.llm = ChatAnthropic(
            model=model,
            api_key=config.anthropic.api_key,
            temperature=0.5  # Higher temperature for creative insights
        )

        self.logger.info("Learning agent initialized", model=model)

    async def _connect_mem0(self):
        """Connect to Mem0 MCP server"""
        mem0_params = StdioServerParameters(
            command="python",
            args=["mcp_servers/mem0_mcp/server.py"],
            env=None
        )
        return mem0_params

    async def execute(self, objective: str) -> Dict[str, Any]:
        """
        Execute a learning/analysis objective

        Args:
            objective: Learning task (e.g., "analyze past week", "improve X")

        Returns:
            Learning insights and recommendations
        """
        self.logger.info("Executing learning objective", objective=objective)

        try:
            mem0_params = await self._connect_mem0()

            async with stdio_client(mem0_params) as (m_read, m_write):
                async with ClientSession(m_read, m_write) as mem0:
                    await mem0.initialize()

                    # Execute learning task
                    results = await self._execute_learning_task(objective, mem0)

                    # Store learning insights
                    await mem0.call_tool("add_memory", {
                        "content": f"Learning session: {objective}. Insights: {results.get('insights', 'N/A')[:200]}",
                        "user_id": "learning_agent",
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "task_type": "learning",
                            "success": results.get("success", False)
                        }
                    })

                    return results

        except Exception as e:
            self.logger.error("Error executing learning task", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_learning_task(
        self,
        objective: str,
        mem0: ClientSession
    ) -> Dict[str, Any]:
        """Execute specific learning task"""

        if any(word in objective.lower() for word in ["analyze", "review", "summarize"]):
            return await self.analyze_past_performance(mem0)
        elif any(word in objective.lower() for word in ["improve", "optimize", "enhance"]):
            return await self.generate_improvements(mem0)
        else:
            return {
                "success": True,
                "summary": f"Learning task '{objective}' queued for analysis"
            }

    async def analyze_past_performance(self, mem0: ClientSession) -> Dict[str, Any]:
        """
        Analyze past agent actions to identify patterns

        Returns:
            Performance analysis and patterns
        """
        self.logger.info("Analyzing past performance")

        # Get all memories from the past week for each agent
        agents = ["infrastructure_agent", "monitoring_agent", "orchestrator_agent"]
        all_memories = {}

        for agent in agents:
            memories = await mem0.call_tool("get_all_memories", {
                "user_id": agent,
                "limit": 100
            })
            all_memories[agent] = memories.content[0].text if memories.content else "No memories"

        # Use LLM to analyze patterns
        system_prompt = """You are analyzing the performance of multiple autonomous agents.

Review their past actions, decisions, and outcomes to identify:
1. **Successful Patterns** - What worked well and should be reinforced
2. **Failure Patterns** - What went wrong and needs improvement
3. **Inefficiencies** - Redundant or wasteful operations
4. **Missing Capabilities** - Tasks they couldn't complete
5. **Improvement Opportunities** - Specific recommendations

Be specific and actionable. Provide concrete examples from the memory data.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Agent Memories:\n{all_memories}")
        ]

        response = await self.llm.ainvoke(messages)

        return {
            "success": True,
            "analysis": response.content,
            "agents_analyzed": agents,
            "timestamp": datetime.now().isoformat()
        }

    async def generate_improvements(self, mem0: ClientSession) -> Dict[str, Any]:
        """
        Generate specific improvement recommendations using RLSR

        RLSR (Reinforcement Learning from Self Reward):
        1. Agent reviews its own actions
        2. Assigns rewards to outcomes (self-evaluation)
        3. Generates improved strategies
        4. Updates decision policies

        Returns:
            Improvement recommendations
        """
        self.logger.info("Generating improvement recommendations")

        # First, analyze performance
        analysis = await self.analyze_past_performance(mem0)

        if not analysis["success"]:
            return analysis

        # Generate improvements based on analysis
        system_prompt = """You are implementing RLSR (Reinforcement Learning from Self Reward).

Based on the performance analysis, generate specific improvements:

1. **Updated Decision Policies**
   - What rules should change?
   - What new heuristics should be added?

2. **New Tool Combinations**
   - What sequences of MCP tools work better?
   - What cross-agent coordination is needed?

3. **Threshold Adjustments**
   - What confidence levels should change?
   - When to escalate to humans?

4. **Knowledge Base Updates**
   - What should be documented?
   - What patterns should be remembered?

Format as actionable recommendations that can be implemented.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Performance Analysis:\n{analysis['analysis']}")
        ]

        response = await self.llm.ainvoke(messages)

        return {
            "success": True,
            "improvements": response.content,
            "based_on_analysis": analysis["analysis"][:200] + "...",
            "timestamp": datetime.now().isoformat()
        }

    async def learn_from_incident(
        self,
        incident_data: Dict[str, Any],
        resolution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Learn from a resolved incident

        Args:
            incident_data: Original incident/alert
            resolution: How it was resolved

        Returns:
            Learning insights
        """
        self.logger.info("Learning from incident", incident=incident_data.get("alert_name"))

        mem0_params = await self._connect_mem0()

        async with stdio_client(mem0_params) as (m_read, m_write):
            async with ClientSession(m_read, m_write) as mem0:
                await mem0.initialize()

                # Analyze incident and resolution
                system_prompt = """You are learning from a resolved incident.

Extract key lessons:
1. Root cause identification
2. Effective resolution steps
3. Prevention strategies
4. Automation opportunities

This will be stored in agent memory for future incidents.
"""

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Incident: {incident_data}\n\nResolution: {resolution}")
                ]

                response = await self.llm.ainvoke(messages)

                # Store lesson in memory
                await mem0.call_tool("add_memory", {
                    "content": f"Incident lesson: {incident_data.get('alert_name', 'unknown')}. {response.content}",
                    "user_id": "learning_agent",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "type": "incident_lesson",
                        "alert_name": incident_data.get("alert_name"),
                        "severity": incident_data.get("severity")
                    }
                })

                return {
                    "success": True,
                    "lessons_learned": response.content,
                    "stored_in_memory": True
                }

    async def weekly_reflection(self) -> Dict[str, Any]:
        """
        Perform weekly self-reflection and improvement cycle

        This should be run as a scheduled task (e.g., via n8n)

        Returns:
            Weekly performance report and improvements
        """
        self.logger.info("Starting weekly reflection")

        mem0_params = await self._connect_mem0()

        async with stdio_client(mem0_params) as (m_read, m_write):
            async with ClientSession(m_read, m_write) as mem0:
                await mem0.initialize()

                # Analyze past week
                analysis = await self.analyze_past_performance(mem0)

                # Generate improvements
                improvements = await self.generate_improvements(mem0)

                # Create summary
                summary = await mem0.call_tool("summarize_memories", {
                    "user_id": "learning_agent"
                })

                # Compile weekly report
                report = f"""
# Weekly Agent Performance Report
**Period:** {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}

## Performance Analysis
{analysis.get('analysis', 'N/A')}

## Improvement Recommendations
{improvements.get('improvements', 'N/A')}

## Memory Summary
{summary.content[0].text if summary.content else 'N/A'}
"""

                # Store report
                await mem0.call_tool("add_memory", {
                    "content": f"Weekly reflection completed. Key insights: {analysis.get('analysis', '')[:200]}",
                    "user_id": "learning_agent",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "type": "weekly_reflection",
                        "period": "7_days"
                    }
                })

                return {
                    "success": True,
                    "report": report,
                    "timestamp": datetime.now().isoformat()
                }


# Main entry point for testing
async def main():
    """Test the learning agent"""
    agent = LearningAgent()

    # Test: Analyze past performance
    print("=== Testing Performance Analysis ===")
    result = await agent.execute("Analyze past performance")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Analysis: {result.get('analysis', 'N/A')[:300]}")

    # Test: Generate improvements
    print("\n=== Testing Improvement Generation ===")
    result = await agent.execute("Generate improvement recommendations")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Improvements: {result.get('improvements', 'N/A')[:300]}")


if __name__ == "__main__":
    asyncio.run(main())
