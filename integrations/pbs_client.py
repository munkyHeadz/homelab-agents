"""
Proxmox Backup Server (PBS) Client

Provides integration with Proxmox Backup Server for:
- Listing backups and snapshots
- Viewing backup status and statistics
- Monitoring datastore capacity
- Backup verification
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException

from shared.logging import get_logger

logger = get_logger(__name__)


class PBSClient:
    """Client for Proxmox Backup Server operations"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
        datastore: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize PBS client

        Args:
            host: PBS server hostname/IP
            port: PBS API port (default: 8007)
            user: PBS user (e.g., root@pam)
            password: User password
            token_id: API token ID (e.g., root@pam!backup-token)
            token_secret: API token secret
            datastore: Default datastore name
            verify_ssl: Verify SSL certificates
        """
        self.host = host or os.getenv("PBS_HOST", "")
        self.port = port or int(os.getenv("PBS_PORT", "8007"))
        self.user = user or os.getenv("PBS_USER", "root@pam")
        self.password = password or os.getenv("PBS_PASSWORD", "")
        self.token_id = token_id or os.getenv("PBS_TOKEN_ID", "")
        self.token_secret = token_secret or os.getenv("PBS_TOKEN_SECRET", "")
        self.datastore = datastore or os.getenv("PBS_DATASTORE", "backups")
        self.verify_ssl = verify_ssl

        self.logger = logger
        self.pbs = None
        self._connect()

    def _connect(self):
        """Establish connection to PBS"""
        try:
            if self.token_id and self.token_secret:
                # Use API token (recommended)
                user_part, token_name = self.token_id.rsplit("!", 1)
                self.pbs = ProxmoxAPI(
                    self.host,
                    user=user_part,
                    token_name=token_name,
                    token_value=self.token_secret,
                    verify_ssl=self.verify_ssl,
                    port=self.port,
                    service="PBS"
                )
            else:
                # Fall back to password authentication
                self.pbs = ProxmoxAPI(
                    self.host,
                    user=self.user,
                    password=self.password,
                    verify_ssl=self.verify_ssl,
                    port=self.port,
                    service="PBS"
                )

            self.logger.info(f"Connected to PBS at {self.host}:{self.port}")

        except Exception as e:
            self.logger.error(f"Failed to connect to PBS: {e}")
            raise

    async def get_datastore_status(self, datastore: Optional[str] = None) -> Dict[str, Any]:
        """
        Get datastore status and statistics

        Args:
            datastore: Datastore name (uses default if not specified)

        Returns:
            Dict with datastore statistics
        """
        ds_name = datastore or self.datastore

        try:
            # Get datastore status
            status = self.pbs.admin.datastore(ds_name).status.get()

            return {
                "success": True,
                "datastore": ds_name,
                "total": status.get("total", 0),
                "used": status.get("used", 0),
                "available": status.get("avail", 0),
                "usage_percent": round((status.get("used", 0) / status.get("total", 1)) * 100, 2),
                "gc_status": status.get("gc-status", {}),
                "count": status.get("counts", {})
            }

        except ResourceException as e:
            self.logger.error(f"Error getting datastore status: {e}")
            return {
                "success": False,
                "error": str(e),
                "datastore": ds_name
            }
        except Exception as e:
            self.logger.error(f"Unexpected error getting datastore status: {e}")
            return {
                "success": False,
                "error": str(e),
                "datastore": ds_name
            }

    async def list_backups(
        self,
        datastore: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        List all backup snapshots

        Args:
            datastore: Datastore name
            limit: Maximum number of snapshots to return

        Returns:
            Dict with list of backups
        """
        ds_name = datastore or self.datastore

        try:
            # Get all backup groups
            groups = self.pbs.admin.datastore(ds_name).groups.get()

            backups = []
            for group in groups[:limit]:
                backup_type = group.get("backup-type", "unknown")
                backup_id = group.get("backup-id", "unknown")

                # Get snapshots for this backup group
                try:
                    snapshots = self.pbs.admin.datastore(ds_name).snapshots.get(
                        **{"backup-type": backup_type, "backup-id": backup_id}
                    )

                    for snapshot in snapshots:
                        backups.append({
                            "type": backup_type,
                            "id": backup_id,
                            "time": snapshot.get("backup-time", 0),
                            "size": snapshot.get("size", 0),
                            "protected": snapshot.get("protected", False),
                            "verification": snapshot.get("verification", {}),
                            "comment": snapshot.get("comment", "")
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to get snapshots for {backup_type}/{backup_id}: {e}")
                    continue

            # Sort by backup time (newest first)
            backups.sort(key=lambda x: x["time"], reverse=True)

            return {
                "success": True,
                "datastore": ds_name,
                "total": len(backups),
                "backups": backups[:limit]
            }

        except ResourceException as e:
            self.logger.error(f"Error listing backups: {e}")
            return {
                "success": False,
                "error": str(e),
                "datastore": ds_name,
                "backups": []
            }
        except Exception as e:
            self.logger.error(f"Unexpected error listing backups: {e}")
            return {
                "success": False,
                "error": str(e),
                "datastore": ds_name,
                "backups": []
            }

    async def get_backup_summary(self, datastore: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of backups

        Args:
            datastore: Datastore name

        Returns:
            Dict with backup summary statistics
        """
        ds_name = datastore or self.datastore

        try:
            backups_result = await self.list_backups(datastore=ds_name, limit=1000)

            if not backups_result.get("success"):
                return backups_result

            backups = backups_result.get("backups", [])

            # Calculate summary statistics
            total_size = sum(b.get("size", 0) for b in backups)
            protected_count = sum(1 for b in backups if b.get("protected", False))

            # Get latest backup time
            latest_backup = backups[0] if backups else None
            latest_time = None
            if latest_backup:
                latest_time = datetime.fromtimestamp(
                    latest_backup["time"],
                    tz=timezone.utc
                )

            # Group by backup type
            by_type = {}
            for backup in backups:
                backup_type = backup.get("type", "unknown")
                if backup_type not in by_type:
                    by_type[backup_type] = {
                        "count": 0,
                        "size": 0,
                        "ids": set()
                    }

                by_type[backup_type]["count"] += 1
                by_type[backup_type]["size"] += backup.get("size", 0)
                by_type[backup_type]["ids"].add(backup.get("id", "unknown"))

            # Convert sets to counts
            for backup_type in by_type:
                by_type[backup_type]["unique_ids"] = len(by_type[backup_type]["ids"])
                del by_type[backup_type]["ids"]

            return {
                "success": True,
                "datastore": ds_name,
                "total_backups": len(backups),
                "total_size": total_size,
                "total_size_gb": round(total_size / (1024**3), 2),
                "protected_count": protected_count,
                "latest_backup_time": latest_time.isoformat() if latest_time else None,
                "by_type": by_type
            }

        except Exception as e:
            self.logger.error(f"Error getting backup summary: {e}")
            return {
                "success": False,
                "error": str(e),
                "datastore": ds_name
            }

    async def get_recent_backups(
        self,
        datastore: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get most recent backups

        Args:
            datastore: Datastore name
            limit: Number of recent backups to return

        Returns:
            Dict with recent backups
        """
        ds_name = datastore or self.datastore

        try:
            result = await self.list_backups(datastore=ds_name, limit=limit)

            if not result.get("success"):
                return result

            backups = result.get("backups", [])[:limit]

            # Format for display
            formatted_backups = []
            for backup in backups:
                backup_time = datetime.fromtimestamp(
                    backup["time"],
                    tz=timezone.utc
                )

                formatted_backups.append({
                    "type": backup["type"],
                    "id": backup["id"],
                    "time": backup_time.isoformat(),
                    "time_ago": self._format_time_ago(backup_time),
                    "size_gb": round(backup["size"] / (1024**3), 2),
                    "protected": backup["protected"],
                    "verified": bool(backup.get("verification", {}).get("state") == "ok")
                })

            return {
                "success": True,
                "datastore": ds_name,
                "backups": formatted_backups
            }

        except Exception as e:
            self.logger.error(f"Error getting recent backups: {e}")
            return {
                "success": False,
                "error": str(e),
                "datastore": ds_name,
                "backups": []
            }

    def _format_time_ago(self, backup_time: datetime) -> str:
        """Format time difference in human-readable format"""
        now = datetime.now(timezone.utc)
        diff = now - backup_time

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"

    async def verify_backup(
        self,
        datastore: Optional[str] = None,
        backup_type: str = "vm",
        backup_id: str = "",
        backup_time: int = 0
    ) -> Dict[str, Any]:
        """
        Verify a backup snapshot

        Args:
            datastore: Datastore name
            backup_type: Backup type (vm, host, ct)
            backup_id: Backup ID
            backup_time: Backup timestamp

        Returns:
            Dict with verification result
        """
        ds_name = datastore or self.datastore

        try:
            result = self.pbs.admin.datastore(ds_name).verify.post(
                **{
                    "backup-type": backup_type,
                    "backup-id": backup_id,
                    "backup-time": backup_time
                }
            )

            return {
                "success": True,
                "datastore": ds_name,
                "upid": result
            }

        except ResourceException as e:
            self.logger.error(f"Error verifying backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error verifying backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
_pbs_client = None


def get_pbs_client() -> Optional[PBSClient]:
    """Get or create the global PBS client instance"""
    global _pbs_client

    # Check if PBS is enabled
    pbs_host = os.getenv("PBS_HOST", "")
    if not pbs_host:
        logger.warning("PBS integration disabled (PBS_HOST not configured)")
        return None

    if _pbs_client is None:
        try:
            _pbs_client = PBSClient()
            logger.info("PBS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PBS client: {e}")
            return None

    return _pbs_client
