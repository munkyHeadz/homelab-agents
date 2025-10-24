#!/usr/bin/env python3
"""
Agent System Startup Script

This script initializes and runs the autonomous agent system.
It can run in different modes:
- interactive: Command-line interface for testing
- daemon: Background service mode
- single: Execute a single objective and exit
"""

import asyncio
import argparse
import sys
from typing import Optional
from datetime import datetime

from agents.orchestrator_agent import OrchestratorAgent
from agents.infrastructure_agent import InfrastructureAgent
from agents.monitoring_agent import MonitoringAgent
from agents.learning_agent import LearningAgent

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class AgentSystem:
    """Main agent system controller"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.orchestrator = OrchestratorAgent()
        self.infrastructure = InfrastructureAgent()
        self.monitoring = MonitoringAgent()
        self.learning = LearningAgent()

        self.logger.info(
            "Agent system initialized",
            mode="autonomous" if config.agent.autonomous_mode else "supervised"
        )

    async def run_interactive(self):
        """
        Run in interactive mode (CLI)

        Allows user to input objectives and see results in real-time.
        """
        print("=" * 80)
        print("🤖 HOMELAB AUTONOMOUS AGENT SYSTEM")
        print("=" * 80)
        print(f"Mode: {'Autonomous' if config.agent.autonomous_mode else 'Supervised'}")
        print(f"Model: {config.anthropic.flagship_model}")
        print(f"Human Approval: {'Required' if config.agent.require_human_approval else 'Optional'}")
        print("=" * 80)
        print("\nCommands:")
        print("  /help          - Show available commands")
        print("  /status        - Show system status")
        print("  /agents        - List all agents")
        print("  /memories      - Show recent memories")
        print("  /learn         - Run learning cycle")
        print("  /quit or /exit - Exit the system")
        print("\nOr enter an objective to execute (e.g., 'Check VM status')")
        print("=" * 80)

        while True:
            try:
                user_input = input("\n🎯 Objective> ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Execute objective via orchestrator
                print(f"\n⏳ Executing: {user_input}")
                result = await self.orchestrator.execute(user_input)

                if result["success"]:
                    print(f"\n✅ Success!")
                    print(f"\n{result.get('summary', 'Task completed')}")
                    print(f"\nThread ID: {result['thread_id']}")
                else:
                    print(f"\n❌ Error: {result.get('error', 'Unknown error')}")

            except KeyboardInterrupt:
                print("\n\n👋 Shutting down...")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                self.logger.error("Error in interactive mode", error=str(e))

    async def _handle_command(self, command: str):
        """Handle special commands"""

        if command in ["/quit", "/exit"]:
            print("\n👋 Goodbye!")
            sys.exit(0)

        elif command == "/help":
            print("\n📚 Available Commands:")
            print("  /status  - System status")
            print("  /agents  - List agents")
            print("  /memories - Recent memories")
            print("  /learn   - Trigger learning cycle")
            print("  /quit    - Exit")

        elif command == "/status":
            print("\n📊 System Status:")
            print(f"  ✅ Orchestrator Agent - Online")
            print(f"  ✅ Infrastructure Agent - Online")
            print(f"  ✅ Monitoring Agent - Online")
            print(f"  ✅ Learning Agent - Online")
            print(f"\n  Database: {config.postgres.host}:{config.postgres.port}")
            print(f"  Model: {config.anthropic.flagship_model}")

        elif command == "/agents":
            print("\n🤖 Available Agents:")
            print("  1. Orchestrator - Coordinates all agents")
            print("  2. Infrastructure - Manages VMs, containers, resources")
            print("  3. Monitoring - Network health, alerts, incidents")
            print("  4. Learning - Self-improvement and optimization")

        elif command == "/memories":
            print("\n🧠 Fetching recent memories...")
            # Would query Mem0 MCP here
            print("  (Implementation pending - requires Mem0 MCP)")

        elif command == "/learn":
            print("\n📖 Running learning cycle...")
            result = await self.learning.execute("Analyze past performance and generate improvements")
            if result["success"]:
                print(f"\n✅ Learning cycle complete!")
                print(f"\nAnalysis:\n{result.get('analysis', 'N/A')[:500]}")
            else:
                print(f"\n❌ Learning cycle failed: {result.get('error')}")

        else:
            print(f"\n❌ Unknown command: {command}")
            print("  Type /help for available commands")

    async def run_daemon(self):
        """
        Run in daemon mode (background service)

        Continuously monitors for tasks from:
        - n8n workflows
        - Prometheus alerts
        - Scheduled tasks
        - Telegram bot commands
        """
        self.logger.info("Starting agent system in daemon mode")

        print("🤖 Agent system running in daemon mode...")
        print("Press Ctrl+C to stop")

        try:
            while True:
                # Check for tasks from various sources
                # TODO: Implement task queue polling

                # Weekly learning cycle (runs on Sundays)
                if datetime.now().weekday() == 6 and datetime.now().hour == 2:
                    self.logger.info("Running weekly learning cycle")
                    await self.learning.weekly_reflection()

                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            self.logger.info("Daemon mode interrupted by user")
            print("\n👋 Shutting down daemon...")

    async def execute_single(self, objective: str):
        """
        Execute a single objective and exit

        Args:
            objective: Task to execute
        """
        self.logger.info("Executing single objective", objective=objective)

        print(f"🎯 Executing: {objective}\n")

        result = await self.orchestrator.execute(objective)

        if result["success"]:
            print(f"✅ Success!\n")
            print(result.get("summary", "Task completed"))
            sys.exit(0)
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Homelab Autonomous Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python run_agents.py --mode interactive

  # Daemon mode
  python run_agents.py --mode daemon

  # Single objective
  python run_agents.py --mode single --objective "Check VM status"

  # Direct agent access
  python run_agents.py --agent infrastructure --objective "List all VMs"
        """
    )

    parser.add_argument(
        "--mode",
        choices=["interactive", "daemon", "single"],
        default="interactive",
        help="Execution mode"
    )

    parser.add_argument(
        "--objective",
        type=str,
        help="Objective to execute (required for 'single' mode)"
    )

    parser.add_argument(
        "--agent",
        choices=["orchestrator", "infrastructure", "monitoring", "learning"],
        help="Specific agent to use (bypasses orchestrator)"
    )

    parser.add_argument(
        "--thread-id",
        type=str,
        help="Resume a specific thread (for human approval workflows)"
    )

    parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve a pending task (used with --thread-id)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.mode == "single" and not args.objective:
        parser.error("--objective is required when using --mode single")

    if args.approve and not args.thread_id:
        parser.error("--thread-id is required when using --approve")

    # Initialize system
    system = AgentSystem()

    # Handle resume workflow
    if args.thread_id and args.approve:
        async def resume():
            result = await system.orchestrator.resume(args.thread_id, True)
            print(f"✅ Task resumed: {result.get('summary', 'N/A')}")

        asyncio.run(resume())
        return

    # Execute based on mode
    if args.mode == "interactive":
        asyncio.run(system.run_interactive())

    elif args.mode == "daemon":
        asyncio.run(system.run_daemon())

    elif args.mode == "single":
        if args.agent:
            # Execute with specific agent
            async def run_specific():
                agent_map = {
                    "infrastructure": system.infrastructure,
                    "monitoring": system.monitoring,
                    "learning": system.learning
                }
                agent = agent_map[args.agent]
                result = await agent.execute(args.objective)
                print(f"✅ Result: {result}")

            asyncio.run(run_specific())
        else:
            # Execute via orchestrator
            asyncio.run(system.execute_single(args.objective))


if __name__ == "__main__":
    main()
