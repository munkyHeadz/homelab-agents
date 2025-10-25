"""
AdGuard Home API Client

Integrates with AdGuard Home to fetch:
- DNS query statistics
- Blocked queries
- Top domains/clients
- Filtering status
"""

import aiohttp
from typing import Dict, Any, List
from datetime import datetime, timezone

from shared.logging import get_logger

logger = get_logger(__name__)


class AdGuardClient:
    """Client for AdGuard Home API"""

    def __init__(self, host: str, port: int = 80, username: str = "", password: str = ""):
        """
        Initialize AdGuard client

        Args:
            host: AdGuard hostname or IP
            port: AdGuard port (default 80)
            username: Admin username
            password: Admin password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{host}:{port}"
        self.session: aiohttp.ClientSession = None
        self.logger = logger

    async def _ensure_session(self):
        """Create session if not exists"""
        if self.session is None or self.session.closed:
            auth = aiohttp.BasicAuth(self.username, self.password) if self.username else None
            self.session = aiohttp.ClientSession(auth=auth)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get DNS query statistics

        Returns:
            Statistics including total queries, blocked, etc.
        """
        try:
            await self._ensure_session()

            async with self.session.get(f"{self.base_url}/control/stats") as response:
                if response.status == 200:
                    data = await response.json()

                    stats = {
                        "total_queries": data.get("num_dns_queries", 0),
                        "blocked_queries": data.get("num_blocked_filtering", 0),
                        "blocked_percentage": 0,
                        "avg_processing_time_ms": data.get("avg_processing_time", 0),
                        "queries_today": 0,
                        "blocked_today": 0
                    }

                    # Calculate percentage
                    if stats["total_queries"] > 0:
                        stats["blocked_percentage"] = round(
                            (stats["blocked_queries"] / stats["total_queries"]) * 100,
                            2
                        )

                    self.logger.info("Retrieved AdGuard statistics")
                    return stats

                else:
                    self.logger.error(f"Failed to get AdGuard stats: {response.status}")
                    return {}

        except Exception as e:
            self.logger.error(f"Error getting AdGuard stats: {e}")
            return {}

    async def get_top_blocked_domains(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top blocked domains

        Args:
            limit: Number of domains to return

        Returns:
            List of blocked domains with counts
        """
        try:
            await self._ensure_session()

            async with self.session.get(f"{self.base_url}/control/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    blocked_domains = data.get("top_blocked_domains", [])

                    # Format as list of dicts
                    results = []
                    for i, (domain, count) in enumerate(blocked_domains[:limit]):
                        results.append({
                            "rank": i + 1,
                            "domain": domain,
                            "count": count
                        })

                    return results
                else:
                    return []

        except Exception as e:
            self.logger.error(f"Error getting top blocked domains: {e}")
            return []

    async def get_top_clients(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top DNS clients by query count

        Args:
            limit: Number of clients to return

        Returns:
            List of clients with query counts
        """
        try:
            await self._ensure_session()

            async with self.session.get(f"{self.base_url}/control/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    top_clients = data.get("top_queried_domains", [])

                    results = []
                    for i, (client, count) in enumerate(top_clients[:limit]):
                        results.append({
                            "rank": i + 1,
                            "client": client,
                            "queries": count
                        })

                    return results
                else:
                    return []

        except Exception as e:
            self.logger.error(f"Error getting top clients: {e}")
            return []

    async def get_filtering_status(self) -> Dict[str, Any]:
        """
        Get current filtering status

        Returns:
            Status information about filters
        """
        try:
            await self._ensure_session()

            async with self.session.get(f"{self.base_url}/control/status") as response:
                if response.status == 200:
                    data = await response.json()

                    status = {
                        "enabled": data.get("protection_enabled", False),
                        "filters_enabled": data.get("filters", {}).get("enabled", False),
                        "safebrowsing_enabled": data.get("safebrowsing_enabled", False),
                        "parental_enabled": data.get("parental_enabled", False),
                        "safesearch_enabled": data.get("safesearch_enabled", False),
                        "version": data.get("version", "unknown")
                    }

                    return status
                else:
                    return {}

        except Exception as e:
            self.logger.error(f"Error getting filtering status: {e}")
            return {}

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
