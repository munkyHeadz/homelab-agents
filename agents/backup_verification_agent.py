"""
Backup Verification Agent

Automatically verifies backup integrity and tests restore capability:
- Monitors backup job status
- Verifies backup file integrity
- Tests restore operations (dry-run)
- Tracks backup success rates
- Alerts on backup failures or missed backups
- Generates backup health reports
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class BackupStatus(Enum):
    """Backup status types"""
    SUCCESS = "success"
    FAILED = "failed"
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    CORRUPTED = "corrupted"


class VerificationLevel(Enum):
    """Verification depth levels"""
    BASIC = "basic"           # Check backup exists and has recent timestamp
    CHECKSUM = "checksum"     # Verify file integrity via checksums
    RESTORE_TEST = "restore_test"  # Perform actual restore test


@dataclass
class BackupInfo:
    """Information about a backup"""
    vm_id: int
    vm_name: str
    backup_time: datetime
    backup_size: int
    backup_file: str
    status: BackupStatus
    verification_level: Optional[VerificationLevel] = None
    verification_time: Optional[datetime] = None
    verification_result: Optional[str] = None
    restore_test_passed: bool = False


class BackupVerificationAgent:
    """
    Verifies backup integrity and tests restore capability

    Features:
    - Automatic backup monitoring
    - Integrity verification
    - Restore testing (dry-run mode)
    - Failure alerts
    - Success rate tracking
    - Historical analysis
    """

    def __init__(self, telegram_notifier=None, infrastructure_agent=None):
        self.logger = get_logger(__name__)
        self.telegram_notifier = telegram_notifier
        self.infrastructure_agent = infrastructure_agent

        # Configuration
        self.verification_interval = int(config.get("BACKUP_VERIFICATION_INTERVAL", "86400"))  # 24 hours
        self.max_backup_age = int(config.get("MAX_BACKUP_AGE_HOURS", "48"))  # 48 hours
        self.enable_restore_tests = config.get("ENABLE_RESTORE_TESTS", "false").lower() == "true"

        # Tracking
        self.backup_history: List[BackupInfo] = []
        self.last_verification_time = None
        self.verification_results: Dict[int, BackupInfo] = {}  # vm_id -> latest backup info

        # Critical VMs that MUST have backups
        self.critical_vms = self._parse_critical_vms()

        self.logger.info("Backup Verification Agent initialized")

    def _parse_critical_vms(self) -> List[int]:
        """Parse critical VM IDs from config"""
        critical = config.get("CRITICAL_VMS", "")
        if not critical:
            return []

        try:
            return [int(vm_id.strip()) for vm_id in critical.split(",") if vm_id.strip()]
        except Exception as e:
            self.logger.error(f"Error parsing CRITICAL_VMS: {e}")
            return []

    async def get_all_backups(self) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get all backups from Proxmox

        Returns:
            Dict mapping VM ID to list of backups
        """
        if not self.infrastructure_agent:
            self.logger.warning("No infrastructure agent available")
            return {}

        try:
            # Get all VMs first
            vms_result = await self.infrastructure_agent.execute("List all VMs and containers")
            if not vms_result.get("success"):
                self.logger.error("Failed to get VM list")
                return {}

            # Get backups for each VM
            backups_by_vm = {}

            # Use Proxmox MCP to get backup information
            from mcp_tools.proxmox_mcp import ProxmoxMCP
            proxmox = ProxmoxMCP()

            # Get all backup volumes
            result = await proxmox.list_backups()

            if result.get("success"):
                # Group backups by VM ID
                for backup in result.get("backups", []):
                    vm_id = backup.get("vmid")
                    if vm_id:
                        if vm_id not in backups_by_vm:
                            backups_by_vm[vm_id] = []
                        backups_by_vm[vm_id].append(backup)

            return backups_by_vm

        except Exception as e:
            self.logger.error(f"Error getting backups: {e}")
            return {}

    async def verify_backup_exists(self, vm_id: int) -> Tuple[BackupStatus, Optional[BackupInfo]]:
        """
        Verify that a recent backup exists for a VM

        Args:
            vm_id: VM ID to check

        Returns:
            Tuple of (status, backup_info)
        """
        try:
            backups_by_vm = await self.get_all_backups()
            backups = backups_by_vm.get(vm_id, [])

            if not backups:
                return BackupStatus.MISSING, None

            # Get most recent backup
            latest_backup = max(backups, key=lambda b: b.get("ctime", 0))

            backup_time = datetime.fromtimestamp(latest_backup.get("ctime", 0))
            age_hours = (datetime.now() - backup_time).total_seconds() / 3600

            # Check if backup is too old
            if age_hours > self.max_backup_age:
                return BackupStatus.MISSING, None

            backup_info = BackupInfo(
                vm_id=vm_id,
                vm_name=latest_backup.get("vmname", f"VM {vm_id}"),
                backup_time=backup_time,
                backup_size=latest_backup.get("size", 0),
                backup_file=latest_backup.get("volid", ""),
                status=BackupStatus.SUCCESS,
                verification_level=VerificationLevel.BASIC,
                verification_time=datetime.now()
            )

            return BackupStatus.SUCCESS, backup_info

        except Exception as e:
            self.logger.error(f"Error verifying backup for VM {vm_id}: {e}")
            return BackupStatus.FAILED, None

    async def verify_backup_integrity(self, backup_info: BackupInfo) -> Tuple[bool, str]:
        """
        Verify backup file integrity

        Args:
            backup_info: Backup information

        Returns:
            Tuple of (success, message)
        """
        try:
            # In a real implementation, this would:
            # 1. Download backup file metadata
            # 2. Verify checksums
            # 3. Check for corruption

            # For now, we'll do a basic check
            if backup_info.backup_size == 0:
                return False, "Backup file size is zero"

            # Check if backup file exists on storage
            from mcp_tools.proxmox_mcp import ProxmoxMCP
            proxmox = ProxmoxMCP()

            result = await proxmox.verify_backup(backup_info.backup_file)

            if result.get("success"):
                backup_info.verification_level = VerificationLevel.CHECKSUM
                backup_info.verification_time = datetime.now()
                return True, "Backup integrity verified"
            else:
                return False, result.get("error", "Unknown verification error")

        except Exception as e:
            self.logger.error(f"Error verifying backup integrity: {e}")
            return False, str(e)

    async def test_backup_restore(self, backup_info: BackupInfo) -> Tuple[bool, str]:
        """
        Test backup restore capability (dry-run)

        This performs a simulated restore to verify the backup can be restored
        without actually creating a VM.

        Args:
            backup_info: Backup information

        Returns:
            Tuple of (success, message)
        """
        if not self.enable_restore_tests:
            return True, "Restore tests disabled in configuration"

        try:
            from mcp_tools.proxmox_mcp import ProxmoxMCP
            proxmox = ProxmoxMCP()

            # Perform dry-run restore test
            result = await proxmox.test_restore(
                backup_file=backup_info.backup_file,
                vm_id=backup_info.vm_id,
                dry_run=True
            )

            if result.get("success"):
                backup_info.verification_level = VerificationLevel.RESTORE_TEST
                backup_info.restore_test_passed = True
                backup_info.verification_time = datetime.now()
                return True, "Restore test passed"
            else:
                backup_info.restore_test_passed = False
                return False, result.get("error", "Restore test failed")

        except Exception as e:
            self.logger.error(f"Error testing restore: {e}")
            return False, str(e)

    async def verify_all_backups(self) -> Dict[str, Any]:
        """
        Verify all VM backups

        Returns:
            Dictionary with verification results
        """
        self.logger.info("Starting backup verification")

        results = {
            "total_vms": 0,
            "verified": 0,
            "failed": 0,
            "missing": 0,
            "critical_missing": [],
            "failures": [],
            "warnings": []
        }

        try:
            # Get all VMs
            if not self.infrastructure_agent:
                return results

            vms_result = await self.infrastructure_agent.execute("List all VMs and containers")
            if not vms_result.get("success"):
                return results

            vms = vms_result.get("vms", [])
            results["total_vms"] = len(vms)

            # Verify each VM's backup
            for vm in vms:
                vm_id = vm.get("vmid")
                if not vm_id:
                    continue

                # Check if backup exists
                status, backup_info = await self.verify_backup_exists(vm_id)

                if status == BackupStatus.MISSING:
                    results["missing"] += 1

                    # Check if this is a critical VM
                    if vm_id in self.critical_vms:
                        results["critical_missing"].append({
                            "vm_id": vm_id,
                            "vm_name": vm.get("name", f"VM {vm_id}")
                        })

                    results["warnings"].append(f"No recent backup for VM {vm_id}")
                    continue

                if status == BackupStatus.FAILED or not backup_info:
                    results["failed"] += 1
                    results["failures"].append(f"Failed to verify backup for VM {vm_id}")
                    continue

                # Verify backup integrity
                integrity_ok, message = await self.verify_backup_integrity(backup_info)

                if not integrity_ok:
                    results["failed"] += 1
                    results["failures"].append(f"VM {vm_id}: {message}")
                    backup_info.status = BackupStatus.CORRUPTED
                else:
                    results["verified"] += 1

                # Store result
                self.verification_results[vm_id] = backup_info
                self.backup_history.append(backup_info)

            self.last_verification_time = datetime.now()

            # Send alerts if needed
            await self._send_verification_alerts(results)

            return results

        except Exception as e:
            self.logger.error(f"Error verifying backups: {e}")
            return results

    async def _send_verification_alerts(self, results: Dict[str, Any]):
        """Send alerts based on verification results"""
        if not self.telegram_notifier:
            return

        # Alert on critical VM backups missing
        if results["critical_missing"]:
            message = "🚨 **CRITICAL: Missing Backups**\n\n"
            message += "The following critical VMs have no recent backups:\n\n"

            for vm in results["critical_missing"]:
                message += f"• VM {vm['vm_id']}: {vm['vm_name']}\n"

            message += f"\n**Action Required:** Check backup jobs immediately!"

            await self.telegram_notifier.send_message(message)

        # Alert on failures
        if results["failures"]:
            if len(results["failures"]) <= 3:
                message = "⚠️ **Backup Verification Failures**\n\n"
                for failure in results["failures"]:
                    message += f"• {failure}\n"

                await self.telegram_notifier.send_message(message)

    async def generate_backup_report(self) -> str:
        """
        Generate comprehensive backup status report

        Returns:
            Formatted report string
        """
        if not self.verification_results:
            await self.verify_all_backups()

        report_lines = [
            "💾 **Backup Verification Report**",
            f"🗓️ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        if self.last_verification_time:
            report_lines.append(f"**Last Verification:** {self.last_verification_time.strftime('%Y-%m-%d %H:%M')}")

        report_lines.append("")

        # Summary statistics
        total = len(self.verification_results)
        verified = sum(1 for b in self.verification_results.values()
                      if b.status == BackupStatus.SUCCESS)
        failed = sum(1 for b in self.verification_results.values()
                    if b.status in [BackupStatus.FAILED, BackupStatus.CORRUPTED])

        report_lines.extend([
            "**📊 Summary**",
            f"Total VMs: {total}",
            f"✅ Verified: {verified}",
            f"❌ Failed: {failed}",
            ""
        ])

        # Recent backups
        recent_backups = sorted(
            self.verification_results.values(),
            key=lambda b: b.backup_time,
            reverse=True
        )[:5]

        if recent_backups:
            report_lines.append("**🕐 Recent Backups**")
            for backup in recent_backups:
                age_hours = (datetime.now() - backup.backup_time).total_seconds() / 3600
                size_gb = backup.backup_size / (1024**3)

                status_emoji = "✅" if backup.status == BackupStatus.SUCCESS else "❌"
                report_lines.append(
                    f"{status_emoji} VM {backup.vm_id} ({backup.vm_name}): "
                    f"{age_hours:.1f}h ago, {size_gb:.1f} GB"
                )
            report_lines.append("")

        # Warnings
        warnings = []
        for vm_id, backup in self.verification_results.items():
            age_hours = (datetime.now() - backup.backup_time).total_seconds() / 3600

            if age_hours > 24:
                warnings.append(f"• VM {vm_id}: Backup is {age_hours:.1f} hours old")

            if backup.status == BackupStatus.CORRUPTED:
                warnings.append(f"• VM {vm_id}: Backup integrity check failed")

        if warnings:
            report_lines.append("**⚠️ Warnings**")
            report_lines.extend(warnings)
            report_lines.append("")

        # Recommendations
        report_lines.extend([
            "**💡 Recommendations**",
            "• Backups should run daily",
            "• Verify backup integrity weekly",
            "• Test restores monthly",
            "• Monitor backup storage space"
        ])

        return "\n".join(report_lines)

    async def get_backup_success_rate(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate backup success rate over time

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with success rate data
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_backups = [b for b in self.backup_history if b.backup_time >= cutoff]

        if not recent_backups:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0
            }

        total = len(recent_backups)
        successful = sum(1 for b in recent_backups if b.status == BackupStatus.SUCCESS)
        failed = total - successful

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "period_days": days
        }

    async def run_verification_loop(self):
        """
        Main verification loop

        Runs backup verification on a schedule
        """
        self.logger.info(f"Starting backup verification loop (every {self.verification_interval}s)")

        while True:
            try:
                # Run verification
                results = await self.verify_all_backups()

                self.logger.info(
                    f"Backup verification complete: "
                    f"{results['verified']} verified, "
                    f"{results['failed']} failed, "
                    f"{results['missing']} missing"
                )

                # Wait for next verification
                await asyncio.sleep(self.verification_interval)

            except Exception as e:
                self.logger.error(f"Error in verification loop: {e}")
                await asyncio.sleep(self.verification_interval)


async def main():
    """Run backup verification standalone"""
    agent = BackupVerificationAgent()
    await agent.run_verification_loop()


if __name__ == "__main__":
    asyncio.run(main())
