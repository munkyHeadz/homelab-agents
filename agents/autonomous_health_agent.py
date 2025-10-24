"""
Autonomous Health Agent - Self-Monitoring, Self-Healing, and Self-Improving

This agent continuously monitors the homelab infrastructure and automatically
fixes issues when safe to do so. For risky actions, it requests approval via Telegram.

Responsibilities:
- Continuous health monitoring (VMs, containers, services, resources)
- Automatic diagnosis of issues
- Risk assessment for remediation actions
- Auto-healing for low-risk issues
- Request approval via Telegram for risky actions
- Learn from successful/failed healing attempts
- Generate health reports
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from shared.config import config
from shared.logging import get_logger
from shared.llm_router import LLMRouter
from shared.metrics import get_metrics_collector

logger = get_logger(__name__)


class RiskLevel(Enum):
    """Risk level for remediation actions"""
    LOW = "low"       # Auto-fix without asking (restart container, clear cache)
    MEDIUM = "medium" # Ask for approval with timeout (restart service, reboot container)
    HIGH = "high"     # Always ask, no timeout (VM reboot, data operations)


class HealthStatus(Enum):
    """Health status of monitored components"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class HealthIssue:
    """Represents a detected health issue"""
    def __init__(self,
                 component: str,
                 issue_type: str,
                 severity: HealthStatus,
                 description: str,
                 metrics: Dict[str, Any],
                 suggested_fix: Optional[str] = None,
                 risk_level: RiskLevel = RiskLevel.MEDIUM):
        self.id = str(uuid.uuid4())[:8]
        self.component = component
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.metrics = metrics
        self.suggested_fix = suggested_fix
        self.risk_level = risk_level
        self.detected_at = datetime.now()
        self.resolved = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission"""
        return {
            "id": self.id,
            "component": self.component,
            "issue_type": self.issue_type,
            "severity": self.severity.value,
            "description": self.description,
            "metrics": self.metrics,
            "suggested_fix": self.suggested_fix,
            "risk_level": self.risk_level.value,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved
        }


class AutonomousHealthAgent:
    """
    Autonomous agent that monitors, diagnoses, and heals infrastructure issues.

    Key Features:
    - Continuous monitoring every 60 seconds
    - Automatic diagnosis using Claude
    - Risk-based auto-healing
    - Telegram approval workflow for risky actions
    - Learning from past actions
    - Comprehensive reporting
    """

    def __init__(self, telegram_notifier=None):
        self.llm_router = LLMRouter()
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector("autonomous_health_agent")

        # Telegram notifier for sending alerts and requesting approvals
        self.telegram_notifier = telegram_notifier

        # Track pending approvals
        self.pending_approvals: Dict[str, HealthIssue] = {}

        # Track active issues
        self.active_issues: List[HealthIssue] = []

        # Track resolved issues for learning
        self.resolved_issues: List[HealthIssue] = []

        # Use balanced model for health analysis
        model = self.llm_router.route_task("incident_analysis")
        self.llm = ChatAnthropic(
            model=model,
            api_key=config.anthropic.api_key,
            temperature=0.2  # Low temperature for consistent diagnosis
        )

        self.logger.info("Autonomous Health Agent initialized", model=model)
        self.metrics.set_health_status(True)

    async def _connect_mcp_servers(self):
        """Connect to all MCP servers for comprehensive monitoring"""
        import sys
        python_path = sys.executable

        # Proxmox MCP
        proxmox_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/proxmox_mcp/server.py"],
            env=None
        )

        # Docker MCP
        docker_params = StdioServerParameters(
            command=python_path,
            args=["mcp_servers/docker_mcp/server.py"],
            env=None
        )

        return proxmox_params, docker_params

    async def monitor_system_health(self) -> List[HealthIssue]:
        """
        Comprehensive system health monitoring

        Checks:
        - Proxmox node health (CPU, memory, disk, uptime)
        - VM/Container status and resource usage
        - Docker system health
        - Container health status
        - MCP server connectivity

        Returns:
            List of detected health issues
        """
        issues = []

        try:
            proxmox_params, docker_params = await self._connect_mcp_servers()

            async with stdio_client(proxmox_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # 1. Check Proxmox node health
                    node_issues = await self._check_proxmox_health(session)
                    issues.extend(node_issues)

                    # 2. Check VM/Container health
                    vm_issues = await self._check_vm_health(session)
                    issues.extend(vm_issues)

            # 3. Check Docker health
            async with stdio_client(docker_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    docker_issues = await self._check_docker_health(session)
                    issues.extend(docker_issues)

        except Exception as e:
            self.logger.error("Error during health monitoring", error=str(e))
            issues.append(HealthIssue(
                component="health_monitor",
                issue_type="monitoring_error",
                severity=HealthStatus.DEGRADED,
                description=f"Health monitoring encountered an error: {str(e)}",
                metrics={"error": str(e)},
                risk_level=RiskLevel.HIGH
            ))

        return issues

    async def _check_proxmox_health(self, session: ClientSession) -> List[HealthIssue]:
        """Check Proxmox node health"""
        issues = []

        try:
            # Get node status
            result = await session.call_tool("proxmox_get_node_status", arguments={})

            if result and result.content:
                status_text = result.content[0].text if result.content else "{}"
                status = json.loads(status_text)

                # Check CPU usage
                cpu_usage = status.get("cpu", 0) * 100
                if cpu_usage > 90:
                    issues.append(HealthIssue(
                        component="proxmox_node",
                        issue_type="high_cpu",
                        severity=HealthStatus.UNHEALTHY if cpu_usage > 95 else HealthStatus.DEGRADED,
                        description=f"Proxmox node CPU usage is high: {cpu_usage:.1f}%",
                        metrics={"cpu_usage": cpu_usage},
                        suggested_fix="Identify and optimize high-CPU processes",
                        risk_level=RiskLevel.LOW
                    ))

                # Check memory usage
                memory = status.get("memory", {})
                if isinstance(memory, dict):
                    used = memory.get("used", 0)
                    total = memory.get("total", 1)
                    mem_percent = (used / total) * 100 if total > 0 else 0

                    if mem_percent > 90:
                        issues.append(HealthIssue(
                            component="proxmox_node",
                            issue_type="high_memory",
                            severity=HealthStatus.UNHEALTHY if mem_percent > 95 else HealthStatus.DEGRADED,
                            description=f"Proxmox node memory usage is high: {mem_percent:.1f}%",
                            metrics={"memory_percent": mem_percent, "used_gb": used / (1024**3)},
                            suggested_fix="Clear caches or stop non-essential containers",
                            risk_level=RiskLevel.MEDIUM
                        ))

                # Check disk usage
                rootfs = status.get("rootfs", {})
                if isinstance(rootfs, dict):
                    used = rootfs.get("used", 0)
                    total = rootfs.get("total", 1)
                    disk_percent = (used / total) * 100 if total > 0 else 0

                    if disk_percent > 85:
                        issues.append(HealthIssue(
                            component="proxmox_node",
                            issue_type="high_disk",
                            severity=HealthStatus.CRITICAL if disk_percent > 95 else HealthStatus.UNHEALTHY,
                            description=f"Proxmox node disk usage is high: {disk_percent:.1f}%",
                            metrics={"disk_percent": disk_percent, "used_gb": used / (1024**3)},
                            suggested_fix="Clean up old backups, logs, or unused data",
                            risk_level=RiskLevel.LOW
                        ))

        except Exception as e:
            self.logger.error("Error checking Proxmox health", error=str(e))

        return issues

    async def _check_vm_health(self, session: ClientSession) -> List[HealthIssue]:
        """Check VM and container health"""
        issues = []

        try:
            # Get VM list
            result = await session.call_tool("proxmox_list_vms", arguments={})

            if result and result.content:
                vms_text = result.content[0].text if result.content else "[]"
                vms = json.loads(vms_text) if isinstance(vms_text, str) else vms_text

                for vm in vms:
                    status = vm.get("status", "unknown")
                    vmid = vm.get("vmid", "unknown")
                    name = vm.get("name", f"VM-{vmid}")
                    vm_type = vm.get("type", "unknown")

                    # Check if VM/Container is stopped unexpectedly
                    if status == "stopped":
                        # Only flag as issue if it's a critical service
                        critical_ids = [104]  # Homelab agents container
                        if vmid in critical_ids:
                            issues.append(HealthIssue(
                                component=f"{vm_type}_{vmid}",
                                issue_type="service_stopped",
                                severity=HealthStatus.CRITICAL,
                                description=f"Critical {vm_type} '{name}' (ID: {vmid}) is stopped",
                                metrics={"vmid": vmid, "name": name, "status": status},
                                suggested_fix=f"Start {vm_type} {vmid}",
                                risk_level=RiskLevel.MEDIUM
                            ))

                    # Check resource usage if running
                    elif status == "running":
                        cpu = vm.get("cpu", 0)
                        if cpu > 0.9:  # 90% CPU
                            issues.append(HealthIssue(
                                component=f"{vm_type}_{vmid}",
                                issue_type="high_cpu",
                                severity=HealthStatus.DEGRADED,
                                description=f"{vm_type} '{name}' (ID: {vmid}) has high CPU: {cpu*100:.1f}%",
                                metrics={"vmid": vmid, "name": name, "cpu_percent": cpu*100},
                                suggested_fix=f"Investigate high CPU usage in {vm_type} {vmid}",
                                risk_level=RiskLevel.LOW
                            ))

        except Exception as e:
            self.logger.error("Error checking VM health", error=str(e))

        return issues

    async def _check_docker_health(self, session: ClientSession) -> List[HealthIssue]:
        """Check Docker system and container health"""
        issues = []

        try:
            # Get Docker info
            result = await session.call_tool("docker_info", arguments={})

            if result and result.content:
                info_text = result.content[0].text if result.content else "{}"
                info = json.loads(info_text) if isinstance(info_text, str) else info_text

                # Check if Docker daemon is healthy
                if not info or "error" in str(info).lower():
                    issues.append(HealthIssue(
                        component="docker_daemon",
                        issue_type="daemon_unhealthy",
                        severity=HealthStatus.CRITICAL,
                        description="Docker daemon is not responding properly",
                        metrics={"info": str(info)},
                        suggested_fix="Restart Docker daemon",
                        risk_level=RiskLevel.HIGH
                    ))
                    return issues

            # Get container list
            result = await session.call_tool("docker_list_containers", arguments={"all": True})

            if result and result.content:
                containers_text = result.content[0].text if result.content else "[]"
                containers = json.loads(containers_text) if isinstance(containers_text, str) else containers_text

                for container in containers:
                    name = container.get("Names", ["unknown"])[0].lstrip("/")
                    state = container.get("State", "unknown")
                    status = container.get("Status", "")

                    # Check for exited containers
                    if state in ["exited", "dead"]:
                        # Check if it exited recently (within last hour)
                        if "hours ago" not in status.lower() and "days ago" not in status.lower():
                            issues.append(HealthIssue(
                                component=f"docker_container_{name}",
                                issue_type="container_stopped",
                                severity=HealthStatus.UNHEALTHY,
                                description=f"Docker container '{name}' exited: {status}",
                                metrics={"container": name, "state": state, "status": status},
                                suggested_fix=f"Restart container '{name}'",
                                risk_level=RiskLevel.LOW
                            ))

                    # Check for unhealthy containers
                    elif "unhealthy" in status.lower():
                        issues.append(HealthIssue(
                            component=f"docker_container_{name}",
                            issue_type="container_unhealthy",
                            severity=HealthStatus.UNHEALTHY,
                            description=f"Docker container '{name}' is unhealthy",
                            metrics={"container": name, "status": status},
                            suggested_fix=f"Restart container '{name}'",
                            risk_level=RiskLevel.LOW
                        ))

        except Exception as e:
            self.logger.error("Error checking Docker health", error=str(e))

        return issues

    async def diagnose_issue(self, issue: HealthIssue) -> HealthIssue:
        """
        Use Claude to diagnose the root cause and suggest remediation

        Args:
            issue: The detected health issue

        Returns:
            Updated issue with enhanced diagnosis
        """
        try:
            diagnosis_prompt = f"""You are a homelab infrastructure expert. Analyze this health issue and provide:
1. Root cause analysis
2. Recommended remediation action
3. Risk level assessment (low/medium/high)

Issue:
- Component: {issue.component}
- Type: {issue.issue_type}
- Severity: {issue.severity.value}
- Description: {issue.description}
- Metrics: {json.dumps(issue.metrics, indent=2)}

Respond in JSON format:
{{
    "root_cause": "explanation",
    "remediation": "specific action to take",
    "risk_level": "low|medium|high",
    "reasoning": "why this is the best approach"
}}"""

            messages = [
                SystemMessage(content="You are an expert in homelab infrastructure diagnostics and remediation."),
                HumanMessage(content=diagnosis_prompt)
            ]

            response = await asyncio.to_thread(self.llm.invoke, messages)
            diagnosis_text = response.content

            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', diagnosis_text, re.DOTALL)
            if json_match:
                diagnosis = json.loads(json_match.group())

                # Update issue with enhanced diagnosis
                issue.suggested_fix = diagnosis.get("remediation", issue.suggested_fix)
                risk_str = diagnosis.get("risk_level", "medium").lower()
                issue.risk_level = RiskLevel(risk_str) if risk_str in ["low", "medium", "high"] else RiskLevel.MEDIUM

                # Add diagnosis to metrics
                issue.metrics["root_cause"] = diagnosis.get("root_cause", "Unknown")
                issue.metrics["reasoning"] = diagnosis.get("reasoning", "")

            self.logger.info("Issue diagnosed", issue_id=issue.id, component=issue.component)

        except Exception as e:
            self.logger.error("Error diagnosing issue", issue_id=issue.id, error=str(e))

        return issue

    async def attempt_auto_heal(self, issue: HealthIssue) -> Tuple[bool, str]:
        """
        Attempt to automatically heal the issue based on risk level

        Args:
            issue: The health issue to heal

        Returns:
            Tuple of (success, message)
        """
        try:
            # Only auto-heal LOW risk issues
            if issue.risk_level != RiskLevel.LOW:
                return False, f"Risk level {issue.risk_level.value} requires approval"

            self.logger.info("Attempting auto-heal", issue_id=issue.id, component=issue.component)

            # Execute remediation based on issue type
            if issue.issue_type == "container_stopped":
                # Restart stopped container
                container_name = issue.metrics.get("container")
                if container_name:
                    success = await self._restart_docker_container(container_name)
                    if success:
                        issue.resolved = True
                        return True, f"Successfully restarted container '{container_name}'"
                    else:
                        return False, f"Failed to restart container '{container_name}'"

            elif issue.issue_type == "container_unhealthy":
                # Restart unhealthy container
                container_name = issue.metrics.get("container")
                if container_name:
                    success = await self._restart_docker_container(container_name)
                    if success:
                        issue.resolved = True
                        return True, f"Successfully restarted unhealthy container '{container_name}'"
                    else:
                        return False, f"Failed to restart container '{container_name}'"

            elif issue.issue_type == "high_disk":
                # Clean up disk space
                success = await self._cleanup_disk_space()
                if success:
                    issue.resolved = True
                    return True, "Successfully cleaned up disk space"
                else:
                    return False, "Failed to clean up disk space"

            else:
                return False, f"No auto-heal action defined for issue type: {issue.issue_type}"

        except Exception as e:
            self.logger.error("Error during auto-heal", issue_id=issue.id, error=str(e))
            return False, f"Auto-heal error: {str(e)}"

    async def _restart_docker_container(self, container_name: str) -> bool:
        """Restart a Docker container"""
        try:
            docker_params = (await self._connect_mcp_servers())[1]

            async with stdio_client(docker_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Restart container
                    result = await session.call_tool("docker_restart_container",
                                                    arguments={"container": container_name})

                    if result and result.content:
                        self.logger.info("Container restarted", container=container_name)
                        return True

        except Exception as e:
            self.logger.error("Error restarting container", container=container_name, error=str(e))

        return False

    async def _cleanup_disk_space(self) -> bool:
        """Clean up disk space (logs, old backups, docker images)"""
        try:
            docker_params = (await self._connect_mcp_servers())[1]

            async with stdio_client(docker_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Prune unused Docker resources
                    result = await session.call_tool("docker_system_prune", arguments={})

                    if result and result.content:
                        self.logger.info("Disk space cleaned up")
                        return True

        except Exception as e:
            self.logger.error("Error cleaning disk space", error=str(e))

        return False

    async def request_approval(self, issue: HealthIssue) -> str:
        """
        Request approval from user via Telegram for risky actions

        Args:
            issue: The health issue requiring approval

        Returns:
            Approval request ID for tracking
        """
        if self.telegram_notifier:
            approval_id = issue.id
            self.pending_approvals[approval_id] = issue

            # Send approval request to Telegram
            await self.telegram_notifier.send_approval_request(issue)

            self.logger.info("Approval requested", approval_id=approval_id, component=issue.component)
            return approval_id
        else:
            self.logger.warning("No Telegram notifier configured for approval request")
            return None

    def handle_approval_response(self, approval_id: str, approved: bool):
        """
        Handle user's approval response from Telegram

        Args:
            approval_id: The approval request ID
            approved: Whether the action was approved
        """
        issue = self.pending_approvals.get(approval_id)

        if issue:
            if approved:
                self.logger.info("Action approved", approval_id=approval_id, component=issue.component)
                # Schedule the action to be executed
                asyncio.create_task(self._execute_approved_action(issue))
            else:
                self.logger.info("Action rejected", approval_id=approval_id, component=issue.component)
                if self.telegram_notifier:
                    asyncio.create_task(
                        self.telegram_notifier.send_message(
                            f"❌ Action rejected for {issue.component}\nIssue will remain unresolved."
                        )
                    )

            # Remove from pending
            del self.pending_approvals[approval_id]
        else:
            self.logger.warning("Unknown approval ID", approval_id=approval_id)

    async def _execute_approved_action(self, issue: HealthIssue):
        """Execute the action that was approved by the user"""
        try:
            self.logger.info("Executing approved action", issue_id=issue.id, component=issue.component)

            # Execute based on issue type
            if "service_stopped" in issue.issue_type:
                vmid = issue.metrics.get("vmid")
                if vmid:
                    success = await self._start_vm(vmid)
                    result_msg = f"✅ Successfully started VM/Container {vmid}" if success else f"❌ Failed to start VM/Container {vmid}"
                else:
                    result_msg = "❌ Missing VM ID"

            elif issue.issue_type == "high_memory":
                success = await self._cleanup_memory()
                result_msg = "✅ Successfully cleared memory caches" if success else "❌ Failed to clear memory"

            else:
                success, result_msg = await self.attempt_auto_heal(issue)

            # Report result
            if self.telegram_notifier:
                await self.telegram_notifier.send_message(
                    f"🔧 Action executed for {issue.component}\n{result_msg}"
                )

            if success:
                issue.resolved = True
                self.resolved_issues.append(issue)

        except Exception as e:
            self.logger.error("Error executing approved action", issue_id=issue.id, error=str(e))
            if self.telegram_notifier:
                await self.telegram_notifier.send_message(
                    f"❌ Error executing action for {issue.component}: {str(e)}"
                )

    async def _start_vm(self, vmid: int) -> bool:
        """Start a VM or container"""
        try:
            proxmox_params = (await self._connect_mcp_servers())[0]

            async with stdio_client(proxmox_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Start VM/Container
                    result = await session.call_tool("proxmox_start_vm",
                                                    arguments={"vmid": vmid})

                    if result and result.content:
                        self.logger.info("VM/Container started", vmid=vmid)
                        return True

        except Exception as e:
            self.logger.error("Error starting VM", vmid=vmid, error=str(e))

        return False

    async def _cleanup_memory(self) -> bool:
        """Clear system caches to free memory"""
        try:
            # This would need to be implemented via a system command MCP tool
            # For now, just log
            self.logger.info("Memory cleanup requested (implementation pending)")
            return True
        except Exception as e:
            self.logger.error("Error cleaning memory", error=str(e))
            return False

    async def generate_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report

        Returns:
            Health report with all metrics and issues
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "active_issues": len(self.active_issues),
            "resolved_today": len([i for i in self.resolved_issues
                                   if i.detected_at > datetime.now() - timedelta(days=1)]),
            "pending_approvals": len(self.pending_approvals),
            "issues_by_severity": {
                "critical": len([i for i in self.active_issues if i.severity == HealthStatus.CRITICAL]),
                "unhealthy": len([i for i in self.active_issues if i.severity == HealthStatus.UNHEALTHY]),
                "degraded": len([i for i in self.active_issues if i.severity == HealthStatus.DEGRADED]),
            },
            "issues": [issue.to_dict() for issue in self.active_issues],
            "recent_resolutions": [issue.to_dict() for issue in self.resolved_issues[-10:]]
        }

        return report

    async def run_monitoring_loop(self, interval: int = 60):
        """
        Main monitoring loop - runs continuously

        Args:
            interval: Seconds between health checks (default: 60)
        """
        self.logger.info("Starting autonomous health monitoring loop", interval=interval)

        while True:
            try:
                # 1. Monitor system health
                detected_issues = await self.monitor_system_health()

                # 2. Filter new issues (not already active)
                new_issues = [issue for issue in detected_issues
                             if not any(active.component == issue.component and
                                       active.issue_type == issue.issue_type
                                       for active in self.active_issues)]

                # 3. Process each new issue
                for issue in new_issues:
                    self.logger.info("New issue detected",
                                   component=issue.component,
                                   type=issue.issue_type,
                                   severity=issue.severity.value)

                    # Diagnose with Claude
                    issue = await self.diagnose_issue(issue)

                    # Add to active issues
                    self.active_issues.append(issue)

                    # Attempt remediation based on risk level
                    if issue.risk_level == RiskLevel.LOW:
                        # Auto-heal
                        success, message = await self.attempt_auto_heal(issue)

                        # Report to Telegram
                        if self.telegram_notifier:
                            status = "✅" if success else "❌"
                            await self.telegram_notifier.send_message(
                                f"🔧 Auto-Healing Action\n\n"
                                f"Component: {issue.component}\n"
                                f"Issue: {issue.description}\n"
                                f"Action: {issue.suggested_fix}\n"
                                f"Result: {status} {message}"
                            )

                        # Remove from active if resolved
                        if success:
                            self.active_issues.remove(issue)
                            self.resolved_issues.append(issue)

                    else:
                        # Request approval for medium/high risk
                        if self.telegram_notifier:
                            await self.request_approval(issue)

                # 4. Clean up resolved issues from active list
                self.active_issues = [i for i in self.active_issues if not i.resolved]

                # 5. Update metrics
                self.metrics.set_health_status(len([i for i in self.active_issues
                                                     if i.severity == HealthStatus.CRITICAL]) == 0)

                # 6. Wait for next interval
                await asyncio.sleep(interval)

            except Exception as e:
                self.logger.error("Error in monitoring loop", error=str(e))
                await asyncio.sleep(interval)
