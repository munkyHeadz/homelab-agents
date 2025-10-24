"""
Prometheus Alert Receiver

Receives alerts from Prometheus Alertmanager and forwards to:
- Telegram (for user notification)
- Autonomous Health Agent (for auto-remediation)

Setup:
1. Configure Alertmanager to send webhooks to this endpoint
2. Run this as a background service
3. Alerts will be processed and forwarded appropriately
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from aiohttp import web

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class PrometheusAlertReceiver:
    """
    Receives and processes Prometheus alerts

    Features:
    - Webhook endpoint for Alertmanager
    - Alert parsing and formatting
    - Forwarding to Telegram
    - Integration with Autonomous Health Agent
    - Alert deduplication
    - Alert grouping
    """

    def __init__(self, telegram_notifier=None, health_agent=None):
        self.logger = get_logger(__name__)
        self.telegram_notifier = telegram_notifier
        self.health_agent = health_agent

        # Track recent alerts to avoid duplicates
        self.recent_alerts: Dict[str, datetime] = {}
        self.dedup_window = 300  # 5 minutes

        # Configuration
        self.webhook_port = int(config.get("PROMETHEUS_WEBHOOK_PORT", "9095"))
        self.webhook_path = config.get("PROMETHEUS_WEBHOOK_PATH", "/prometheus/webhook")

        self.logger.info(f"Prometheus Alert Receiver initialized on port {self.webhook_port}")

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming Prometheus webhook

        Expected format from Alertmanager:
        {
          "receiver": "homelab-telegram",
          "status": "firing|resolved",
          "alerts": [
            {
              "status": "firing|resolved",
              "labels": {
                "alertname": "HighCPU",
                "severity": "warning",
                "instance": "node1",
                ...
              },
              "annotations": {
                "summary": "High CPU usage detected",
                "description": "CPU usage is above 90%"
              },
              "startsAt": "2025-01-01T00:00:00Z",
              "endsAt": "0001-01-01T00:00:00Z",
              "generatorURL": "http://prometheus:9090/graph?..."
            }
          ],
          "groupLabels": {...},
          "commonLabels": {...},
          "commonAnnotations": {...},
          "externalURL": "http://alertmanager:9093",
          "version": "4",
          "groupKey": "...",
          "truncatedAlerts": 0
        }
        """
        try:
            data = await request.json()

            self.logger.info(f"Received Prometheus webhook: {data.get('status', 'unknown')} status")

            # Process each alert
            alerts = data.get("alerts", [])
            for alert in alerts:
                await self.process_alert(alert, data.get("status"))

            return web.Response(text="OK", status=200)

        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}")
            return web.Response(text=f"Error: {str(e)}", status=500)

    async def process_alert(self, alert: Dict[str, Any], group_status: str):
        """Process a single alert"""
        try:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            status = alert.get("status", group_status)

            # Extract key information
            alertname = labels.get("alertname", "Unknown")
            severity = labels.get("severity", "info")
            instance = labels.get("instance", "")
            summary = annotations.get("summary", "")
            description = annotations.get("description", "")

            # Check for duplicates
            alert_key = f"{alertname}:{instance}:{status}"
            if alert_key in self.recent_alerts:
                last_sent = self.recent_alerts[alert_key]
                if (datetime.now() - last_sent).total_seconds() < self.dedup_window:
                    self.logger.debug(f"Skipping duplicate alert: {alert_key}")
                    return

            # Update recent alerts
            self.recent_alerts[alert_key] = datetime.now()

            # Format alert for Telegram
            if status == "firing":
                await self.handle_firing_alert(alertname, severity, instance, summary, description, alert)
            elif status == "resolved":
                await self.handle_resolved_alert(alertname, instance, summary)

        except Exception as e:
            self.logger.error(f"Error processing alert: {e}")

    async def handle_firing_alert(self, alertname: str, severity: str, instance: str,
                                  summary: str, description: str, alert: Dict[str, Any]):
        """Handle a firing alert"""
        # Determine severity emoji
        if severity == "critical":
            emoji = "🔴"
            sev_text = "CRITICAL"
        elif severity == "warning":
            emoji = "🟡"
            sev_text = "WARNING"
        else:
            emoji = "🔵"
            sev_text = "INFO"

        # Build Telegram message
        message = f"""{emoji} **Prometheus Alert**

**{alertname}**
Severity: {sev_text}
Instance: {instance}

**Summary:** {summary}

**Description:** {description}

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Send to Telegram
        if self.telegram_notifier:
            await self.telegram_notifier.send_message(message)

        # Forward to Autonomous Health Agent for possible auto-remediation
        if self.health_agent and severity in ["critical", "warning"]:
            await self.forward_to_health_agent(alertname, severity, instance, description, alert)

    async def handle_resolved_alert(self, alertname: str, instance: str, summary: str):
        """Handle a resolved alert"""
        message = f"""✅ **Alert Resolved**

**{alertname}**
Instance: {instance}

{summary}

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Send to Telegram
        if self.telegram_notifier:
            await self.telegram_notifier.send_message(message)

    async def forward_to_health_agent(self, alertname: str, severity: str, instance: str,
                                      description: str, alert: Dict[str, Any]):
        """
        Forward alert to Autonomous Health Agent for potential auto-remediation

        The health agent will:
        1. Analyze the alert
        2. Determine if it's something it can fix
        3. Take action or request approval
        """
        try:
            from agents.autonomous_health_agent import HealthIssue, HealthStatus, RiskLevel

            # Map alert to health issue
            severity_map = {
                "critical": HealthStatus.CRITICAL,
                "warning": HealthStatus.UNHEALTHY,
                "info": HealthStatus.DEGRADED
            }

            # Create health issue from alert
            issue = HealthIssue(
                component=instance or "prometheus_alert",
                issue_type=f"prometheus_{alertname.lower()}",
                severity=severity_map.get(severity, HealthStatus.DEGRADED),
                description=description or alertname,
                metrics={
                    "alertname": alertname,
                    "severity": severity,
                    "instance": instance,
                    "alert_data": alert
                },
                suggested_fix=self._suggest_fix_for_alert(alertname, alert),
                risk_level=RiskLevel.MEDIUM  # Prometheus alerts default to MEDIUM risk
            )

            # Diagnose and potentially act on the issue
            issue = await self.health_agent.diagnose_issue(issue)

            # Add to active issues
            self.health_agent.active_issues.append(issue)

            # Attempt remediation based on risk level
            if issue.risk_level == RiskLevel.LOW:
                success, message = await self.health_agent.attempt_auto_heal(issue)
                if success:
                    self.logger.info(f"Auto-healed Prometheus alert: {alertname}")
            else:
                # Request approval via Telegram
                await self.health_agent.request_approval(issue)

        except Exception as e:
            self.logger.error(f"Error forwarding to health agent: {e}")

    def _suggest_fix_for_alert(self, alertname: str, alert: Dict[str, Any]) -> str:
        """Suggest a fix based on the alert name"""
        suggestions = {
            "HighCPU": "Identify and optimize high-CPU processes",
            "HighMemory": "Clear caches or stop non-essential services",
            "HighDiskUsage": "Clean up old logs and unused data",
            "ContainerDown": "Restart the affected container",
            "ServiceDown": "Restart the affected service",
            "HighLatency": "Check network connectivity and service health",
            "HostDown": "Investigate host connectivity",
        }

        return suggestions.get(alertname, f"Investigate {alertname} alert")

    async def cleanup_old_alerts(self):
        """Clean up old entries from recent_alerts to prevent memory growth"""
        now = datetime.now()
        to_remove = []

        for alert_key, timestamp in self.recent_alerts.items():
            if (now - timestamp).total_seconds() > self.dedup_window:
                to_remove.append(alert_key)

        for key in to_remove:
            del self.recent_alerts[key]

    async def run_server(self):
        """Run the webhook server"""
        app = web.Application()
        app.router.add_post(self.webhook_path, self.handle_webhook)

        # Add health check endpoint
        async def health_check(request):
            return web.Response(text="OK", status=200)

        app.router.add_get("/health", health_check)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.webhook_port)

        self.logger.info(f"Starting Prometheus webhook server on port {self.webhook_port}")
        await site.start()

        # Start cleanup task
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(600)  # Every 10 minutes
                await self.cleanup_old_alerts()

        asyncio.create_task(periodic_cleanup())

        # Keep running
        while True:
            await asyncio.sleep(3600)


async def main():
    """Run the Prometheus alert receiver standalone"""
    receiver = PrometheusAlertReceiver()
    await receiver.run_server()


if __name__ == "__main__":
    asyncio.run(main())
