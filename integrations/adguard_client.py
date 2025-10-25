"""
AdGuard API Client

Integrates with AdGuard services to fetch:
- DNS query statistics
- Blocked queries
- Top domains/clients
- Filtering status

Supports both:
- AdGuard Home (self-hosted)
- AdGuard DNS (cloud service)

Documentation:
- AdGuard Home: https://github.com/AdguardTeam/AdGuardHome/wiki/API
- AdGuard DNS: https://adguard-dns.io/kb/private-dns/api/overview/
"""

import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from shared.logging import get_logger

logger = get_logger(__name__)


class AdGuardClient:
    """Client for AdGuard Home and AdGuard DNS APIs"""

    def __init__(self,
                 use_cloud_api: bool = False,
                 # Cloud DNS settings
                 username: str = "",
                 password: str = "",
                 # AdGuard Home settings
                 host: str = "adguard.local",
                 port: int = 80):
        """
        Initialize AdGuard client

        Supports both AdGuard DNS (cloud) and AdGuard Home (self-hosted)

        AdGuard DNS (cloud):
            use_cloud_api: Set to True
            username: Your AdGuard account username/email
            password: Your AdGuard account password

        AdGuard Home (self-hosted):
            use_cloud_api: Set to False (default)
            host: AdGuard Home hostname or IP
            port: AdGuard Home port (default 80)
            username: Admin username
            password: Admin password
        """
        self.use_cloud_api = use_cloud_api
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        if self.use_cloud_api:
            self.base_url = "https://api.adguard-dns.io"
            self.access_token: Optional[str] = None
            self.refresh_token: Optional[str] = None
            self.token_expires_at: Optional[datetime] = None
        else:
            self.base_url = f"http://{host}:{port}"

        self.session: aiohttp.ClientSession = None
        self.logger = logger

    async def _get_oauth_token(self) -> bool:
        """Get OAuth access token for AdGuard DNS cloud API"""
        try:
            if not self.username or not self.password:
                self.logger.error("Username and password required for AdGuard DNS")
                return False

            # Create temporary session for token request
            async with aiohttp.ClientSession() as temp_session:
                token_url = f"{self.base_url}/oapi/v1/oauth_token"
                data = {
                    "username": self.username,
                    "password": self.password
                }

                async with temp_session.post(token_url, json=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.access_token = token_data.get("access_token")
                        self.refresh_token = token_data.get("refresh_token")

                        # Calculate expiry time
                        expires_in = token_data.get("expires_in", 3600)
                        self.token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in

                        self.logger.info("Successfully obtained AdGuard DNS access token")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to get OAuth token: {response.status} - {error_text}")
                        return False

        except Exception as e:
            self.logger.error(f"Error getting OAuth token: {e}")
            return False

    async def _ensure_session(self):
        """Create session if not exists"""
        if self.session is None or self.session.closed:
            if self.use_cloud_api:
                # Cloud API uses Bearer token
                headers = {}
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"

                self.session = aiohttp.ClientSession(headers=headers)
            else:
                # AdGuard Home uses basic auth
                auth = aiohttp.BasicAuth(self.username, self.password) if self.username else None
                self.session = aiohttp.ClientSession(auth=auth)

    async def login(self) -> bool:
        """
        Authenticate with AdGuard

        For AdGuard DNS (cloud): Get OAuth token
        For AdGuard Home: Basic auth is used automatically

        Returns:
            True if authentication successful
        """
        if self.use_cloud_api:
            # Get OAuth token for cloud API
            if not await self._get_oauth_token():
                return False

        await self._ensure_session()
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get DNS query statistics

        Returns:
            Statistics including total queries, blocked, etc.
        """
        try:
            await self._ensure_session()

            if self.use_cloud_api:
                # AdGuard DNS cloud API
                endpoint = "/oapi/v1/stats/time"
                params = {
                    "start_time": int((datetime.now(timezone.utc).timestamp() - 86400) * 1000),  # Last 24h
                    "end_time": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "step": 3600000  # 1 hour intervals
                }

                async with self.session.get(f"{self.base_url}{endpoint}", params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Sum up queries and blocked from time series
                        total_queries = 0
                        blocked_queries = 0

                        for point in data.get("time_series", []):
                            total_queries += point.get("queries", 0)
                            blocked_queries += point.get("blocked", 0)

                        stats = {
                            "total_queries": total_queries,
                            "blocked_queries": blocked_queries,
                            "blocked_percentage": 0,
                            "avg_processing_time_ms": 0,  # Not available in cloud API
                            "queries_today": total_queries,
                            "blocked_today": blocked_queries
                        }

                        # Calculate percentage
                        if stats["total_queries"] > 0:
                            stats["blocked_percentage"] = round(
                                (stats["blocked_queries"] / stats["total_queries"]) * 100,
                                2
                            )

                        self.logger.info("Retrieved AdGuard DNS statistics")
                        return stats
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to get AdGuard DNS stats: {response.status} - {error_text}")
                        return {}

            else:
                # AdGuard Home API
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

                        self.logger.info("Retrieved AdGuard Home statistics")
                        return stats

                    else:
                        self.logger.error(f"Failed to get AdGuard Home stats: {response.status}")
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

            if self.use_cloud_api:
                # AdGuard DNS cloud API
                endpoint = "/oapi/v1/stats/domains"
                params = {
                    "start_time": int((datetime.now(timezone.utc).timestamp() - 86400) * 1000),  # Last 24h
                    "end_time": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "limit": limit,
                    "order_by": "queries"  # Order by query count
                }

                async with self.session.get(f"{self.base_url}{endpoint}", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        domains = data.get("top_blocked_domains", data.get("domains", []))

                        # Format as list of dicts
                        results = []
                        for i, domain_data in enumerate(domains[:limit]):
                            if isinstance(domain_data, dict):
                                results.append({
                                    "rank": i + 1,
                                    "domain": domain_data.get("domain", "unknown"),
                                    "count": domain_data.get("blocked", domain_data.get("queries", 0))
                                })
                            elif isinstance(domain_data, (list, tuple)) and len(domain_data) >= 2:
                                results.append({
                                    "rank": i + 1,
                                    "domain": domain_data[0],
                                    "count": domain_data[1]
                                })

                        return results
                    else:
                        return []

            else:
                # AdGuard Home API
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
