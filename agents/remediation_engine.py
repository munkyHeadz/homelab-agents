"""
Automated Remediation Engine

Provides self-healing and automated remediation capabilities:
- Auto-restart failed services
- Automatic cleanup (logs, disk space)
- Container health monitoring and recovery
- Resource scaling and optimization
- Smart alert suppression during remediation
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum

from shared.logging import get_logger
from shared.config import config
from shared.metrics import get_metrics_collector

logger = get_logger(__name__)


class RemediationStatus(str, Enum):
    """Status of remediation action"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RemediationType(str, Enum):
    """Types of remediation actions"""
    SERVICE_RESTART = "service_restart"
    CONTAINER_RESTART = "container_restart"
    DISK_CLEANUP = "disk_cleanup"
    LOG_ROTATION = "log_rotation"
    RESOURCE_SCALE = "resource_scale"
    CUSTOM = "custom"


class RemediationAction:
    """Represents a remediation action"""

    def __init__(
        self,
        action_id: str,
        action_type: RemediationType,
        description: str,
        target: str,
        severity: str = "medium",
        auto_approve: bool = False,
        cooldown_minutes: int = 15
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.description = description
        self.target = target
        self.severity = severity
        self.auto_approve = auto_approve
        self.cooldown_minutes = cooldown_minutes
        self.status = RemediationStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.executed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "description": self.description,
            "target": self.target,
            "severity": self.severity,
            "auto_approve": self.auto_approve,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "result": self.result,
            "error": self.error
        }


class RemediationEngine:
    """Engine for executing automated remediation actions"""

    def __init__(self, infrastructure_agent=None):
        self.infrastructure_agent = infrastructure_agent
        self.metrics = get_metrics_collector("remediation_engine")
        self.logger = logger

        # Track recent actions to enforce cooldown
        self.action_history: List[RemediationAction] = []
        self.max_history = 100

        # Callbacks for notifications
        self.notification_callbacks: List[Callable] = []

        # Safety limits
        self.max_actions_per_hour = 10
        self.require_approval = not config.features.auto_remediation

        self.logger.info("Remediation engine initialized", auto_remediation=config.features.auto_remediation)

    def register_notification_callback(self, callback: Callable):
        """Register callback for remediation notifications"""
        self.notification_callbacks.append(callback)

    async def _notify(self, action: RemediationAction, message: str):
        """Send notification about remediation action"""
        for callback in self.notification_callbacks:
            try:
                await callback(action, message)
            except Exception as e:
                self.logger.error(f"Error in notification callback: {e}")

    def _check_cooldown(self, target: str, action_type: RemediationType, cooldown_minutes: int) -> bool:
        """Check if action is in cooldown period"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)

        for action in self.action_history:
            if (action.target == target and
                action.action_type == action_type and
                action.executed_at and
                action.executed_at > cutoff):
                return False

        return True

    def _check_rate_limit(self) -> bool:
        """Check if we've exceeded rate limit"""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_actions = [
            a for a in self.action_history
            if a.executed_at and a.executed_at > one_hour_ago
        ]
        return len(recent_actions) < self.max_actions_per_hour

    async def restart_service(self, vmid: str, service_name: str, auto_approve: bool = False) -> RemediationAction:
        """
        Restart a failed service in a VM/container

        Args:
            vmid: VM/container ID
            service_name: Name of the service to restart
            auto_approve: Skip approval if true

        Returns:
            RemediationAction with result
        """
        action = RemediationAction(
            action_id=f"restart_{service_name}_{vmid}_{int(datetime.now().timestamp())}",
            action_type=RemediationType.SERVICE_RESTART,
            description=f"Restart {service_name} in {vmid}",
            target=f"{vmid}:{service_name}",
            severity="medium",
            auto_approve=auto_approve,
            cooldown_minutes=15
        )

        try:
            # Check cooldown
            if not self._check_cooldown(action.target, action.action_type, action.cooldown_minutes):
                action.status = RemediationStatus.SKIPPED
                action.error = "Action in cooldown period"
                self.logger.warning(f"Skipped {action.description}: cooldown active")
                return action

            # Check rate limit
            if not self._check_rate_limit():
                action.status = RemediationStatus.SKIPPED
                action.error = "Rate limit exceeded"
                self.logger.warning(f"Skipped {action.description}: rate limit")
                return action

            # Check approval requirement
            if self.require_approval and not auto_approve:
                action.status = RemediationStatus.PENDING
                await self._notify(action, f"⚠️ Remediation requires approval: {action.description}")
                self.logger.info(f"Remediation pending approval: {action.description}")
                return action

            # Execute remediation
            action.status = RemediationStatus.IN_PROGRESS
            action.executed_at = datetime.now(timezone.utc)

            await self._notify(action, f"🔧 Starting remediation: {action.description}")

            if self.infrastructure_agent:
                result = await self.infrastructure_agent.execute(
                    f"Restart service {service_name} in VM/container {vmid}"
                )

                if result.get("success"):
                    action.status = RemediationStatus.SUCCESS
                    action.result = result
                    await self._notify(action, f"✅ Remediation successful: {action.description}")
                    self.logger.info(f"Remediation successful: {action.description}")
                else:
                    action.status = RemediationStatus.FAILED
                    action.error = result.get("error", "Unknown error")
                    await self._notify(action, f"❌ Remediation failed: {action.description}")
                    self.logger.error(f"Remediation failed: {action.description}")
            else:
                action.status = RemediationStatus.FAILED
                action.error = "Infrastructure agent not available"

            # Record in history
            self.action_history.append(action)
            if len(self.action_history) > self.max_history:
                self.action_history.pop(0)

            # Record metrics
            self.metrics.record_agent_execution(
                agent_name="remediation_engine",
                task_type=action.action_type.value,
                success=(action.status == RemediationStatus.SUCCESS),
                duration=0
            )

            return action

        except Exception as e:
            action.status = RemediationStatus.FAILED
            action.error = str(e)
            self.logger.error(f"Error in restart_service: {e}")
            return action

    async def cleanup_disk(self, vmid: str, path: str = "/var/log", auto_approve: bool = False) -> RemediationAction:
        """
        Clean up disk space by removing old logs

        Args:
            vmid: VM/container ID
            path: Path to clean
            auto_approve: Skip approval if true

        Returns:
            RemediationAction with result
        """
        action = RemediationAction(
            action_id=f"cleanup_{vmid}_{int(datetime.now().timestamp())}",
            action_type=RemediationType.DISK_CLEANUP,
            description=f"Clean up {path} in {vmid}",
            target=f"{vmid}:{path}",
            severity="low",
            auto_approve=auto_approve,
            cooldown_minutes=60
        )

        try:
            if not self._check_cooldown(action.target, action.action_type, action.cooldown_minutes):
                action.status = RemediationStatus.SKIPPED
                action.error = "Action in cooldown period"
                return action

            if self.require_approval and not auto_approve:
                action.status = RemediationStatus.PENDING
                await self._notify(action, f"⚠️ Cleanup requires approval: {action.description}")
                return action

            action.status = RemediationStatus.IN_PROGRESS
            action.executed_at = datetime.now(timezone.utc)

            await self._notify(action, f"🧹 Starting cleanup: {action.description}")

            if self.infrastructure_agent:
                result = await self.infrastructure_agent.execute(
                    f"Clean up old log files in {path} on VM/container {vmid}, keep last 7 days"
                )

                if result.get("success"):
                    action.status = RemediationStatus.SUCCESS
                    action.result = result
                    await self._notify(action, f"✅ Cleanup successful: {action.description}")
                else:
                    action.status = RemediationStatus.FAILED
                    action.error = result.get("error", "Unknown error")
                    await self._notify(action, f"❌ Cleanup failed: {action.description}")
            else:
                action.status = RemediationStatus.FAILED
                action.error = "Infrastructure agent not available"

            self.action_history.append(action)
            if len(self.action_history) > self.max_history:
                self.action_history.pop(0)

            return action

        except Exception as e:
            action.status = RemediationStatus.FAILED
            action.error = str(e)
            self.logger.error(f"Error in cleanup_disk: {e}")
            return action

    async def heal_container(self, container_id: str, auto_approve: bool = False) -> RemediationAction:
        """
        Restart an unhealthy Docker container

        Args:
            container_id: Container ID or name
            auto_approve: Skip approval if true

        Returns:
            RemediationAction with result
        """
        action = RemediationAction(
            action_id=f"heal_{container_id}_{int(datetime.now().timestamp())}",
            action_type=RemediationType.CONTAINER_RESTART,
            description=f"Restart unhealthy container {container_id}",
            target=container_id,
            severity="medium",
            auto_approve=auto_approve,
            cooldown_minutes=10
        )

        try:
            if not self._check_cooldown(action.target, action.action_type, action.cooldown_minutes):
                action.status = RemediationStatus.SKIPPED
                action.error = "Action in cooldown period"
                return action

            if self.require_approval and not auto_approve:
                action.status = RemediationStatus.PENDING
                await self._notify(action, f"⚠️ Container restart requires approval: {action.description}")
                return action

            action.status = RemediationStatus.IN_PROGRESS
            action.executed_at = datetime.now(timezone.utc)

            await self._notify(action, f"🏥 Healing container: {action.description}")

            if self.infrastructure_agent:
                result = await self.infrastructure_agent.execute(
                    f"Restart Docker container {container_id}"
                )

                if result.get("success"):
                    action.status = RemediationStatus.SUCCESS
                    action.result = result
                    await self._notify(action, f"✅ Container healed: {action.description}")
                else:
                    action.status = RemediationStatus.FAILED
                    action.error = result.get("error", "Unknown error")
                    await self._notify(action, f"❌ Container healing failed: {action.description}")
            else:
                action.status = RemediationStatus.FAILED
                action.error = "Infrastructure agent not available"

            self.action_history.append(action)
            if len(self.action_history) > self.max_history:
                self.action_history.pop(0)

            return action

        except Exception as e:
            action.status = RemediationStatus.FAILED
            action.error = str(e)
            self.logger.error(f"Error in heal_container: {e}")
            return action

    def get_recent_actions(self, limit: int = 10) -> List[RemediationAction]:
        """Get recent remediation actions"""
        return sorted(
            self.action_history,
            key=lambda x: x.created_at,
            reverse=True
        )[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get remediation statistics"""
        total = len(self.action_history)
        success = len([a for a in self.action_history if a.status == RemediationStatus.SUCCESS])
        failed = len([a for a in self.action_history if a.status == RemediationStatus.FAILED])
        pending = len([a for a in self.action_history if a.status == RemediationStatus.PENDING])

        return {
            "total_actions": total,
            "successful": success,
            "failed": failed,
            "pending": pending,
            "success_rate": round((success / total * 100) if total > 0 else 0, 2),
            "auto_remediation_enabled": config.features.auto_remediation
        }


# Global instance
_remediation_engine = None

def get_remediation_engine(infrastructure_agent=None) -> RemediationEngine:
    """Get or create the global remediation engine instance"""
    global _remediation_engine
    if _remediation_engine is None:
        _remediation_engine = RemediationEngine(infrastructure_agent)
    elif infrastructure_agent is not None:
        _remediation_engine.infrastructure_agent = infrastructure_agent
    return _remediation_engine
