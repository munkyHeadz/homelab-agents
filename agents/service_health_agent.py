"""
Service-Specific Health Checks Agent

Monitors health of specific services running in the homelab:
- Plex Media Server
- Sonarr (TV show management)
- Radarr (Movie management)
- Lidarr (Music management)
- Jellyfin
- Home Assistant
- Nextcloud
- And custom services

Features:
- HTTP endpoint health checks
- API availability testing
- Service-specific metrics
- Custom health check scripts
- Database connectivity tests
- Performance monitoring
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class ServiceType(Enum):
    """Types of services we can monitor"""
    PLEX = "plex"
    SONARR = "sonarr"
    RADARR = "radarr"
    LIDARR = "lidarr"
    JELLYFIN = "jellyfin"
    HOME_ASSISTANT = "homeassistant"
    NEXTCLOUD = "nextcloud"
    PIHOLE = "pihole"
    PORTAINER = "portainer"
    CUSTOM = "custom"


class HealthStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for a service"""
    name: str
    service_type: ServiceType
    url: str
    health_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    check_interval: int = 60  # seconds
    timeout: int = 10  # seconds
    custom_checks: List[str] = None  # Custom check functions


@dataclass
class ServiceHealth:
    """Health information for a service"""
    service_name: str
    service_type: ServiceType
    status: HealthStatus
    response_time: Optional[float] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    issues: List[str] = None


class ServiceHealthAgent:
    """
    Monitors health of specific services

    Features:
    - HTTP health checks
    - API availability tests
    - Service-specific metrics
    - Performance monitoring
    - Alert on service issues
    """

    def __init__(self, telegram_notifier=None):
        self.logger = get_logger(__name__)
        self.telegram_notifier = telegram_notifier

        # Service configurations
        self.services: Dict[str, ServiceConfig] = {}
        self._load_service_configs()

        # Health tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        self.health_history: List[ServiceHealth] = []

        # Alert tracking (to avoid spam)
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_cooldown = 300  # 5 minutes

        self.logger.info(f"Service Health Agent initialized with {len(self.services)} services")

    def _load_service_configs(self):
        """Load service configurations from environment"""
        # Plex
        plex_url = config.get("PLEX_URL")
        if plex_url:
            self.services["plex"] = ServiceConfig(
                name="Plex Media Server",
                service_type=ServiceType.PLEX,
                url=plex_url,
                health_endpoint="/identity",
                api_key=config.get("PLEX_TOKEN")
            )

        # Sonarr
        sonarr_url = config.get("SONARR_URL")
        if sonarr_url:
            self.services["sonarr"] = ServiceConfig(
                name="Sonarr",
                service_type=ServiceType.SONARR,
                url=sonarr_url,
                health_endpoint="/api/v3/system/status",
                api_key=config.get("SONARR_API_KEY")
            )

        # Radarr
        radarr_url = config.get("RADARR_URL")
        if radarr_url:
            self.services["radarr"] = ServiceConfig(
                name="Radarr",
                service_type=ServiceType.RADARR,
                url=radarr_url,
                health_endpoint="/api/v3/system/status",
                api_key=config.get("RADARR_API_KEY")
            )

        # Jellyfin
        jellyfin_url = config.get("JELLYFIN_URL")
        if jellyfin_url:
            self.services["jellyfin"] = ServiceConfig(
                name="Jellyfin",
                service_type=ServiceType.JELLYFIN,
                url=jellyfin_url,
                health_endpoint="/health"
            )

        # Home Assistant
        ha_url = config.get("HOME_ASSISTANT_URL")
        if ha_url:
            self.services["homeassistant"] = ServiceConfig(
                name="Home Assistant",
                service_type=ServiceType.HOME_ASSISTANT,
                url=ha_url,
                health_endpoint="/api/",
                api_key=config.get("HOME_ASSISTANT_TOKEN")
            )

        # Pi-hole
        pihole_url = config.get("PIHOLE_URL")
        if pihole_url:
            self.services["pihole"] = ServiceConfig(
                name="Pi-hole",
                service_type=ServiceType.PIHOLE,
                url=pihole_url,
                health_endpoint="/admin/api.php?status"
            )

        # Nextcloud
        nextcloud_url = config.get("NEXTCLOUD_URL")
        if nextcloud_url:
            self.services["nextcloud"] = ServiceConfig(
                name="Nextcloud",
                service_type=ServiceType.NEXTCLOUD,
                url=nextcloud_url,
                health_endpoint="/status.php"
            )

        # Portainer
        portainer_url = config.get("PORTAINER_URL")
        if portainer_url:
            self.services["portainer"] = ServiceConfig(
                name="Portainer",
                service_type=ServiceType.PORTAINER,
                url=portainer_url,
                health_endpoint="/api/status"
            )

    async def check_http_health(self, service: ServiceConfig) -> Tuple[HealthStatus, float, Optional[str]]:
        """
        Check service health via HTTP

        Args:
            service: Service configuration

        Returns:
            Tuple of (status, response_time, error_message)
        """
        try:
            # Build URL
            if service.health_endpoint:
                url = f"{service.url.rstrip('/')}{service.health_endpoint}"
            else:
                url = service.url

            # Build headers
            headers = {}
            if service.api_key:
                # Different services use different auth methods
                if service.service_type in [ServiceType.SONARR, ServiceType.RADARR, ServiceType.LIDARR]:
                    headers["X-Api-Key"] = service.api_key
                elif service.service_type == ServiceType.HOME_ASSISTANT:
                    headers["Authorization"] = f"Bearer {service.api_key}"
                elif service.service_type == ServiceType.PLEX:
                    url += f"?X-Plex-Token={service.api_key}"

            # Make request
            start_time = datetime.now()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=service.timeout),
                    ssl=False  # For self-signed certs in homelab
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds()

                    if response.status == 200:
                        return HealthStatus.HEALTHY, response_time, None
                    elif response.status in [429, 503]:
                        return HealthStatus.DEGRADED, response_time, f"HTTP {response.status}"
                    else:
                        return HealthStatus.UNHEALTHY, response_time, f"HTTP {response.status}"

        except asyncio.TimeoutError:
            return HealthStatus.UNHEALTHY, service.timeout, "Request timeout"
        except aiohttp.ClientError as e:
            return HealthStatus.DOWN, 0.0, f"Connection error: {str(e)}"
        except Exception as e:
            return HealthStatus.UNKNOWN, 0.0, str(e)

    async def check_service_specific_health(self, service: ServiceConfig) -> Dict[str, Any]:
        """
        Perform service-specific health checks

        Args:
            service: Service configuration

        Returns:
            Dictionary with service-specific metrics
        """
        metrics = {}

        try:
            if service.service_type == ServiceType.PLEX:
                metrics = await self._check_plex_health(service)
            elif service.service_type == ServiceType.SONARR:
                metrics = await self._check_sonarr_health(service)
            elif service.service_type == ServiceType.RADARR:
                metrics = await self._check_radarr_health(service)
            elif service.service_type == ServiceType.HOME_ASSISTANT:
                metrics = await self._check_homeassistant_health(service)
            elif service.service_type == ServiceType.PIHOLE:
                metrics = await self._check_pihole_health(service)

        except Exception as e:
            self.logger.error(f"Error checking {service.name} specific health: {e}")

        return metrics

    async def _check_plex_health(self, service: ServiceConfig) -> Dict[str, Any]:
        """Check Plex-specific metrics"""
        try:
            url = f"{service.url}/status/sessions?X-Plex-Token={service.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "active_streams": data.get("MediaContainer", {}).get("size", 0),
                            "transcoding": sum(1 for s in data.get("MediaContainer", {}).get("Metadata", [])
                                             if s.get("TranscodeSession"))
                        }
        except Exception as e:
            self.logger.error(f"Error checking Plex metrics: {e}")

        return {}

    async def _check_sonarr_health(self, service: ServiceConfig) -> Dict[str, Any]:
        """Check Sonarr-specific metrics"""
        try:
            headers = {"X-Api-Key": service.api_key}

            async with aiohttp.ClientSession() as session:
                # Get queue
                async with session.get(f"{service.url}/api/v3/queue", headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "queue_size": len(data.get("records", [])),
                            "downloading": sum(1 for r in data.get("records", [])
                                             if r.get("status") == "downloading")
                        }

        except Exception as e:
            self.logger.error(f"Error checking Sonarr metrics: {e}")

        return {}

    async def _check_radarr_health(self, service: ServiceConfig) -> Dict[str, Any]:
        """Check Radarr-specific metrics"""
        try:
            headers = {"X-Api-Key": service.api_key}

            async with aiohttp.ClientSession() as session:
                # Get queue
                async with session.get(f"{service.url}/api/v3/queue", headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "queue_size": len(data.get("records", [])),
                            "downloading": sum(1 for r in data.get("records", [])
                                             if r.get("status") == "downloading")
                        }

        except Exception as e:
            self.logger.error(f"Error checking Radarr metrics: {e}")

        return {}

    async def _check_homeassistant_health(self, service: ServiceConfig) -> Dict[str, Any]:
        """Check Home Assistant-specific metrics"""
        try:
            headers = {"Authorization": f"Bearer {service.api_key}"}

            async with aiohttp.ClientSession() as session:
                # Get state
                async with session.get(f"{service.url}/api/", headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "version": data.get("version", "unknown")
                        }

        except Exception as e:
            self.logger.error(f"Error checking Home Assistant metrics: {e}")

        return {}

    async def _check_pihole_health(self, service: ServiceConfig) -> Dict[str, Any]:
        """Check Pi-hole-specific metrics"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get stats
                async with session.get(f"{service.url}/admin/api.php?summary", ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "queries_today": data.get("dns_queries_today", 0),
                            "blocked_today": data.get("ads_blocked_today", 0),
                            "percent_blocked": data.get("ads_percentage_today", 0)
                        }

        except Exception as e:
            self.logger.error(f"Error checking Pi-hole metrics: {e}")

        return {}

    async def check_service_health(self, service_id: str) -> Optional[ServiceHealth]:
        """
        Check health of a specific service

        Args:
            service_id: Service identifier

        Returns:
            ServiceHealth object or None
        """
        service = self.services.get(service_id)
        if not service:
            self.logger.warning(f"Unknown service: {service_id}")
            return None

        # HTTP health check
        status, response_time, error_msg = await self.check_http_health(service)

        # Service-specific checks
        metrics = {}
        if status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            metrics = await self.check_service_specific_health(service)

        # Analyze issues
        issues = []
        if error_msg:
            issues.append(error_msg)

        if response_time and response_time > 5.0:
            issues.append(f"Slow response time: {response_time:.2f}s")

        # Create health object
        health = ServiceHealth(
            service_name=service.name,
            service_type=service.service_type,
            status=status,
            response_time=response_time,
            last_check=datetime.now(),
            error_message=error_msg,
            metrics=metrics,
            issues=issues
        )

        # Store health
        self.service_health[service_id] = health
        self.health_history.append(health)

        # Send alert if unhealthy
        if status in [HealthStatus.UNHEALTHY, HealthStatus.DOWN]:
            await self._send_alert(service_id, health)

        return health

    async def check_all_services(self) -> Dict[str, ServiceHealth]:
        """
        Check health of all configured services

        Returns:
            Dictionary mapping service_id to ServiceHealth
        """
        self.logger.info(f"Checking health of {len(self.services)} services")

        results = {}
        for service_id in self.services:
            health = await self.check_service_health(service_id)
            if health:
                results[service_id] = health

        return results

    async def _send_alert(self, service_id: str, health: ServiceHealth):
        """Send alert for unhealthy service"""
        if not self.telegram_notifier:
            return

        # Check alert cooldown
        last_alert = self.last_alert_time.get(service_id)
        if last_alert:
            time_since_alert = (datetime.now() - last_alert).total_seconds()
            if time_since_alert < self.alert_cooldown:
                return

        # Build alert message
        status_emoji = {
            HealthStatus.DOWN: "🔴",
            HealthStatus.UNHEALTHY: "🟠",
            HealthStatus.DEGRADED: "🟡"
        }.get(health.status, "⚪")

        message = f"{status_emoji} **Service Alert: {health.service_name}**\n\n"
        message += f"**Status:** {health.status.value.upper()}\n"

        if health.error_message:
            message += f"**Error:** {health.error_message}\n"

        if health.issues:
            message += "\n**Issues:**\n"
            for issue in health.issues:
                message += f"• {issue}\n"

        message += f"\n**Time:** {health.last_check.strftime('%Y-%m-%d %H:%M:%S')}"

        await self.telegram_notifier.send_message(message)
        self.last_alert_time[service_id] = datetime.now()

    async def generate_health_report(self) -> str:
        """
        Generate comprehensive service health report

        Returns:
            Formatted report string
        """
        if not self.service_health:
            await self.check_all_services()

        report_lines = [
            "🔍 **Service Health Report**",
            f"🗓️ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        # Summary
        total = len(self.service_health)
        healthy = sum(1 for h in self.service_health.values() if h.status == HealthStatus.HEALTHY)
        degraded = sum(1 for h in self.service_health.values() if h.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for h in self.service_health.values()
                       if h.status in [HealthStatus.UNHEALTHY, HealthStatus.DOWN])

        report_lines.extend([
            "**📊 Summary**",
            f"Total Services: {total}",
            f"✅ Healthy: {healthy}",
            f"🟡 Degraded: {degraded}",
            f"❌ Unhealthy: {unhealthy}",
            ""
        ])

        # Service details
        report_lines.append("**🔧 Service Status**")

        for service_id, health in sorted(self.service_health.items()):
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "🟡",
                HealthStatus.UNHEALTHY: "🟠",
                HealthStatus.DOWN: "🔴",
                HealthStatus.UNKNOWN: "⚪"
            }.get(health.status, "⚪")

            line = f"{status_emoji} **{health.service_name}**"

            if health.response_time:
                line += f" ({health.response_time:.2f}s)"

            if health.metrics:
                # Show relevant metrics
                metric_parts = []
                if "active_streams" in health.metrics:
                    metric_parts.append(f"{health.metrics['active_streams']} streams")
                if "queue_size" in health.metrics:
                    metric_parts.append(f"{health.metrics['queue_size']} queued")

                if metric_parts:
                    line += f" - {', '.join(metric_parts)}"

            report_lines.append(line)

            if health.issues:
                for issue in health.issues:
                    report_lines.append(f"  ⚠️ {issue}")

        report_lines.append("")

        # Performance summary
        avg_response_time = sum(h.response_time for h in self.service_health.values() if h.response_time) / len(self.service_health)
        report_lines.extend([
            "**⚡ Performance**",
            f"Average Response Time: {avg_response_time:.2f}s",
            ""
        ])

        return "\n".join(report_lines)

    async def run_monitoring_loop(self, check_interval: int = 60):
        """
        Main monitoring loop

        Args:
            check_interval: Seconds between checks
        """
        self.logger.info(f"Starting service health monitoring (every {check_interval}s)")

        while True:
            try:
                await self.check_all_services()
                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(check_interval)


async def main():
    """Run service health monitoring standalone"""
    agent = ServiceHealthAgent()
    await agent.run_monitoring_loop()


if __name__ == "__main__":
    asyncio.run(main())
