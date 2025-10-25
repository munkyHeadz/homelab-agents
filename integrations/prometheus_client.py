"""
Prometheus Client

Provides integration with Prometheus for metrics queries and monitoring:
- Query current system metrics
- Retrieve alert status
- Get time-series data
- Health checks
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import aiohttp
from urllib.parse import urlencode

from shared.logging import get_logger

logger = get_logger(__name__)


class PrometheusClient:
    """Client for Prometheus API operations"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        url: Optional[str] = None
    ):
        """
        Initialize Prometheus client

        Args:
            host: Prometheus hostname/IP
            port: Prometheus port (default: 9090)
            url: Full Prometheus URL (overrides host/port)
        """
        if url:
            self.base_url = url.rstrip('/')
        else:
            host = host or os.getenv("PROMETHEUS_HOST", "localhost")
            port = port or int(os.getenv("PROMETHEUS_PORT", "9090"))
            self.base_url = f"http://{host}:{port}"

        self.logger = logger
        self.session = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def query(self, query: str) -> Dict[str, Any]:
        """
        Execute instant Prometheus query

        Args:
            query: PromQL query string

        Returns:
            Dict with query results
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}/api/v1/query"
            params = {"query": query}

            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "success":
                        return {
                            "success": True,
                            "data": data.get("data", {}),
                            "result_type": data.get("data", {}).get("resultType"),
                            "result": data.get("data", {}).get("result", [])
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error", "Unknown error")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {await response.text()}"
                    }

        except aiohttp.ClientError as e:
            self.logger.error(f"Error querying Prometheus: {e}")
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Unexpected error querying Prometheus: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "15s"
    ) -> Dict[str, Any]:
        """
        Execute range Prometheus query

        Args:
            query: PromQL query string
            start: Start time
            end: End time
            step: Query resolution step

        Returns:
            Dict with query results
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}/api/v1/query_range"
            params = {
                "query": query,
                "start": int(start.timestamp()),
                "end": int(end.timestamp()),
                "step": step
            }

            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "success":
                        return {
                            "success": True,
                            "data": data.get("data", {}),
                            "result_type": data.get("data", {}).get("resultType"),
                            "result": data.get("data", {}).get("result", [])
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error", "Unknown error")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"Error querying Prometheus range: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics

        Returns:
            Dict with CPU, memory, disk metrics
        """
        metrics = {}

        try:
            # CPU usage
            cpu_query = '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
            cpu_result = await self.query(cpu_query)

            if cpu_result.get("success"):
                results = cpu_result.get("result", [])
                if results:
                    metrics["cpu"] = []
                    for result in results:
                        instance = result.get("metric", {}).get("instance", "unknown")
                        value = float(result.get("value", [0, "0"])[1])
                        metrics["cpu"].append({
                            "instance": instance,
                            "usage_percent": round(value, 2)
                        })

            # Memory usage
            mem_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
            mem_result = await self.query(mem_query)

            if mem_result.get("success"):
                results = mem_result.get("result", [])
                if results:
                    metrics["memory"] = []
                    for result in results:
                        instance = result.get("metric", {}).get("instance", "unknown")
                        value = float(result.get("value", [0, "0"])[1])
                        metrics["memory"].append({
                            "instance": instance,
                            "usage_percent": round(value, 2)
                        })

            # Disk usage
            disk_query = '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100'
            disk_result = await self.query(disk_query)

            if disk_result.get("success"):
                results = disk_result.get("result", [])
                if results:
                    metrics["disk"] = []
                    for result in results:
                        instance = result.get("metric", {}).get("instance", "unknown")
                        value = float(result.get("value", [0, "0"])[1])
                        metrics["disk"].append({
                            "instance": instance,
                            "usage_percent": round(value, 2)
                        })

            return {
                "success": True,
                "metrics": metrics
            }

        except Exception as e:
            self.logger.error(f"Error getting current metrics: {e}")
            return {
                "success": False,
                "error": str(e),
                "metrics": {}
            }

    async def get_targets(self) -> Dict[str, Any]:
        """
        Get Prometheus scrape targets

        Returns:
            Dict with active/inactive targets
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}/api/v1/targets"

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "success":
                        targets_data = data.get("data", {})
                        active_targets = targets_data.get("activeTargets", [])
                        dropped_targets = targets_data.get("droppedTargets", [])

                        return {
                            "success": True,
                            "active_count": len(active_targets),
                            "dropped_count": len(dropped_targets),
                            "active_targets": active_targets,
                            "dropped_targets": dropped_targets
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error", "Unknown error")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"Error getting targets: {e}")
            return {
                "success": False,
                "error": str(e),
                "active_count": 0,
                "dropped_count": 0
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Prometheus health

        Returns:
            Dict with health status
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}/-/healthy"

            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "healthy": True,
                        "url": self.base_url
                    }
                else:
                    return {
                        "success": False,
                        "healthy": False,
                        "error": f"HTTP {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"Error checking Prometheus health: {e}")
            return {
                "success": False,
                "healthy": False,
                "error": str(e)
            }

    async def get_alerts(self) -> Dict[str, Any]:
        """
        Get current alerts from Prometheus

        Returns:
            Dict with active alerts
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}/api/v1/alerts"

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "success":
                        alerts = data.get("data", {}).get("alerts", [])

                        # Group by state
                        by_state = {
                            "firing": [],
                            "pending": [],
                            "inactive": []
                        }

                        for alert in alerts:
                            state = alert.get("state", "inactive")
                            by_state[state].append(alert)

                        return {
                            "success": True,
                            "total": len(alerts),
                            "firing_count": len(by_state["firing"]),
                            "pending_count": len(by_state["pending"]),
                            "alerts": alerts,
                            "by_state": by_state
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error", "Unknown error")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"Error getting alerts: {e}")
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "firing_count": 0,
                "pending_count": 0
            }


# Global instance
_prometheus_client = None


def get_prometheus_client() -> Optional[PrometheusClient]:
    """Get or create the global Prometheus client instance"""
    global _prometheus_client

    # Check if Prometheus is configured
    prom_url = os.getenv("PROMETHEUS_URL", "")
    prom_host = os.getenv("PROMETHEUS_HOST", "")

    if not prom_url and not prom_host:
        logger.warning("Prometheus integration disabled (PROMETHEUS_HOST not configured)")
        return None

    if _prometheus_client is None:
        try:
            _prometheus_client = PrometheusClient(url=prom_url if prom_url else None)
            logger.info("Prometheus client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus client: {e}")
            return None

    return _prometheus_client
