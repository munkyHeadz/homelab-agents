"""
Backup Manager

Provides high-level backup management and monitoring:
- Backup status monitoring
- Missing backup detection
- Backup health reporting
- Integration with alert system
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from shared.logging import get_logger
from integrations.pbs_client import get_pbs_client

logger = get_logger(__name__)


class BackupManager:
    """Manages backup monitoring and reporting"""

    def __init__(self):
        self.logger = logger
        self.pbs_client = get_pbs_client()

        if not self.pbs_client:
            self.logger.warning("BackupManager initialized without PBS client")

    def is_available(self) -> bool:
        """Check if PBS integration is available"""
        return self.pbs_client is not None

    async def get_backup_status(self) -> Dict[str, Any]:
        """
        Get comprehensive backup status

        Returns:
            Dict with backup status information
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "PBS integration not configured",
                "available": False
            }

        try:
            # Get datastore status
            datastore_status = await self.pbs_client.get_datastore_status()

            # Get backup summary
            backup_summary = await self.pbs_client.get_backup_summary()

            # Get recent backups
            recent_backups = await self.pbs_client.get_recent_backups(limit=5)

            # Check backup health
            health = await self._check_backup_health(backup_summary)

            return {
                "success": True,
                "available": True,
                "datastore": datastore_status,
                "summary": backup_summary,
                "recent": recent_backups.get("backups", []),
                "health": health
            }

        except Exception as e:
            self.logger.error(f"Error getting backup status: {e}")
            return {
                "success": False,
                "error": str(e),
                "available": True
            }

    async def _check_backup_health(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check backup health and identify issues

        Args:
            summary: Backup summary from get_backup_summary()

        Returns:
            Dict with health status and issues
        """
        issues = []
        status = "healthy"

        if not summary.get("success"):
            return {
                "status": "error",
                "issues": ["Failed to retrieve backup summary"]
            }

        # Check if backups exist
        total_backups = summary.get("total_backups", 0)
        if total_backups == 0:
            issues.append("No backups found")
            status = "critical"

        # Check latest backup age
        latest_backup = summary.get("latest_backup_time")
        if latest_backup:
            latest_time = datetime.fromisoformat(latest_backup)
            age = datetime.now(timezone.utc) - latest_time

            if age > timedelta(days=2):
                issues.append(f"Latest backup is {age.days} days old")
                status = "warning" if status != "critical" else "critical"
            elif age > timedelta(days=1):
                issues.append(f"Latest backup is over 1 day old")
                if status == "healthy":
                    status = "warning"
        else:
            issues.append("No recent backups")
            status = "critical"

        # Check protected backups
        protected_count = summary.get("protected_count", 0)
        if protected_count == 0 and total_backups > 0:
            issues.append("No backups are protected")
            if status == "healthy":
                status = "info"

        return {
            "status": status,
            "issues": issues if issues else None
        }

    async def get_backup_report(self) -> str:
        """
        Generate formatted backup report for Telegram

        Returns:
            Markdown-formatted backup report
        """
        if not self.is_available():
            return "📦 **Backup Status**: ⚠️ PBS not configured"

        try:
            status = await self.get_backup_status()

            if not status.get("success"):
                return f"📦 **Backup Status**: ❌ Error\n\n_{status.get('error', 'Unknown error')}_"

            report = "📦 **Backup Status**\n\n"

            # Datastore info
            datastore = status.get("datastore", {})
            if datastore.get("success"):
                usage = datastore.get("usage_percent", 0)
                used_gb = round(datastore.get("used", 0) / (1024**3), 2)
                total_gb = round(datastore.get("total", 0) / (1024**3), 2)

                emoji = "🟢" if usage < 80 else "🟡" if usage < 90 else "🔴"
                report += f"**Datastore:** {datastore.get('datastore', 'Unknown')}\n"
                report += f"{emoji} Storage: {used_gb} GB / {total_gb} GB ({usage}%)\n\n"

            # Backup summary
            summary = status.get("summary", {})
            if summary.get("success"):
                total = summary.get("total_backups", 0)
                size_gb = summary.get("total_size_gb", 0)
                protected = summary.get("protected_count", 0)
                latest = summary.get("latest_backup_time")

                report += f"**Backups:** {total} snapshots ({size_gb} GB)\n"
                report += f"**Protected:** {protected} backups\n"

                if latest:
                    latest_time = datetime.fromisoformat(latest)
                    age = datetime.now(timezone.utc) - latest_time
                    hours_ago = age.total_seconds() / 3600

                    if hours_ago < 24:
                        time_str = f"{int(hours_ago)}h ago"
                    else:
                        time_str = f"{age.days}d ago"

                    report += f"**Latest:** {time_str}\n\n"

                # Backup types
                by_type = summary.get("by_type", {})
                if by_type:
                    report += "**By Type:**\n"
                    for backup_type, type_info in by_type.items():
                        count = type_info.get("count", 0)
                        unique = type_info.get("unique_ids", 0)
                        report += f"  • {backup_type}: {count} snapshots ({unique} VMs)\n"

                    report += "\n"

            # Health status
            health = status.get("health", {})
            health_status = health.get("status", "unknown")

            if health_status == "healthy":
                report += "✅ **Status:** Healthy\n"
            elif health_status == "warning":
                report += "⚠️ **Status:** Warning\n"
            elif health_status == "critical":
                report += "🔴 **Status:** Critical\n"
            else:
                report += f"❓ **Status:** {health_status}\n"

            issues = health.get("issues")
            if issues:
                report += "\n**Issues:**\n"
                for issue in issues:
                    report += f"  • {issue}\n"

            # Recent backups
            recent = status.get("recent", [])
            if recent:
                report += "\n**Recent Backups:**\n"
                for backup in recent[:3]:
                    backup_type = backup.get("type", "unknown")
                    backup_id = backup.get("id", "unknown")
                    time_ago = backup.get("time_ago", "unknown")
                    size = backup.get("size_gb", 0)

                    verified = "✅" if backup.get("verified") else "⭕"
                    protected = "🔒" if backup.get("protected") else ""

                    report += f"  • {backup_type}/{backup_id} - {time_ago} ({size} GB) {verified}{protected}\n"

            return report

        except Exception as e:
            self.logger.error(f"Error generating backup report: {e}")
            return f"📦 **Backup Status**: ❌ Error\n\n_{str(e)}_"

    async def get_backup_list(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get list of recent backups

        Args:
            limit: Number of backups to return

        Returns:
            Dict with backup list
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "PBS integration not configured",
                "backups": []
            }

        try:
            return await self.pbs_client.get_recent_backups(limit=limit)

        except Exception as e:
            self.logger.error(f"Error getting backup list: {e}")
            return {
                "success": False,
                "error": str(e),
                "backups": []
            }

    async def check_backup_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for backup-related issues that should trigger alerts

        Returns:
            List of alert dictionaries
        """
        if not self.is_available():
            return []

        alerts = []

        try:
            status = await self.get_backup_status()

            if not status.get("success"):
                alerts.append({
                    "severity": "warning",
                    "message": "Failed to check backup status",
                    "details": status.get("error", "Unknown error")
                })
                return alerts

            # Check health status
            health = status.get("health", {})
            health_status = health.get("status", "unknown")

            if health_status == "critical":
                for issue in health.get("issues", []):
                    alerts.append({
                        "severity": "critical",
                        "message": "Critical backup issue",
                        "details": issue
                    })
            elif health_status == "warning":
                for issue in health.get("issues", []):
                    alerts.append({
                        "severity": "warning",
                        "message": "Backup warning",
                        "details": issue
                    })

            # Check datastore capacity
            datastore = status.get("datastore", {})
            if datastore.get("success"):
                usage = datastore.get("usage_percent", 0)

                if usage >= 95:
                    alerts.append({
                        "severity": "critical",
                        "message": "Datastore nearly full",
                        "details": f"Usage at {usage}%"
                    })
                elif usage >= 85:
                    alerts.append({
                        "severity": "warning",
                        "message": "Datastore filling up",
                        "details": f"Usage at {usage}%"
                    })

            return alerts

        except Exception as e:
            self.logger.error(f"Error checking backup alerts: {e}")
            return [{
                "severity": "warning",
                "message": "Failed to check backup alerts",
                "details": str(e)
            }]


# Global instance
_backup_manager = None


def get_backup_manager() -> BackupManager:
    """Get or create the global backup manager instance"""
    global _backup_manager

    if _backup_manager is None:
        _backup_manager = BackupManager()
        logger.info("Backup manager initialized")

    return _backup_manager
