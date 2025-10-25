"""
Scheduled Report Generator

Generates automated system reports:
- Daily system summary (infrastructure, network, alerts)
- Weekly trends (resource usage, incidents)
- Monthly cost/performance reports
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum

from shared.logging import get_logger

logger = get_logger(__name__)


class ReportType(str, Enum):
    """Types of automated reports"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_TRENDS = "weekly_trends"
    MONTHLY_SUMMARY = "monthly_summary"


class ReportGenerator:
    """Generates formatted reports for Telegram"""

    def __init__(self, infrastructure_agent=None, network_agent=None, alert_manager=None):
        self.infrastructure_agent = infrastructure_agent
        self.network_agent = network_agent
        self.alert_manager = alert_manager
        self.logger = logger

    async def generate_daily_summary(self) -> str:
        """
        Generate daily system summary report

        Returns:
            Formatted markdown report
        """
        try:
            self.logger.info("Generating daily summary report")

            report_time = datetime.now(timezone.utc)
            report = f"📊 **Daily System Summary**\n"
            report += f"_{report_time.strftime('%Y-%m-%d %H:%M UTC')}_\n\n"

            # Infrastructure Status
            if self.infrastructure_agent:
                try:
                    result = await self.infrastructure_agent.execute(
                        "Get summary of all VMs and containers with their status and resource usage"
                    )

                    if result.get("success"):
                        report += "**🖥️ Infrastructure:**\n"
                        summary = result.get("summary", "No data available")
                        # Extract key metrics from summary
                        report += f"_{summary[:200]}..._\n\n"
                    else:
                        report += "**🖥️ Infrastructure:** ⚠️ Unable to retrieve\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting infrastructure data: {e}")
                    report += "**🖥️ Infrastructure:** ❌ Error\n\n"

            # Network Status
            if self.network_agent:
                try:
                    status = await self.network_agent.get_network_status()

                    if status.get("success"):
                        network = status.get("network", {})
                        services = status.get("services", {})

                        report += "**🌐 Network:**\n"
                        report += f"  • Status: {network.get('status', 'unknown').title()}\n"
                        report += f"  • Connected Devices: {network.get('connected_devices', 0)}\n"
                        report += f"  • Uptime: {network.get('uptime_hours', 0):.1f}h\n"

                        # Service status
                        unifi_status = "✅" if services.get("unifi") == "available" else "⚠️"
                        adguard_status = "✅" if services.get("adguard") == "available" else "⚠️"
                        report += f"  • Unifi: {unifi_status} | AdGuard: {adguard_status}\n\n"
                    else:
                        report += "**🌐 Network:** ⚠️ Unable to retrieve\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting network data: {e}")
                    report += "**🌐 Network:** ❌ Error\n\n"

            # Alert Status
            if self.alert_manager:
                try:
                    stats = self.alert_manager.get_stats()

                    report += "**🚨 Alerts (24h):**\n"

                    if stats.get("firing", 0) > 0:
                        report += f"  • 🔴 Active: {stats.get('firing', 0)}\n"
                        report += f"  • Critical: {stats.get('critical', 0)}\n"
                        report += f"  • Warning: {stats.get('warning', 0)}\n"
                    else:
                        report += f"  • ✅ No active alerts\n"

                    report += f"  • Acknowledged: {stats.get('acknowledged', 0)}\n"
                    report += f"  • Silenced: {stats.get('silenced', 0)}\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting alert data: {e}")
                    report += "**🚨 Alerts:** ❌ Error\n\n"

            # Footer
            report += "---\n"
            report += "_Next report: Tomorrow at 08:00 UTC_"

            self.logger.info("Daily summary report generated successfully")
            return report

        except Exception as e:
            self.logger.error(f"Error generating daily summary: {e}")
            return f"❌ Error generating daily report: {str(e)}"

    async def generate_weekly_trends(self) -> str:
        """
        Generate weekly trends report

        Returns:
            Formatted markdown report
        """
        try:
            self.logger.info("Generating weekly trends report")

            report_time = datetime.now(timezone.utc)
            week_start = report_time - timedelta(days=7)

            report = f"📈 **Weekly Trends Report**\n"
            report += f"_{week_start.strftime('%Y-%m-%d')} to {report_time.strftime('%Y-%m-%d')}_\n\n"

            # Infrastructure Trends
            report += "**🖥️ Infrastructure Highlights:**\n"

            if self.infrastructure_agent:
                try:
                    result = await self.infrastructure_agent.execute(
                        "Analyze resource usage trends and provide optimization recommendations"
                    )

                    if result.get("success"):
                        summary = result.get("summary", "No trends data")
                        report += f"_{summary[:300]}..._\n\n"
                    else:
                        report += "_No infrastructure data available_\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting infrastructure trends: {e}")
                    report += "_Error retrieving infrastructure trends_\n\n"

            # Network Trends
            if self.network_agent:
                try:
                    # Get current network status as baseline
                    status = await self.network_agent.get_network_status()

                    if status.get("success"):
                        network = status.get("network", {})

                        report += "**🌐 Network Trends:**\n"
                        report += f"  • Current Uptime: {network.get('uptime_hours', 0):.1f}h\n"
                        report += f"  • Active Devices: {network.get('connected_devices', 0)}\n"
                        report += f"  • Status: {network.get('status', 'unknown').title()}\n\n"
                    else:
                        report += "**🌐 Network Trends:** _No data_\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting network trends: {e}")
                    report += "**🌐 Network Trends:** _Error_\n\n"

            # Alert Trends
            if self.alert_manager:
                try:
                    stats = self.alert_manager.get_stats()

                    report += "**🚨 Alert Summary:**\n"
                    report += f"  • Total Alerts: {stats.get('total', 0)}\n"
                    report += f"  • Resolved: {stats.get('resolved', 0)}\n"
                    report += f"  • Currently Active: {stats.get('firing', 0)}\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting alert trends: {e}")
                    report += "**🚨 Alert Summary:** _Error_\n\n"

            # Recommendations
            report += "**💡 Recommendations:**\n"
            report += "_System operating within normal parameters_\n\n"

            report += "---\n"
            report += "_Next weekly report: Next Monday at 08:00 UTC_"

            self.logger.info("Weekly trends report generated successfully")
            return report

        except Exception as e:
            self.logger.error(f"Error generating weekly trends: {e}")
            return f"❌ Error generating weekly report: {str(e)}"

    async def generate_monthly_summary(self) -> str:
        """
        Generate monthly summary report

        Returns:
            Formatted markdown report
        """
        try:
            self.logger.info("Generating monthly summary report")

            report_time = datetime.now(timezone.utc)
            month_start = report_time.replace(day=1)

            report = f"📅 **Monthly Summary Report**\n"
            report += f"_{month_start.strftime('%B %Y')}_\n\n"

            # System Overview
            report += "**📊 System Overview:**\n"

            if self.infrastructure_agent:
                try:
                    result = await self.infrastructure_agent.execute(
                        "Provide monthly summary of system performance and resource utilization"
                    )

                    if result.get("success"):
                        summary = result.get("summary", "No monthly data")
                        report += f"{summary[:400]}\n\n"
                    else:
                        report += "_No infrastructure data available_\n\n"
                except Exception as e:
                    self.logger.error(f"Error getting monthly infrastructure: {e}")
                    report += "_Error retrieving infrastructure data_\n\n"

            # Network Summary
            report += "**🌐 Network Summary:**\n"
            report += "_Monthly network statistics will be available once tracking is enabled_\n\n"

            # Incident Summary
            if self.alert_manager:
                report += "**🚨 Incident Summary:**\n"
                stats = self.alert_manager.get_stats()
                report += f"  • Total Incidents: {stats.get('total', 0)}\n"
                report += f"  • Resolved: {stats.get('resolved', 0)}\n\n"

            # Cost Tracking (placeholder)
            report += "**💰 Resource Usage:**\n"
            report += "_Cost tracking will be available in future updates_\n\n"

            report += "---\n"
            report += "_Next monthly report: First day of next month_"

            self.logger.info("Monthly summary report generated successfully")
            return report

        except Exception as e:
            self.logger.error(f"Error generating monthly summary: {e}")
            return f"❌ Error generating monthly report: {str(e)}"


# Global instance
_report_generator = None


def get_report_generator(infrastructure_agent=None, network_agent=None, alert_manager=None):
    """Get or create the global report generator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator(infrastructure_agent, network_agent, alert_manager)
    else:
        # Update agents if provided
        if infrastructure_agent is not None:
            _report_generator.infrastructure_agent = infrastructure_agent
        if network_agent is not None:
            _report_generator.network_agent = network_agent
        if alert_manager is not None:
            _report_generator.alert_manager = alert_manager
    return _report_generator
