"""
Alert Management System

Handles Prometheus Alertmanager webhook integration and alert lifecycle tracking.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from shared.logging import get_logger

logger = get_logger(__name__)


class AlertStatus(str, Enum):
    """Alert status states"""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Alert:
    """Alert data model"""
    fingerprint: str
    status: AlertStatus
    severity: AlertSeverity
    name: str
    description: str
    instance: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    starts_at: datetime
    ends_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['starts_at'] = self.starts_at.isoformat()
        if self.ends_at:
            data['ends_at'] = self.ends_at.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        return data
    
    @classmethod
    def from_alertmanager(cls, alert_data: Dict[str, Any]) -> 'Alert':
        """Create Alert from Alertmanager webhook data"""
        labels = alert_data.get('labels', {})
        annotations = alert_data.get('annotations', {})
        
        # Parse severity
        severity_str = labels.get('severity', 'info').lower()
        severity = AlertSeverity(severity_str) if severity_str in AlertSeverity.__members__.values() else AlertSeverity.INFO
        
        # Parse status
        status_str = alert_data.get('status', 'firing').lower()
        status = AlertStatus(status_str) if status_str in AlertStatus.__members__.values() else AlertStatus.FIRING
        
        return cls(
            fingerprint=alert_data.get('fingerprint', ''),
            status=status,
            severity=severity,
            name=labels.get('alertname', 'Unknown'),
            description=annotations.get('description', annotations.get('summary', 'No description')),
            instance=labels.get('instance', labels.get('node', 'Unknown')),
            labels=labels,
            annotations=annotations,
            starts_at=datetime.fromisoformat(alert_data.get('startsAt', datetime.now().isoformat()).replace('Z', '+00:00')),
            ends_at=datetime.fromisoformat(alert_data.get('endsAt', '').replace('Z', '+00:00')) if alert_data.get('endsAt') else None
        )
    
    def format_telegram(self) -> str:
        """Format alert for Telegram message"""
        # Severity emoji
        emoji = {
            AlertSeverity.CRITICAL: "🔴",
            AlertSeverity.WARNING: "🟡",
            AlertSeverity.INFO: "🔵"
        }.get(self.severity, "⚪")
        
        # Status emoji
        status_emoji = {
            AlertStatus.FIRING: "🚨",
            AlertStatus.RESOLVED: "✅",
            AlertStatus.ACKNOWLEDGED: "👀",
            AlertStatus.SILENCED: "🔕"
        }.get(self.status, "❓")
        
        # Duration
        duration = datetime.now() - self.starts_at
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        message = f"""{status_emoji} **Alert: {self.name}**

{emoji} **Severity:** {self.severity.value.upper()}
📍 **Instance:** {self.instance}
⏱️ **Duration:** {duration_str}

{self.description}

**Fingerprint:** `{self.fingerprint[:8]}...`
**Started:** {self.starts_at.strftime('%Y-%m-%d %H:%M:%S')}"""
        
        if self.ends_at:
            message += f"\n**Resolved:** {self.ends_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if self.acknowledged_at:
            message += f"\n\n👀 Acknowledged by {self.acknowledged_by} at {self.acknowledged_at.strftime('%H:%M:%S')}"
        
        return message


class AlertManager:
    """
    Alert management system
    
    Tracks active alerts, handles acknowledgments, and manages alert lifecycle.
    """
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}  # fingerprint -> Alert
        self.logger = get_logger(__name__)
        self.notification_callbacks: List[callable] = []
    
    def register_notification_callback(self, callback: callable):
        """Register a callback for alert notifications"""
        self.notification_callbacks.append(callback)
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> List[Alert]:
        """
        Process Alertmanager webhook payload
        
        Args:
            webhook_data: Alertmanager webhook JSON payload
            
        Returns:
            List of processed alerts
        """
        self.logger.info("Processing Alertmanager webhook", 
                        alerts_count=len(webhook_data.get('alerts', [])))
        
        processed_alerts = []
        
        for alert_data in webhook_data.get('alerts', []):
            try:
                alert = Alert.from_alertmanager(alert_data)
                
                # Update or add alert
                existing = self.alerts.get(alert.fingerprint)
                
                if existing:
                    # Update existing alert
                    if alert.status == AlertStatus.RESOLVED:
                        alert.ends_at = datetime.now()
                        self.logger.info("Alert resolved", alert=alert.name, fingerprint=alert.fingerprint[:8])
                    
                    # Preserve acknowledgment if exists
                    if existing.acknowledged_at:
                        alert.acknowledged_at = existing.acknowledged_at
                        alert.acknowledged_by = existing.acknowledged_by
                        alert.status = AlertStatus.ACKNOWLEDGED
                else:
                    self.logger.info("New alert received", alert=alert.name, 
                                   severity=alert.severity.value, fingerprint=alert.fingerprint[:8])
                
                self.alerts[alert.fingerprint] = alert
                processed_alerts.append(alert)
                
                # Trigger notification callbacks
                for callback in self.notification_callbacks:
                    try:
                        await callback(alert)
                    except Exception as e:
                        self.logger.error("Notification callback failed", error=str(e))
                
            except Exception as e:
                self.logger.error("Error processing alert", error=str(e), alert_data=alert_data)
        
        return processed_alerts
    
    def acknowledge_alert(self, fingerprint: str, user: str) -> Optional[Alert]:
        """
        Acknowledge an alert
        
        Args:
            fingerprint: Alert fingerprint (full or prefix)
            user: Username/ID of acknowledger
            
        Returns:
            Acknowledged alert or None
        """
        # Find alert by full fingerprint or prefix
        alert = self.alerts.get(fingerprint)
        if not alert:
            # Try prefix match
            matches = [a for fp, a in self.alerts.items() if fp.startswith(fingerprint)]
            if matches:
                alert = matches[0]
        
        if alert and alert.status == AlertStatus.FIRING:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            alert.acknowledged_by = user
            self.logger.info("Alert acknowledged", alert=alert.name, 
                           fingerprint=fingerprint[:8], user=user)
            return alert
        
        return None
    
    def silence_alert(self, fingerprint: str, duration_minutes: int = 60) -> Optional[Alert]:
        """
        Silence an alert for a duration
        
        Args:
            fingerprint: Alert fingerprint
            duration_minutes: Silence duration in minutes
            
        Returns:
            Silenced alert or None
        """
        alert = self.alerts.get(fingerprint)
        if not alert:
            # Try prefix match
            matches = [a for fp, a in self.alerts.items() if fp.startswith(fingerprint)]
            if matches:
                alert = matches[0]
        
        if alert:
            alert.status = AlertStatus.SILENCED
            self.logger.info("Alert silenced", alert=alert.name, 
                           duration=duration_minutes, fingerprint=fingerprint[:8])
            return alert
        
        return None
    
    def get_active_alerts(self, include_resolved: bool = False) -> List[Alert]:
        """Get list of active alerts"""
        alerts = list(self.alerts.values())
        
        if not include_resolved:
            alerts = [a for a in alerts if a.status != AlertStatus.RESOLVED]
        
        # Sort by severity and start time
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 99), a.starts_at), reverse=True)
        
        return alerts
    
    def get_alert_by_fingerprint(self, fingerprint: str) -> Optional[Alert]:
        """Get alert by fingerprint (full or prefix)"""
        alert = self.alerts.get(fingerprint)
        if not alert:
            # Try prefix match
            matches = [a for fp, a in self.alerts.items() if fp.startswith(fingerprint)]
            if matches:
                alert = matches[0]
        return alert
    
    def get_stats(self) -> Dict[str, int]:
        """Get alert statistics"""
        stats = {
            'total': len(self.alerts),
            'firing': 0,
            'acknowledged': 0,
            'resolved': 0,
            'silenced': 0,
            'critical': 0,
            'warning': 0,
            'info': 0
        }
        
        for alert in self.alerts.values():
            if alert.status == AlertStatus.FIRING:
                stats['firing'] += 1
            elif alert.status == AlertStatus.ACKNOWLEDGED:
                stats['acknowledged'] += 1
            elif alert.status == AlertStatus.RESOLVED:
                stats['resolved'] += 1
            elif alert.status == AlertStatus.SILENCED:
                stats['silenced'] += 1
            
            if alert.severity == AlertSeverity.CRITICAL:
                stats['critical'] += 1
            elif alert.severity == AlertSeverity.WARNING:
                stats['warning'] += 1
            elif alert.severity == AlertSeverity.INFO:
                stats['info'] += 1
        
        return stats
    
    def cleanup_old_alerts(self, hours: int = 24):
        """Remove resolved alerts older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        to_remove = []
        for fingerprint, alert in self.alerts.items():
            if alert.status == AlertStatus.RESOLVED and alert.ends_at and alert.ends_at < cutoff:
                to_remove.append(fingerprint)
        
        for fingerprint in to_remove:
            del self.alerts[fingerprint]
        
        if to_remove:
            self.logger.info("Cleaned up old alerts", count=len(to_remove))


# Global alert manager instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
