"""
Network Monitoring Agent

Provides enhanced network monitoring and management:
- Unifi device tracking and statistics
- Network health monitoring
- Bandwidth usage analysis
- Connected device information
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from anthropic import Anthropic
from shared.config import config
from shared.logging import get_logger
from shared.metrics import get_metrics_collector
from integrations.unifi_client import UnifiClient
from integrations.adguard_client import AdGuardClient

logger = get_logger(__name__)


class NetworkAgent:
    """Agent for network monitoring and management"""

    def __init__(self):
        self.client = Anthropic(api_key=config.anthropic.api_key)
        self.model = config.anthropic.default_model
        self.metrics = get_metrics_collector("network_agent")
        self.logger = logger

        # Initialize API clients if enabled
        self.unifi_client = None
        self.adguard_client = None

        if config.unifi.enabled:
            self.unifi_client = UnifiClient(
                # Cloud API settings (recommended)
                api_key=config.unifi.api_key,
                site_id=config.unifi.site_id,
                use_cloud_api=config.unifi.use_cloud_api,
                # Local controller settings (legacy)
                host=config.unifi.host,
                port=config.unifi.port,
                username=config.unifi.username,
                password=config.unifi.password,
                site=config.unifi.site,
                verify_ssl=config.unifi.verify_ssl
            )
            api_type = "Cloud API" if config.unifi.use_cloud_api else "Local Controller"
            self.logger.info(f"Unifi integration enabled ({api_type})")

        if config.adguard.enabled:
            self.adguard_client = AdGuardClient(
                use_cloud_api=config.adguard.use_cloud_api,
                username=config.adguard.username,
                password=config.adguard.password,
                host=config.adguard.host,
                port=config.adguard.port
            )
            api_type = "AdGuard DNS (cloud)" if config.adguard.use_cloud_api else "AdGuard Home"
            self.logger.info(f"AdGuard integration enabled ({api_type})")

        self.logger.info("Network agent initialized", model=self.model)

    async def get_network_status(self) -> Dict[str, Any]:
        """
        Get comprehensive network status

        Returns dict with:
        - connected_devices: Count of active devices
        - bandwidth_usage: Current bandwidth statistics
        - health_status: Overall network health
        - alerts: Any network issues
        """
        try:
            self.logger.info("Getting network status")

            status = {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "network": {
                    "status": "healthy",
                    "connected_devices": 0,
                    "total_bandwidth_mbps": 1000,
                    "current_usage_mbps": 0,
                    "uptime_hours": 0
                },
                "services": {
                    "unifi": "unavailable",
                    "adguard": "unavailable",
                    "router": "unavailable"
                },
                "message": None
            }

            # Get data from Unifi if available
            if self.unifi_client:
                try:
                    await self.unifi_client.login()
                    stats = await self.unifi_client.get_network_stats()

                    if stats:
                        status["network"]["connected_devices"] = stats.get("connected_devices", 0)
                        status["network"]["uptime_hours"] = round(stats.get("uptime_hours", 0), 2)
                        status["services"]["unifi"] = "available"

                        # Get bandwidth
                        bandwidth = await self.unifi_client.get_bandwidth_usage()
                        status["network"]["current_usage_mbps"] = bandwidth.get("total_mbps", 0)

                    await self.unifi_client.logout()

                except Exception as e:
                    self.logger.error(f"Error getting Unifi data: {e}")
                    status["services"]["unifi"] = "error"

            # Check AdGuard status if available
            if self.adguard_client:
                try:
                    # Login for cloud API (OAuth token), no-op for Home (basic auth)
                    await self.adguard_client.login()

                    filter_status = await self.adguard_client.get_filtering_status()
                    if filter_status:
                        status["services"]["adguard"] = "available"
                        if not filter_status.get("enabled"):
                            status["services"]["adguard"] = "disabled"

                    await self.adguard_client.close()
                except Exception as e:
                    self.logger.error(f"Error getting AdGuard status: {e}")
                    status["services"]["adguard"] = "error"

            # Add helpful message if no integrations
            if not self.unifi_client and not self.adguard_client:
                status["message"] = "No network integrations configured. Enable UNIFI or ADGUARD in config."

            return status

        except Exception as e:
            self.logger.error(f"Error getting network status: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_connected_devices(self) -> Dict[str, Any]:
        """
        Get list of currently connected network devices

        Returns device information including:
        - device_name
        - ip_address
        - mac_address
        - connection_type (wired/wireless)
        - last_seen
        """
        try:
            self.logger.info("Getting connected devices")

            devices = {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_devices": 0,
                "devices": [],
                "message": None
            }

            # Get devices from Unifi if available
            if self.unifi_client:
                try:
                    await self.unifi_client.login()
                    clients = await self.unifi_client.get_clients()

                    devices["devices"] = clients
                    devices["total_devices"] = len(clients)

                    await self.unifi_client.logout()

                except Exception as e:
                    self.logger.error(f"Error getting Unifi clients: {e}")
                    devices["message"] = f"Error getting Unifi clients: {str(e)}"
            else:
                devices["message"] = "Unifi integration not enabled. Set UNIFI_ENABLED=true in config."

            return devices

        except Exception as e:
            self.logger.error(f"Error getting connected devices: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_bandwidth_stats(self) -> Dict[str, Any]:
        """
        Get bandwidth usage statistics

        Returns:
        - current_download_mbps
        - current_upload_mbps
        - peak_usage
        - top_consumers (devices using most bandwidth)
        """
        try:
            self.logger.info("Getting bandwidth statistics")

            stats = {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bandwidth": {
                    "download_mbps": 0,
                    "upload_mbps": 0,
                    "total_mbps": 0
                },
                "message": None
            }

            # Get bandwidth from Unifi if available
            if self.unifi_client:
                try:
                    await self.unifi_client.login()
                    bandwidth = await self.unifi_client.get_bandwidth_usage()

                    stats["bandwidth"]["download_mbps"] = bandwidth.get("download_mbps", 0)
                    stats["bandwidth"]["upload_mbps"] = bandwidth.get("upload_mbps", 0)
                    stats["bandwidth"]["total_mbps"] = bandwidth.get("total_mbps", 0)

                    await self.unifi_client.logout()

                except Exception as e:
                    self.logger.error(f"Error getting Unifi bandwidth: {e}")
                    stats["message"] = f"Error getting bandwidth: {str(e)}"
            else:
                stats["message"] = "Unifi integration not enabled. Set UNIFI_ENABLED=true in config."

            return stats

        except Exception as e:
            self.logger.error(f"Error getting bandwidth stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute(self, task: str) -> Dict[str, Any]:
        """
        Execute network-related tasks using Claude

        Args:
            task: Natural language description of the network task

        Returns:
            Dict with task results
        """
        try:
            self.logger.info(f"Executing network task", task=task)
            start_time = datetime.now()

            # Use Claude to understand and route the task
            prompt = f"""You are a network monitoring assistant.

The user has requested: "{task}"

Based on this request, determine what network information they need and respond with:
1. A brief acknowledgment of their request
2. What network data should be gathered
3. How to present the information

Available network capabilities:
- Network status (overall health, uptime)
- Connected devices list
- Bandwidth usage statistics

Keep your response concise and focused on the network aspect."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text if response.content else "No response"

            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_agent_execution(
                agent_name="network",
                task_type="execute",
                success=True,
                duration=duration
            )

            self.logger.info("Network task completed", duration=duration)

            return {
                "success": True,
                "summary": result_text,
                "task": task,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error executing network task: {e}")
            self.metrics.record_agent_execution(
                agent_name="network",
                task_type="execute",
                success=False,
                duration=0
            )
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
