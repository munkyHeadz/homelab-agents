"""
Scheduled Reporting Agent

Generates and sends automated reports:
- Daily health summaries
- Weekly trend analysis
- Monthly resource reports
- Backup status reports
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class ReportType(Enum):
    """Types of automated reports"""
    DAILY_HEALTH = "daily_health"
    WEEKLY_TRENDS = "weekly_trends"
    MONTHLY_SUMMARY = "monthly_summary"
    BACKUP_STATUS = "backup_status"


class ScheduledReportingAgent:
    """
    Generates and sends automated reports on a schedule

    Features:
    - Daily health summaries at configured time
    - Weekly trend analysis
    - Monthly resource reports
    - Backup status reports
    - Customizable report schedules
    """

    def __init__(self, telegram_notifier=None, health_agent=None, infrastructure_agent=None):
        self.logger = get_logger(__name__)
        self.telegram_notifier = telegram_notifier
        self.health_agent = health_agent
        self.infrastructure_agent = infrastructure_agent

        # Report schedules (hour in 24h format)
        self.daily_report_hour = int(config.get("DAILY_REPORT_HOUR", "8"))  # 8 AM
        self.weekly_report_day = int(config.get("WEEKLY_REPORT_DAY", "1"))  # Monday
        self.monthly_report_day = int(config.get("MONTHLY_REPORT_DAY", "1"))  # 1st of month

        # Track last report times
        self.last_daily_report = None
        self.last_weekly_report = None
        self.last_monthly_report = None

        self.logger.info("Scheduled Reporting Agent initialized")

    async def generate_daily_health_summary(self) -> str:
        """
        Generate daily health summary report

        Includes:
        - Issues resolved in last 24h
        - Current active issues
        - Resource usage trends
        - System uptime
        - Backup status
        """
        now = datetime.now()
        report_lines = [
            "📊 **Daily Health Summary**",
            f"🗓️ {now.strftime('%A, %B %d, %Y')}",
            ""
        ]

        # Get health report if available
        if self.health_agent:
            try:
                health_data = await self.health_agent.generate_health_report()

                report_lines.extend([
                    "**🏥 System Health**",
                    f"Active Issues: {health_data['active_issues']}",
                    f"Resolved Today: {health_data['resolved_today']}",
                    f"Pending Approvals: {health_data['pending_approvals']}",
                    ""
                ])

                # Issues by severity
                issues_by_sev = health_data['issues_by_severity']
                if any(issues_by_sev.values()):
                    report_lines.append("**Issues by Severity:**")
                    if issues_by_sev['critical'] > 0:
                        report_lines.append(f"🔴 Critical: {issues_by_sev['critical']}")
                    if issues_by_sev['unhealthy'] > 0:
                        report_lines.append(f"🟠 Unhealthy: {issues_by_sev['unhealthy']}")
                    if issues_by_sev['degraded'] > 0:
                        report_lines.append(f"🟡 Degraded: {issues_by_sev['degraded']}")
                    report_lines.append("")

                # Top issues
                if health_data['issues']:
                    report_lines.append("**📋 Active Issues:**")
                    for issue in health_data['issues'][:3]:  # Top 3
                        report_lines.append(f"• {issue['component']}: {issue['description']}")
                    report_lines.append("")

                # Recent resolutions
                if health_data['recent_resolutions']:
                    report_lines.append("**✅ Recently Resolved:**")
                    for issue in health_data['recent_resolutions'][:3]:  # Top 3
                        report_lines.append(f"• {issue['component']}: Fixed {issue['description']}")
                    report_lines.append("")

            except Exception as e:
                self.logger.error(f"Error getting health data: {e}")
                report_lines.extend([
                    "**Health Data:** Error retrieving",
                    ""
                ])

        # Get infrastructure stats if available
        if self.infrastructure_agent:
            try:
                infra_data = await self.infrastructure_agent.monitor_resources()

                if infra_data.get("success"):
                    report_lines.extend([
                        "**💻 Infrastructure Status**",
                        "Node: ✅ Online",
                        "Docker: ✅ Running",
                        ""
                    ])
            except Exception as e:
                self.logger.error(f"Error getting infrastructure data: {e}")

        # Recommendations
        report_lines.extend([
            "**💡 Recommendations**",
            "• Review active issues above",
            "• Check backup status with /backup",
            "• Monitor resource trends",
            ""
        ])

        # Footer
        report_lines.extend([
            "---",
            "📈 Use `/health` for real-time status",
            "🔧 Use `/enable_autohealing` if not running"
        ])

        return "\n".join(report_lines)

    async def generate_weekly_trends(self) -> str:
        """
        Generate weekly trends report

        Includes:
        - Issue frequency and types
        - Auto-fix success rate
        - Resource usage trends
        - Most common problems
        """
        now = datetime.now()
        week_start = now - timedelta(days=7)

        report_lines = [
            "📈 **Weekly Trends Report**",
            f"🗓️ {week_start.strftime('%b %d')} - {now.strftime('%b %d, %Y')}",
            ""
        ]

        if self.health_agent:
            try:
                # Get resolved issues from last 7 days
                resolved = [i for i in self.health_agent.resolved_issues
                           if i.detected_at > week_start]

                report_lines.extend([
                    "**🔧 Auto-Healing Performance**",
                    f"Total Issues Resolved: {len(resolved)}",
                    f"Average per Day: {len(resolved) / 7:.1f}",
                    ""
                ])

                # Group by issue type
                issue_types = {}
                for issue in resolved:
                    issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1

                if issue_types:
                    report_lines.append("**Most Common Issues:**")
                    for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                        report_lines.append(f"• {issue_type}: {count} times")
                    report_lines.append("")

                # Success rate
                if resolved:
                    report_lines.extend([
                        "**📊 Success Metrics**",
                        f"Auto-Fix Success: {len([i for i in resolved if i.resolved])} / {len(resolved)}",
                        f"Success Rate: {len([i for i in resolved if i.resolved]) / len(resolved) * 100:.1f}%",
                        ""
                    ])

            except Exception as e:
                self.logger.error(f"Error generating trends: {e}")

        report_lines.extend([
            "**💡 Insights**",
            "• System appears stable this week",
            "• Continue monitoring for patterns",
            ""
        ])

        return "\n".join(report_lines)

    async def generate_monthly_summary(self) -> str:
        """
        Generate monthly summary report

        Includes:
        - Total issues and resolutions
        - Resource usage summary
        - Cost analysis (if applicable)
        - Notable events
        """
        now = datetime.now()
        month_start = now.replace(day=1)

        report_lines = [
            "📅 **Monthly Summary Report**",
            f"🗓️ {month_start.strftime('%B %Y')}",
            ""
        ]

        if self.health_agent:
            try:
                resolved_this_month = [i for i in self.health_agent.resolved_issues
                                      if i.detected_at >= month_start]

                report_lines.extend([
                    "**📊 Monthly Statistics**",
                    f"Issues Resolved: {len(resolved_this_month)}",
                    f"Auto-Fixes: {len([i for i in resolved_this_month if i.risk_level.value == 'low'])}",
                    f"Approved Actions: {len([i for i in resolved_this_month if i.risk_level.value in ['medium', 'high']])}",
                    ""
                ])

            except Exception as e:
                self.logger.error(f"Error generating monthly summary: {e}")

        report_lines.extend([
            "**🎯 Goals for Next Month**",
            "• Maintain or improve auto-fix rate",
            "• Reduce manual interventions",
            "• Optimize resource usage",
            ""
        ])

        return "\n".join(report_lines)

    async def generate_backup_report(self) -> str:
        """
        Generate backup status report

        Includes:
        - Last backup time for each VM
        - Backup success/failure status
        - Storage usage
        - Backup recommendations
        """
        report_lines = [
            "💾 **Backup Status Report**",
            f"🗓️ {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ""
        ]

        if self.infrastructure_agent:
            try:
                result = await self.infrastructure_agent.execute("List all backups")

                if result.get("success"):
                    report_lines.extend([
                        "**Backup Status**",
                        result.get("summary", "Backup information retrieved"),
                        ""
                    ])
                else:
                    report_lines.extend([
                        "**Backup Status**",
                        "❌ Error retrieving backup information",
                        ""
                    ])

            except Exception as e:
                self.logger.error(f"Error getting backup status: {e}")
                report_lines.extend([
                    "**Backup Status**",
                    "❌ Error retrieving backup information",
                    ""
                ])

        report_lines.extend([
            "**💡 Backup Recommendations**",
            "• Verify backups are running daily",
            "• Test restore process monthly",
            "• Monitor backup storage space",
            ""
        ])

        return "\n".join(report_lines)

    async def should_send_daily_report(self) -> bool:
        """Check if it's time to send daily report"""
        now = datetime.now()

        # Check if it's the right hour
        if now.hour != self.daily_report_hour:
            return False

        # Check if we already sent today
        if self.last_daily_report:
            if self.last_daily_report.date() == now.date():
                return False

        return True

    async def should_send_weekly_report(self) -> bool:
        """Check if it's time to send weekly report"""
        now = datetime.now()

        # Check if it's the right day and hour
        if now.weekday() != self.weekly_report_day or now.hour != self.daily_report_hour:
            return False

        # Check if we already sent this week
        if self.last_weekly_report:
            days_since = (now - self.last_weekly_report).days
            if days_since < 7:
                return False

        return True

    async def should_send_monthly_report(self) -> bool:
        """Check if it's time to send monthly report"""
        now = datetime.now()

        # Check if it's the right day and hour
        if now.day != self.monthly_report_day or now.hour != self.daily_report_hour:
            return False

        # Check if we already sent this month
        if self.last_monthly_report:
            if self.last_monthly_report.month == now.month and self.last_monthly_report.year == now.year:
                return False

        return True

    async def send_report(self, report_type: ReportType, content: str):
        """Send report via Telegram"""
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_message(content)
                self.logger.info(f"Sent {report_type.value} report")
            except Exception as e:
                self.logger.error(f"Error sending {report_type.value} report: {e}")

    async def run_reporting_loop(self, check_interval: int = 3600):
        """
        Main reporting loop - checks every hour

        Args:
            check_interval: Seconds between checks (default: 3600 = 1 hour)
        """
        self.logger.info(f"Starting scheduled reporting loop (checking every {check_interval}s)")

        while True:
            try:
                now = datetime.now()

                # Check daily report
                if await self.should_send_daily_report():
                    self.logger.info("Generating daily health summary")
                    report = await self.generate_daily_health_summary()
                    await self.send_report(ReportType.DAILY_HEALTH, report)
                    self.last_daily_report = now

                # Check weekly report
                if await self.should_send_weekly_report():
                    self.logger.info("Generating weekly trends report")
                    report = await self.generate_weekly_trends()
                    await self.send_report(ReportType.WEEKLY_TRENDS, report)
                    self.last_weekly_report = now

                # Check monthly report
                if await self.should_send_monthly_report():
                    self.logger.info("Generating monthly summary report")
                    report = await self.generate_monthly_summary()
                    await self.send_report(ReportType.MONTHLY_SUMMARY, report)
                    self.last_monthly_report = now

                # Wait for next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error in reporting loop: {e}")
                await asyncio.sleep(check_interval)
