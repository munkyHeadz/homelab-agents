"""
Orchestrator Agent - Central Coordinator for Homelab Automation

This agent coordinates all specialized agents using LangGraph.
It receives high-level objectives and delegates tasks to appropriate agents.

Responsibilities:
- Route tasks to specialized agents
- Coordinate multi-agent workflows
- Maintain conversation state
- Handle human-in-the-loop approvals
- Aggregate results from multiple agents
"""

import os
import asyncio
from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from shared.config import config
from shared.logging import get_logger
from shared.llm_router import LLMRouter, TaskType

logger = get_logger(__name__)


# Graph State Definition
class AgentState(TypedDict):
    """State shared across all agents in the graph"""
    messages: Annotated[Sequence[BaseMessage], "Conversation history"]
    task_type: str
    objective: str
    current_agent: str
    results: Dict[str, Any]
    requires_approval: bool
    approved: bool
    error: str | None
    iteration: int
    max_iterations: int


class OrchestratorAgent:
    """
    Central orchestrator using LangGraph for multi-agent coordination.

    Architecture:
    - Receives user objectives
    - Analyzes task requirements
    - Routes to specialized agents
    - Aggregates results
    - Requests human approval when needed
    """

    def __init__(self):
        self.llm_router = LLMRouter()
        self.logger = get_logger(__name__)

        # Initialize flagship model for orchestration
        self.llm = ChatAnthropic(
            model=config.anthropic.flagship_model,
            api_key=config.anthropic.api_key,
            temperature=0.3  # Lower temperature for more deterministic routing
        )

        # PostgreSQL checkpoint saver for state persistence
        # Note: Checkpointing is disabled for now to simplify initial deployment
        # TODO: Re-enable after setting up agent_checkpoints database schema
        self.checkpointer = None

        # Build the agent graph
        self.graph = self._build_graph()

        self.logger.info("Orchestrator agent initialized", model=config.anthropic.flagship_model)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine for agent orchestration"""

        workflow = StateGraph(AgentState)

        # Add nodes (agent steps)
        workflow.add_node("analyze_task", self._analyze_task)
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("execute_infrastructure", self._execute_infrastructure)
        workflow.add_node("execute_monitoring", self._execute_monitoring)
        workflow.add_node("execute_learning", self._execute_learning)
        workflow.add_node("check_approval", self._check_approval)
        workflow.add_node("aggregate_results", self._aggregate_results)

        # Set entry point
        workflow.set_entry_point("analyze_task")

        # Add edges (transitions)
        workflow.add_edge("analyze_task", "route_to_agent")

        # Conditional routing based on task type
        workflow.add_conditional_edges(
            "route_to_agent",
            self._determine_agent,
            {
                "infrastructure": "execute_infrastructure",
                "monitoring": "execute_monitoring",
                "learning": "execute_learning",
                "aggregate": "aggregate_results"
            }
        )

        # Agent execution flows
        workflow.add_edge("execute_infrastructure", "check_approval")
        workflow.add_edge("execute_monitoring", "check_approval")
        workflow.add_edge("execute_learning", "aggregate_results")

        # Approval flow
        workflow.add_conditional_edges(
            "check_approval",
            self._should_request_approval,
            {
                "approved": "aggregate_results",
                "pending": END,  # Wait for human approval
                "rejected": END
            }
        )

        workflow.add_edge("aggregate_results", END)

        # Compile without checkpointer for now (will add back after schema setup)
        return workflow.compile()

    async def _analyze_task(self, state: AgentState) -> AgentState:
        """Analyze the user's objective and determine requirements"""
        self.logger.info("Analyzing task", objective=state["objective"])

        system_prompt = """You are the Orchestrator Agent for a homelab automation system.

Your role is to analyze user objectives and determine:
1. What type of task this is (infrastructure, monitoring, learning, multi-agent)
2. Which specialized agents should handle it
3. Whether human approval is required (high-risk operations)

Available agents:
- Infrastructure Agent: VM/container management, Proxmox, Docker
- Monitoring Agent: Network monitoring, alerts, Unifi, Pi-hole, Tailscale
- Learning Agent: Memory management, pattern analysis, self-improvement

High-risk operations requiring approval:
- Deleting VMs or containers
- Modifying firewall rules
- Changing DNS settings
- Updating ACLs
- Any destructive operation

Respond with JSON:
{
    "task_type": "infrastructure|monitoring|learning|multi_agent",
    "agents_needed": ["agent1", "agent2"],
    "requires_approval": true|false,
    "risk_level": "low|medium|high",
    "reasoning": "explanation"
}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Objective: {state['objective']}")
        ]

        response = await self.llm.ainvoke(messages)

        # Parse response
        import json
        try:
            # Extract JSON from response
            content = response.content if isinstance(response.content, str) else str(response.content)

            # Try to find JSON in the response
            if "```json" in content:
                # Extract JSON from markdown code block
                json_str = content.split("```json")[1].split("```")[0].strip()
                analysis = json.loads(json_str)
            elif "{" in content:
                # Try to find JSON object
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                analysis = json.loads(json_str)
            else:
                # Default analysis if JSON parsing fails
                analysis = {
                    "task_type": "infrastructure",  # Default to infrastructure for Proxmox tasks
                    "agents_needed": ["infrastructure"],
                    "requires_approval": False,
                    "risk_level": "low",
                    "reasoning": "Defaulted to infrastructure agent"
                }
        except Exception as e:
            self.logger.warning(f"Failed to parse LLM response as JSON: {e}, using default")
            analysis = {
                "task_type": "infrastructure",
                "agents_needed": ["infrastructure"],
                "requires_approval": False,
                "risk_level": "low",
                "reasoning": "JSON parsing failed, defaulted to infrastructure"
            }

        state["task_type"] = analysis.get("task_type", "infrastructure")
        state["requires_approval"] = analysis.get("requires_approval", False)
        state["results"]["analysis"] = analysis

        self.logger.info(
            "Task analysis complete",
            task_type=state["task_type"],
            requires_approval=state["requires_approval"]
        )

        return state

    async def _route_to_agent(self, state: AgentState) -> AgentState:
        """Route task to appropriate specialized agent"""
        self.logger.info("Routing task", task_type=state["task_type"])
        return state

    def _determine_agent(self, state: AgentState) -> str:
        """Determine which agent node to execute next"""
        task_type = state["task_type"]

        if task_type == "infrastructure":
            return "infrastructure"
        elif task_type == "monitoring":
            return "monitoring"
        elif task_type == "learning":
            return "learning"
        else:
            return "aggregate"

    async def _execute_infrastructure(self, state: AgentState) -> AgentState:
        """Execute infrastructure agent tasks"""
        self.logger.info("Executing infrastructure agent")

        # Import here to avoid circular dependency
        from agents.infrastructure_agent import InfrastructureAgent

        infra_agent = InfrastructureAgent()
        result = await infra_agent.execute(state["objective"])

        state["results"]["infrastructure"] = result
        state["current_agent"] = "infrastructure"

        return state

    async def _execute_monitoring(self, state: AgentState) -> AgentState:
        """Execute monitoring agent tasks"""
        self.logger.info("Executing monitoring agent")

        # Import here to avoid circular dependency
        from agents.monitoring_agent import MonitoringAgent

        monitoring_agent = MonitoringAgent()
        result = await monitoring_agent.execute(state["objective"])

        state["results"]["monitoring"] = result
        state["current_agent"] = "monitoring"

        return state

    async def _execute_learning(self, state: AgentState) -> AgentState:
        """Execute learning agent tasks"""
        self.logger.info("Executing learning agent")

        # Import here to avoid circular dependency
        from agents.learning_agent import LearningAgent

        learning_agent = LearningAgent()
        result = await learning_agent.execute(state["objective"])

        state["results"]["learning"] = result
        state["current_agent"] = "learning"

        return state

    async def _check_approval(self, state: AgentState) -> AgentState:
        """Check if human approval is needed"""
        if state["requires_approval"] and not state.get("approved", False):
            self.logger.warning(
                "Task requires human approval",
                task_type=state["task_type"],
                agent=state["current_agent"]
            )
            # Send notification via Telegram (integrated via n8n)
            await self._request_human_approval(state)

        return state

    def _should_request_approval(self, state: AgentState) -> str:
        """Determine approval flow"""
        if not state["requires_approval"]:
            return "approved"
        elif state.get("approved", False):
            return "approved"
        elif state.get("approved") is False:
            return "rejected"
        else:
            return "pending"

    async def _aggregate_results(self, state: AgentState) -> AgentState:
        """Aggregate results from all agents"""
        self.logger.info("Aggregating results")

        summary_prompt = f"""Summarize the results of this task execution:

Objective: {state['objective']}
Task Type: {state['task_type']}
Agents Executed: {list(state['results'].keys())}

Results:
{state['results']}

Provide a concise summary for the user highlighting:
1. What was accomplished
2. Any issues encountered
3. Next recommended actions
"""

        messages = [HumanMessage(content=summary_prompt)]
        response = await self.llm.ainvoke(messages)

        state["results"]["summary"] = response.content
        state["messages"].append(AIMessage(content=response.content))

        self.logger.info("Task execution complete", summary=response.content[:200])

        return state

    async def _request_human_approval(self, state: AgentState):
        """Request human approval via Telegram"""
        # This would integrate with n8n workflow to send Telegram message
        approval_message = f"""
🤖 **Approval Required**

**Task:** {state['objective']}
**Agent:** {state['current_agent']}
**Risk Level:** {state['results'].get('analysis', {}).get('risk_level', 'unknown')}

**Planned Actions:**
{state['results'].get(state['current_agent'], {})}

Reply with:
- `/approve` to proceed
- `/reject` to cancel
- `/details` for more information
"""

        # TODO: Send via n8n webhook
        self.logger.info("Approval request sent", message=approval_message)

    async def execute(self, objective: str, thread_id: str = None) -> Dict[str, Any]:
        """
        Execute an objective through the agent graph

        Args:
            objective: High-level user objective
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Results from agent execution
        """
        if not thread_id:
            thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        initial_state: AgentState = {
            "messages": [HumanMessage(content=objective)],
            "task_type": "",
            "objective": objective,
            "current_agent": "",
            "results": {},
            "requires_approval": False,
            "approved": False,
            "error": None,
            "iteration": 0,
            "max_iterations": 10
        }

        config_dict = {"configurable": {"thread_id": thread_id}}

        try:
            # Execute the graph
            final_state = await self.graph.ainvoke(initial_state, config_dict)

            return {
                "success": True,
                "results": final_state["results"],
                "summary": final_state["results"].get("summary"),
                "thread_id": thread_id
            }

        except Exception as e:
            self.logger.error("Error executing objective", error=str(e), objective=objective)
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id
            }

    async def resume(self, thread_id: str, approval_status: bool) -> Dict[str, Any]:
        """
        Resume a workflow after human approval/rejection

        Args:
            thread_id: Thread ID of the paused workflow
            approval_status: True if approved, False if rejected

        Returns:
            Results from continued execution
        """
        config_dict = {"configurable": {"thread_id": thread_id}}

        # Get current state
        snapshot = await self.graph.aget_state(config_dict)
        current_state = snapshot.values

        # Update approval status
        current_state["approved"] = approval_status

        if not approval_status:
            self.logger.info("Task rejected by human", thread_id=thread_id)
            return {
                "success": False,
                "message": "Task rejected by human operator",
                "thread_id": thread_id
            }

        # Resume execution
        try:
            final_state = await self.graph.ainvoke(current_state, config_dict)

            return {
                "success": True,
                "results": final_state["results"],
                "summary": final_state["results"].get("summary"),
                "thread_id": thread_id
            }

        except Exception as e:
            self.logger.error("Error resuming workflow", error=str(e), thread_id=thread_id)
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id
            }


# Main entry point for testing
async def main():
    """Test the orchestrator agent"""
    orchestrator = OrchestratorAgent()

    # Example objective
    objective = "Check the status of all VMs and containers in Proxmox"

    result = await orchestrator.execute(objective)

    print(f"Success: {result['success']}")
    print(f"Summary: {result.get('summary', 'N/A')}")
    print(f"Thread ID: {result['thread_id']}")


if __name__ == "__main__":
    asyncio.run(main())
