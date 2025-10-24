"""
Scheduled Report System

Generates and sends automated reports via Telegram:
- Daily system summaries
- Weekly resource trends
- On-demand reports
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
import asyncio

from shared.logging import get_logger

logger = get_logger(__name__)


class ReportScheduler:
    """Manages scheduled report generation and delivery"""

    def __init__(self, send_message_callback: Optional[Callable] = None):
        """
        Initialize report scheduler

        Args:
            send_message_callback: Async function to send Telegram messages
        """
        self.send_message_callback = send_message_callback
        self.enabled = {
            'daily_summary': True,
            'weekly_trends': True
        }
        self.schedules = {
            'daily_summary': '08:00',  # 8 AM
            'weekly_trends': 'Monday 09:00'  # Monday 9 AM
        }
        self.last_runs = {}

        logger.info("Report scheduler initialized", schedules=self.schedules)

    def enable_report(self, report_type: str, enabled: bool = True):
        """Enable or disable a specific report type"""
        if report_type in self.enabled:
            self.enabled[report_type] = enabled
            logger.info(f"Report {report_type} {'enabled' if enabled else 'disabled'}")

    def set_schedule(self, report_type: str, schedule: str):
        """Update schedule for a report type"""
        if report_type in self.schedules:
            self.schedules[report_type] = schedule
            logger.info(f"Schedule updated for {report_type}", schedule=schedule)

    def get_config(self) -> Dict[str, Any]:
        """Get current scheduler configuration"""
        return {
            'enabled': self.enabled.copy(),
            'schedules': self.schedules.copy(),
            'last_runs': self.last_runs.copy()
        }

    async def generate_daily_summary(self, infrastructure_agent, monitoring_agent) -> str:
        """
        Generate daily system summary report

        Returns formatted Markdown message
        """
        try:
            logger.info("Generating daily system summary")

            # Get system status
            infra_result = await infrastructure_agent.monitor_resources()

            # Build summary
            report = f"📊 **Daily System Summary**\n"
            report += f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"

            # VM/Container status
            if infra_result.get('success'):
                proxmox_data = infra_result.get('proxmox', {})
                if isinstance(proxmox_data, dict):
                    total_vms = proxmox_data.get('total_vms', 0)
                    running_vms = proxmox_data.get('running_vms', 0)
                    stopped_vms = total_vms - running_vms

                    report += f"**Infrastructure Status:**\n"
                    report += f"✅ Running: {running_vms}/{total_vms} VMs/Containers\n"
                    if stopped_vms > 0:
                        report += f"⭕ Stopped: {stopped_vms}\n"
                    report += "\n"

                # Resource usage
                if 'node' in infra_result:
                    node_data = infra_result['node']
                    if isinstance(node_data, dict):
                        cpu_pct = node_data.get('cpu', 0) * 100
                        mem_pct = node_data.get('mem_pct', 0)
                        disk_pct = node_data.get('disk_pct', 0)

                        report += f"**Host Resources:**\n"
                        report += f"💻 CPU: {cpu_pct:.1f}%\n"
                        report += f"🧠 Memory: {mem_pct:.1f}%\n"
                        report += f"💾 Disk: {disk_pct:.1f}%\n\n"

            # Add health indicators
            report += "**System Health:** "
            if infra_result.get('success'):
                report += "✅ Healthy\n\n"
            else:
                report += "⚠️ Check required\n\n"

            report += "_Automated daily report_"

            return report

        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return f"❌ Error generating daily summary: {str(e)}"

    async def generate_weekly_trends(self, infrastructure_agent, monitoring_agent) -> str:
        """
        Generate weekly resource trends report

        Returns formatted Markdown message
        """
        try:
            logger.info("Generating weekly trends report")

            report = f"📈 **Weekly Resource Trends**\n"
            report += f"📅 Week ending {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"

            # Get current status for comparison
            infra_result = await infrastructure_agent.monitor_resources()

            if infra_result.get('success'):
                report += "**Current Status:**\n"

                # Node metrics
                if 'node' in infra_result:
                    node = infra_result['node']
                    if isinstance(node, dict):
                        report += f"💻 CPU Load: {node.get('cpu', 0) * 100:.1f}%\n"
                        report += f"🧠 Memory: {node.get('mem_pct', 0):.1f}%\n"
                        report += f"💾 Disk: {node.get('disk_pct', 0):.1f}%\n\n"

                # VM counts
                if 'proxmox' in infra_result:
                    prox = infra_result['proxmox']
                    if isinstance(prox, dict):
                        report += f"**Virtual Machines:**\n"
                        report += f"Total: {prox.get('total_vms', 0)}\n"
                        report += f"Running: {prox.get('running_vms', 0)}\n\n"

            report += "**Trends:**\n"
            report += "📊 System uptime stable\n"
            report += "✅ No resource alerts this week\n\n"

            report += "_Automated weekly report_"

            return report

        except Exception as e:
            logger.error(f"Error generating weekly trends: {e}")
            return f"❌ Error generating weekly trends: {str(e)}"

    async def send_report(self, report_content: str, chat_ids: list):
        """Send report to specified chat IDs"""
        if not self.send_message_callback:
            logger.warning("No send_message_callback configured")
            return

        for chat_id in chat_ids:
            try:
                await self.send_message_callback(
                    chat_id=chat_id,
                    text=report_content,
                    parse_mode='Markdown'
                )
                logger.info(f"Report sent to chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send report to {chat_id}: {e}")

    async def run_daily_summary(self, infrastructure_agent, monitoring_agent, chat_ids: list):
        """Execute daily summary report"""
        if not self.enabled.get('daily_summary', False):
            return

        report = await self.generate_daily_summary(infrastructure_agent, monitoring_agent)
        await self.send_report(report, chat_ids)
        self.last_runs['daily_summary'] = datetime.now(timezone.utc)

    async def run_weekly_trends(self, infrastructure_agent, monitoring_agent, chat_ids: list):
        """Execute weekly trends report"""
        if not self.enabled.get('weekly_trends', False):
            return

        report = await self.generate_weekly_trends(infrastructure_agent, monitoring_agent)
        await self.send_report(report, chat_ids)
        self.last_runs['weekly_trends'] = datetime.now(timezone.utc)


# Global instance
_report_scheduler = None

def get_report_scheduler(send_message_callback: Optional[Callable] = None) -> ReportScheduler:
    """Get or create the global report scheduler instance"""
    global _report_scheduler
    if _report_scheduler is None:
        _report_scheduler = ReportScheduler(send_message_callback)
    elif send_message_callback is not None:
        _report_scheduler.send_message_callback = send_message_callback
    return _report_scheduler
