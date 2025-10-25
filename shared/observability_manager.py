"""
Observability Manager

Provides high-level observability and monitoring dashboard:
- Current system metrics display
- Grafana dashboard links
- Prometheus query interface
- Performance monitoring
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from shared.logging import get_logger
from integrations.prometheus_client import get_prometheus_client

logger = get_logger(__name__)


class ObservabilityManager:
    """Manages observability and monitoring dashboards"""

    def __init__(self):
        self.logger = logger
        self.prometheus_client = get_prometheus_client()

        # Grafana configuration
        self.grafana_url = os.getenv("GRAFANA_URL", "http://192.168.1.105:3000")
        self.grafana_host = os.getenv("GRAFANA_HOST", "192.168.1.105")
        self.grafana_port = int(os.getenv("GRAFANA_PORT", "3000"))

        # Prometheus configuration
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://192.168.1.104:9090")

        if not self.prometheus_client:
            self.logger.warning("ObservabilityManager initialized without Prometheus client")

    def is_available(self) -> bool:
        """Check if Prometheus integration is available"""
        return self.prometheus_client is not None

    async def get_metrics_dashboard(self) -> str:
        """
        Generate metrics dashboard for Telegram

        Returns:
            Markdown-formatted metrics dashboard
        """
        if not self.is_available():
            return "📊 **System Metrics**: ⚠️ Prometheus not configured"

        try:
            # Get health status
            health = await self.prometheus_client.health_check()

            if not health.get("healthy"):
                return f"📊 **System Metrics**: ❌ Prometheus unavailable\n\n_{health.get('error', 'Connection failed')}_"

            # Get current metrics
            metrics_result = await self.prometheus_client.get_current_metrics()

            if not metrics_result.get("success"):
                return f"📊 **System Metrics**: ❌ Error retrieving metrics\n\n_{metrics_result.get('error', 'Unknown error')}_"

            metrics = metrics_result.get("metrics", {})

            report = "📊 **System Metrics Dashboard**\n\n"
            report += f"_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n\n"

            # CPU metrics
            cpu_metrics = metrics.get("cpu", [])
            if cpu_metrics:
                report += "**💻 CPU Usage:**\n"
                for metric in cpu_metrics:
                    instance = metric.get("instance", "unknown").split(":")[0]
                    usage = metric.get("usage_percent", 0)

                    emoji = "🟢" if usage < 70 else "🟡" if usage < 85 else "🔴"
                    report += f"{emoji} {instance}: {usage}%\n"

                report += "\n"

            # Memory metrics
            mem_metrics = metrics.get("memory", [])
            if mem_metrics:
                report += "**🧠 Memory Usage:**\n"
                for metric in mem_metrics:
                    instance = metric.get("instance", "unknown").split(":")[0]
                    usage = metric.get("usage_percent", 0)

                    emoji = "🟢" if usage < 80 else "🟡" if usage < 90 else "🔴"
                    report += f"{emoji} {instance}: {usage}%\n"

                report += "\n"

            # Disk metrics
            disk_metrics = metrics.get("disk", [])
            if disk_metrics:
                report += "**💾 Disk Usage:**\n"
                for metric in disk_metrics:
                    instance = metric.get("instance", "unknown").split(":")[0]
                    usage = metric.get("usage_percent", 0)

                    emoji = "🟢" if usage < 80 else "🟡" if usage < 90 else "🔴"
                    report += f"{emoji} {instance}: {usage}%\n"

                report += "\n"

            # Get targets status
            targets_result = await self.prometheus_client.get_targets()

            if targets_result.get("success"):
                active = targets_result.get("active_count", 0)
                dropped = targets_result.get("dropped_count", 0)

                report += "**🎯 Prometheus Targets:**\n"
                report += f"  • Active: {active}\n"
                if dropped > 0:
                    report += f"  • Dropped: {dropped}\n"
                report += "\n"

            # Get alert status
            alerts_result = await self.prometheus_client.get_alerts()

            if alerts_result.get("success"):
                total = alerts_result.get("total", 0)
                firing = alerts_result.get("firing_count", 0)
                pending = alerts_result.get("pending_count", 0)

                report += "**🚨 Prometheus Alerts:**\n"
                if firing > 0:
                    report += f"  • 🔴 Firing: {firing}\n"
                if pending > 0:
                    report += f"  • 🟡 Pending: {pending}\n"
                if firing == 0 and pending == 0:
                    report += f"  • ✅ No active alerts\n"

                report += f"  • Total: {total}\n\n"

            # Links
            report += "**🔗 Dashboards:**\n"
            report += f"  • [Prometheus]({self.prometheus_url})\n"
            report += f"  • [Grafana]({self.grafana_url})\n"

            return report

        except Exception as e:
            self.logger.error(f"Error generating metrics dashboard: {e}")
            return f"📊 **System Metrics**: ❌ Error\n\n_{str(e)}_"

    async def get_prometheus_alerts(self) -> str:
        """
        Get Prometheus alerts formatted for Telegram

        Returns:
            Markdown-formatted alerts list
        """
        if not self.is_available():
            return "🚨 **Prometheus Alerts**: ⚠️ Prometheus not configured"

        try:
            alerts_result = await self.prometheus_client.get_alerts()

            if not alerts_result.get("success"):
                return f"🚨 **Prometheus Alerts**: ❌ Error\n\n_{alerts_result.get('error', 'Unknown error')}_"

            total = alerts_result.get("total", 0)
            firing_count = alerts_result.get("firing_count", 0)
            pending_count = alerts_result.get("pending_count", 0)
            by_state = alerts_result.get("by_state", {})

            report = "🚨 **Prometheus Alerts**\n\n"

            if total == 0:
                report += "✅ No alerts\n\n"
                report += f"[View in Prometheus]({self.prometheus_url}/alerts)"
                return report

            report += f"**Summary:** {firing_count} firing, {pending_count} pending\n\n"

            # Firing alerts
            firing_alerts = by_state.get("firing", [])
            if firing_alerts:
                report += "**🔴 Firing Alerts:**\n"
                for alert in firing_alerts[:10]:  # Limit to 10
                    name = alert.get("labels", {}).get("alertname", "Unknown")
                    instance = alert.get("labels", {}).get("instance", "")
                    severity = alert.get("labels", {}).get("severity", "unknown")
                    summary = alert.get("annotations", {}).get("summary", "")

                    report += f"\n**{name}**"
                    if severity:
                        report += f" [{severity}]"
                    report += "\n"

                    if instance:
                        report += f"  • Instance: {instance}\n"

                    if summary:
                        report += f"  • {summary}\n"

                if len(firing_alerts) > 10:
                    report += f"\n_...and {len(firing_alerts) - 10} more_\n"

                report += "\n"

            # Pending alerts
            pending_alerts = by_state.get("pending", [])
            if pending_alerts:
                report += "**🟡 Pending Alerts:**\n"
                for alert in pending_alerts[:5]:  # Limit to 5
                    name = alert.get("labels", {}).get("alertname", "Unknown")
                    instance = alert.get("labels", {}).get("instance", "")

                    report += f"  • {name}"
                    if instance:
                        report += f" ({instance})"
                    report += "\n"

                if len(pending_alerts) > 5:
                    report += f"  _...and {len(pending_alerts) - 5} more_\n"

                report += "\n"

            report += f"[View all in Prometheus]({self.prometheus_url}/alerts)"

            return report

        except Exception as e:
            self.logger.error(f"Error getting Prometheus alerts: {e}")
            return f"🚨 **Prometheus Alerts**: ❌ Error\n\n_{str(e)}_"

    async def get_grafana_links(self) -> str:
        """
        Get Grafana dashboard links

        Returns:
            Markdown-formatted Grafana links
        """
        report = "📊 **Grafana Dashboards**\n\n"

        # Common dashboard links
        dashboards = [
            {
                "name": "Home",
                "path": "/"
            },
            {
                "name": "Node Exporter Full",
                "path": "/d/rYdddlPWk/node-exporter-full"
            },
            {
                "name": "Prometheus Stats",
                "path": "/d/prometheus-stats/prometheus-stats"
            },
            {
                "name": "Alertmanager",
                "path": "/d/alertmanager/alertmanager"
            }
        ]

        report += "**Quick Links:**\n"
        for dashboard in dashboards:
            name = dashboard["name"]
            url = f"{self.grafana_url}{dashboard['path']}"
            report += f"  • [{name}]({url})\n"

        report += f"\n**Grafana URL:**\n`{self.grafana_url}`\n"

        return report

    async def query_prometheus(self, query: str) -> str:
        """
        Execute custom Prometheus query

        Args:
            query: PromQL query string

        Returns:
            Markdown-formatted query results
        """
        if not self.is_available():
            return "⚠️ Prometheus not configured"

        try:
            result = await self.prometheus_client.query(query)

            if not result.get("success"):
                return f"❌ Query failed:\n\n`{result.get('error', 'Unknown error')}`"

            result_type = result.get("result_type", "unknown")
            results = result.get("result", [])

            report = f"**Query:** `{query}`\n\n"
            report += f"**Type:** {result_type}\n"
            report += f"**Results:** {len(results)}\n\n"

            if not results:
                report += "_No results_"
                return report

            # Format results
            for i, res in enumerate(results[:10]):  # Limit to 10 results
                metric = res.get("metric", {})
                value = res.get("value", [])

                if metric:
                    report += f"**Result {i+1}:**\n"
                    for key, val in metric.items():
                        report += f"  • {key}: {val}\n"

                    if len(value) == 2:
                        timestamp = datetime.fromtimestamp(value[0], tz=timezone.utc)
                        val = value[1]
                        report += f"  • value: {val}\n"
                        report += f"  • time: {timestamp.strftime('%H:%M:%S')}\n"

                    report += "\n"

            if len(results) > 10:
                report += f"_...and {len(results) - 10} more results_"

            return report

        except Exception as e:
            self.logger.error(f"Error executing Prometheus query: {e}")
            return f"❌ Query error:\n\n`{str(e)}`"


# Global instance
_observability_manager = None


def get_observability_manager() -> ObservabilityManager:
    """Get or create the global observability manager instance"""
    global _observability_manager

    if _observability_manager is None:
        _observability_manager = ObservabilityManager()
        logger.info("Observability manager initialized")

    return _observability_manager
