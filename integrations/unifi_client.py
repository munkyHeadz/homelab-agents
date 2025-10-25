"""
Unifi Site Manager API Client

Integrates with Unifi Site Manager API (cloud-based) to fetch:
- Connected devices/clients
- Network statistics
- Bandwidth usage
- Device health

Documentation: https://developer.ui.com/site-manager-api
"""

import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import ssl

from shared.logging import get_logger

logger = get_logger(__name__)


class UnifiClient:
    """Client for Unifi Site Manager API (cloud-based with API key)"""

    def __init__(self, api_key: str = "", site_id: str = "",
                 use_cloud_api: bool = True,
                 host: str = "", port: int = 443,
                 username: str = "", password: str = "",
                 site: str = "default", verify_ssl: bool = False):
        """
        Initialize Unifi client

        Supports both Cloud API (recommended) and Local Controller API

        Cloud API (recommended):
            api_key: Your Unifi API key from console.ui.com
            site_id: Your site ID (found in console URL)
            use_cloud_api: Set to True (default)

        Local Controller API (legacy):
            host: Controller hostname or IP
            port: Controller port (default 443)
            username: Admin username
            password: Admin password
            site: Site name (default "default")
            use_cloud_api: Set to False
        """
        self.use_cloud_api = use_cloud_api
        self.api_key = api_key
        self.site_id = site_id

        # Local controller settings (legacy)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.site = site
        self.verify_ssl = verify_ssl

        if self.use_cloud_api:
            self.base_url = "https://api.ui.com/ea"
        else:
            self.base_url = f"https://{host}:{port}"

        self.session: Optional[aiohttp.ClientSession] = None
        self.cookies = {}
        self.logger = logger

    async def _ensure_session(self):
        """Create session if not exists"""
        if self.session is None or self.session.closed:
            headers = {}

            if self.use_cloud_api and self.api_key:
                # Cloud API uses X-API-Key header authentication
                headers["X-API-Key"] = self.api_key
                headers["Content-Type"] = "application/json"

            connector = aiohttp.TCPConnector(ssl=ssl.SSLContext() if not self.verify_ssl else None)
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=headers,
                cookie_jar=aiohttp.CookieJar() if not self.use_cloud_api else None
            )

    async def login(self) -> bool:
        """
        Authenticate with Unifi

        For Cloud API: No login needed, uses API key
        For Local Controller: Login with username/password

        Returns:
            True if authentication successful
        """
        try:
            await self._ensure_session()

            # Cloud API doesn't need explicit login, just API key in headers
            if self.use_cloud_api:
                if not self.api_key:
                    self.logger.error("No API key provided for Unifi Cloud API")
                    return False
                self.logger.info("Using Unifi Cloud API with API key")
                return True

            # Local controller login
            login_data = {
                "username": self.username,
                "password": self.password,
                "remember": False
            }

            async with self.session.post(
                f"{self.base_url}/api/login",
                json=login_data,
                ssl=False if not self.verify_ssl else None
            ) as response:
                if response.status == 200:
                    self.logger.info("Successfully logged in to Unifi Controller")
                    return True
                else:
                    self.logger.error(f"Failed to login to Unifi: {response.status}")
                    return False

        except Exception as e:
            self.logger.error(f"Error authenticating with Unifi: {e}")
            return False

    async def get_clients(self) -> List[Dict[str, Any]]:
        """
        Get all connected clients

        Returns:
            List of client dictionaries with device info
        """
        try:
            await self._ensure_session()

            async with self.session.get(
                f"{self.base_url}/api/s/{self.site}/stat/sta",
                ssl=False if not self.verify_ssl else None
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    clients = data.get("data", [])

                    self.logger.info(f"Retrieved {len(clients)} connected clients")

                    # Format client data
                    formatted_clients = []
                    for client in clients:
                        formatted_clients.append({
                            "name": client.get("hostname", client.get("name", "Unknown")),
                            "ip_address": client.get("ip", "N/A"),
                            "mac_address": client.get("mac", "N/A"),
                            "connection_type": "wireless" if client.get("is_wired") == False else "wired",
                            "last_seen": datetime.fromtimestamp(
                                client.get("last_seen", 0),
                                tz=timezone.utc
                            ).isoformat(),
                            "rx_bytes": client.get("rx_bytes", 0),
                            "tx_bytes": client.get("tx_bytes", 0),
                            "signal": client.get("signal", 0),
                            "uptime": client.get("uptime", 0)
                        })

                    return formatted_clients
                else:
                    self.logger.error(f"Failed to get clients: {response.status}")
                    return []

        except Exception as e:
            self.logger.error(f"Error getting Unifi clients: {e}")
            return []

    async def get_network_stats(self) -> Dict[str, Any]:
        """
        Get network statistics

        Returns:
            Network stats including bandwidth, uptime, etc.
        """
        try:
            await self._ensure_session()

            async with self.session.get(
                f"{self.base_url}/api/s/{self.site}/stat/health",
                ssl=False if not self.verify_ssl else None
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    health_data = data.get("data", [])

                    stats = {
                        "status": "healthy",
                        "connected_devices": 0,
                        "uptime_hours": 0,
                        "wan": {},
                        "lan": {}
                    }

                    for item in health_data:
                        subsystem = item.get("subsystem", "")

                        if subsystem == "wan":
                            stats["wan"] = {
                                "status": item.get("status", "unknown"),
                                "uptime": item.get("uptime", 0),
                                "rx_bytes": item.get("rx_bytes-r", 0),
                                "tx_bytes": item.get("tx_bytes-r", 0)
                            }
                            stats["uptime_hours"] = item.get("uptime", 0) / 3600

                        elif subsystem == "lan":
                            stats["lan"] = {
                                "num_user": item.get("num_user", 0),
                                "num_guest": item.get("num_guest", 0)
                            }
                            stats["connected_devices"] = item.get("num_user", 0) + item.get("num_guest", 0)

                    self.logger.info("Retrieved network stats from Unifi")
                    return stats

                else:
                    self.logger.error(f"Failed to get network stats: {response.status}")
                    return {}

        except Exception as e:
            self.logger.error(f"Error getting network stats: {e}")
            return {}

    async def get_bandwidth_usage(self) -> Dict[str, Any]:
        """
        Get current bandwidth usage

        Returns:
            Bandwidth statistics in Mbps
        """
        try:
            stats = await self.get_network_stats()

            wan = stats.get("wan", {})
            rx_bytes_per_sec = wan.get("rx_bytes", 0)
            tx_bytes_per_sec = wan.get("tx_bytes", 0)

            # Convert bytes/sec to Mbps
            download_mbps = (rx_bytes_per_sec * 8) / 1_000_000
            upload_mbps = (tx_bytes_per_sec * 8) / 1_000_000

            return {
                "download_mbps": round(download_mbps, 2),
                "upload_mbps": round(upload_mbps, 2),
                "total_mbps": round(download_mbps + upload_mbps, 2)
            }

        except Exception as e:
            self.logger.error(f"Error calculating bandwidth: {e}")
            return {
                "download_mbps": 0,
                "upload_mbps": 0,
                "total_mbps": 0
            }

    async def logout(self):
        """Logout from Unifi Controller"""
        try:
            if self.session and not self.session.closed:
                await self.session.post(
                    f"{self.base_url}/api/logout",
                    ssl=False if not self.verify_ssl else None
                )
                await self.session.close()
                self.logger.info("Logged out from Unifi Controller")
        except Exception as e:
            self.logger.error(f"Error logging out: {e}")

    async def __aenter__(self):
        """Context manager entry"""
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.logout()
