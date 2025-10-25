"""
Unifi Controller API Client

Integrates with Unifi Controller to fetch:
- Connected devices/clients
- Network statistics
- Bandwidth usage
- Device health
"""

import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import ssl

from shared.logging import get_logger

logger = get_logger(__name__)


class UnifiClient:
    """Client for Unifi Controller API"""

    def __init__(self, host: str, port: int = 443, username: str = "", password: str = "",
                 site: str = "default", verify_ssl: bool = False):
        """
        Initialize Unifi client

        Args:
            host: Controller hostname or IP
            port: Controller port (default 443)
            username: Admin username
            password: Admin password
            site: Site name (default "default")
            verify_ssl: Verify SSL certificate
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.site = site
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{host}:{port}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookies = {}
        self.logger = logger

    async def _ensure_session(self):
        """Create session if not exists"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=ssl.SSLContext() if not self.verify_ssl else None)
            self.session = aiohttp.ClientSession(
                connector=connector,
                cookie_jar=aiohttp.CookieJar()
            )

    async def login(self) -> bool:
        """
        Authenticate with Unifi Controller

        Returns:
            True if login successful
        """
        try:
            await self._ensure_session()

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
            self.logger.error(f"Error logging in to Unifi: {e}")
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
