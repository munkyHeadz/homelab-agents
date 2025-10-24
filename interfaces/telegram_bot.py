#!/usr/bin/env python3
"""
Telegram Bot Interface for Homelab Agent System - Enhanced Version

Provides a Telegram bot interface to interact with the autonomous agent system.

Features:
- System status and monitoring
- VM/Container management with safety confirmations
- Alert integration with Prometheus/Alertmanager
- Docker container control
- Natural language interface
- Automatic updates
"""

import asyncio
import os
import json
import re
import subprocess
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.infrastructure_agent import InfrastructureAgent
from agents.monitoring_agent import MonitoringAgent
from agents.network_agent import NetworkAgent
from shared.config import config
from shared.logging import get_logger
from shared.metrics import start_metrics_server, get_metrics_collector
from shared.alert_manager import get_alert_manager, Alert, AlertStatus
from shared.report_scheduler import get_report_scheduler
from interfaces.webhook_server import WebhookServer

logger = get_logger(__name__)


class TelegramBotInterface:
    """
    Enhanced Telegram bot interface for agent system
    
    Integrates with:
    - Infrastructure Agent: VM/Container management
    - Monitoring Agent: Resource monitoring and alerts
    - Alert Manager: Prometheus/Alertmanager integration
    - Webhook Server: Alert notifications
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.token = config.telegram.bot_token
        self.allowed_users = config.telegram.admin_ids
        self.start_time = datetime.now()
        self.application = None  # Will be set in run()

        # Initialize agents
        self.infrastructure_agent = InfrastructureAgent()
        self.monitoring_agent = MonitoringAgent()
        self.network_agent = NetworkAgent()

        # Initialize alert system
        self.alert_manager = get_alert_manager()
        self.webhook_server = WebhookServer(port=8001, alert_callback=self.on_alert_received)

        # Initialize report scheduler (callback set later in run_async)
        self.report_scheduler = get_report_scheduler()

        # Pending confirmations for destructive actions
        self.pending_confirmations = {}

        self.logger.info("Telegram bot interface initialized with alert integration and scheduled reports")

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot"""
        return str(user_id) in self.allowed_users

    def parse_json_response(self, text: str) -> Optional[Dict]:
        """Extract and parse JSON from MCP response"""
        try:
            return json.loads(text)
        except:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
        return None

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    def format_uptime(self, seconds: int) -> str:
        """Format uptime in human readable format"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "< 1m"

    def format_percentage(self, used: float, total: float) -> str:
        """Format usage percentage with visual indicator"""
        if total == 0:
            return "N/A"

        pct = (used / total) * 100

        if pct < 50:
            emoji = "🟢"
        elif pct < 80:
            emoji = "🟡"
        else:
            emoji = "🔴"

        return f"{emoji} {pct:.1f}%"

    def parse_proxmox_node_status(self, raw_data: str) -> str:
        """Parse and format Proxmox node status"""
        try:
            data = self.parse_json_response(raw_data)
            if data:
                cpu_pct = data.get('cpu', 0) * 100
                mem_used = data.get('memory', {}).get('used', 0)
                mem_total = data.get('memory', {}).get('total', 0)
                uptime = data.get('uptime', 0)

                return f"""🖥️ **Node: {data.get('node', 'Unknown')}**

**CPU Usage:** {self.format_percentage(cpu_pct, 100)}
**Memory:** {self.format_bytes(mem_used)} / {self.format_bytes(mem_total)} ({self.format_percentage(mem_used, mem_total)})
**Uptime:** {self.format_uptime(uptime)}
**Load Average:** {data.get('loadavg', ['N/A', 'N/A', 'N/A'])[0]}"""
            else:
                return self._format_text_data(raw_data)
        except Exception as e:
            self.logger.error(f"Error parsing node status: {e}")
            return raw_data[:500]

    def parse_docker_info(self, raw_data: str) -> str:
        """Parse and format Docker system info"""
        try:
            data = self.parse_json_response(raw_data)
            if data:
                containers = data.get('Containers', 0)
                running = data.get('ContainersRunning', 0)
                paused = data.get('ContainersPaused', 0)
                stopped = data.get('ContainersStopped', 0)
                images = data.get('Images', 0)

                return f"""🐳 **Docker System**

**Containers:** {containers} total
  └ Running: {running} | Stopped: {stopped} | Paused: {paused}
**Images:** {images}
**Version:** {data.get('ServerVersion', 'Unknown')}
**Storage Driver:** {data.get('Driver', 'Unknown')}"""
            else:
                return self._format_text_data(raw_data)
        except Exception as e:
            self.logger.error(f"Error parsing Docker info: {e}")
            return raw_data[:500]

    def parse_vm_list(self, raw_data: str) -> str:
        """Parse and format VM/Container list"""
        try:
            data = self.parse_json_response(raw_data)
            if isinstance(data, list):
                lxc_containers = []
                vms = []

                for item in data:
                    status_emoji = "✅" if item.get('status') == 'running' else "⭕"
                    name = item.get('name', f"ID {item.get('vmid', 'Unknown')}")
                    vmid = item.get('vmid', '?')
                    mem = self.format_bytes(item.get('mem', 0))
                    maxmem = self.format_bytes(item.get('maxmem', 0))
                    cpu = item.get('cpu', 0) * 100
                    uptime_days = item.get('uptime', 0) / 86400

                    # Compact format
                    line = f"{status_emoji} `{vmid}` {name}\n"
                    if item.get('status') == 'running':
                        line += f"    💻 {cpu:.1f}% | 🧠 {mem}/{maxmem} | ⏱ {uptime_days:.1f}d"
                    else:
                        line += f"    Status: {item.get('status', 'unknown')}"

                    if item.get('type') == 'lxc':
                        lxc_containers.append(line)
                    else:
                        vms.append(line)

                parts = []
                if vms:
                    parts.append(f"🖥️ **Virtual Machines** ({len(vms)})\n" + "\n".join(vms))
                if lxc_containers:
                    parts.append(f"📦 **LXC Containers** ({len(lxc_containers)})\n" + "\n".join(lxc_containers))

                return "\n\n".join(parts) if parts else "No VMs or containers found"
            else:
                # Handle text format - replace escaped newlines
                formatted = raw_data.replace('\\n', '\n').strip()
                if len(formatted) > 3000:
                    formatted = formatted[:3000] + "\n\n_... (truncated - too many items)_"
                return formatted
        except Exception as e:
            self.logger.error(f"Error parsing VM list: {e}")
            return raw_data[:1000].replace('\\n', '\n')

    def parse_container_list(self, raw_data: str) -> str:
        """Parse and format Docker container list"""
        try:
            data = self.parse_json_response(raw_data)
            if isinstance(data, list):
                if not data:
                    return "🐳 No Docker containers found"

                result = f"🐳 **Docker Containers** ({len(data)})\n\n"
                for container in data:
                    status = container.get('State', 'unknown')
                    status_emoji = "✅" if status == 'running' else "⭕"
                    name = container.get('Names', ['Unknown'])[0].lstrip('/')
                    image = container.get('Image', 'Unknown')

                    # Shorten image name if too long
                    if len(image) > 40:
                        image = image[:37] + "..."

                    result += f"{status_emoji} `{name}`\n"
                    result += f"    📦 {image}\n"
                    result += f"    {container.get('Status', 'Unknown')}\n\n"

                return result.strip()
            else:
                # Handle text format
                formatted = raw_data.replace('\\n', '\n').strip()
                if len(formatted) > 3000:
                    formatted = formatted[:3000] + "\n\n_... (truncated)_"
                return formatted
        except Exception as e:
            self.logger.error(f"Error parsing container list: {e}")
            return raw_data[:1000].replace('\\n', '\n')

    def _format_text_data(self, text: str) -> str:
        """Format plain text data for better readability"""
        # Replace escaped newlines with actual newlines
        text = text.replace('\\n', '\n')
        # Remove excessive blank lines
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        # Telegram message limit is 4096, but leave room for formatting
        if len(text) > 3500:
            text = text[:3500] + "\n\n_... (truncated - message too long)_"
        return text.strip()

    # === ALERT SYSTEM COMMANDS (Phase A) ===

    async def on_alert_received(self, alert: Alert):
        """Callback when alert is received from Alertmanager"""
        if alert.status != AlertStatus.FIRING:
            return
        
        try:
            message = alert.format_telegram()
            
            for admin_id in self.allowed_users:
                try:
                    if self.application:
                        await self.application.bot.send_message(
                            chat_id=admin_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    self.logger.error(f"Failed to send alert to {admin_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error in alert callback: {e}")

    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command - show active alerts"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        alerts = self.alert_manager.get_active_alerts()
        stats = self.alert_manager.get_stats()
        
        if not alerts:
            await update.message.reply_text(
                "✅ No active alerts!\n\nAll systems operational.",
                parse_mode='Markdown'
            )
            return
        
        response = f"""🚨 **Active Alerts** ({stats['firing']} firing)

**Summary:**
🔴 Critical: {stats['critical']}
🟡 Warning: {stats['warning']}
👀 Acknowledged: {stats['acknowledged']}
🔕 Silenced: {stats['silenced']}

**Alerts:**
"""
        
        for alert in alerts[:10]:
            emoji = {
                AlertStatus.FIRING: "🚨",
                AlertStatus.ACKNOWLEDGED: "👀",
                AlertStatus.SILENCED: "🔕"
            }.get(alert.status, "❓")

            from datetime import timezone
            duration = datetime.now(timezone.utc) - alert.starts_at
            minutes = int(duration.total_seconds() // 60)
            
            response += f"\n{emoji} **{alert.name}**\n"
            response += f"  └ {alert.instance} • {minutes}m • `{alert.fingerprint[:8]}`\n"
        
        if len(alerts) > 10:
            response += f"\n_... and {len(alerts) - 10} more_"
        
        response += "\n\nUse `/ack <fingerprint>` to acknowledge"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def ack_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ack command - acknowledge an alert"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/ack <fingerprint>`\n\nExample: `/ack a1b2c3d4`",
                parse_mode='Markdown'
            )
            return
        
        fingerprint = context.args[0]
        user = update.effective_user.username or str(update.effective_user.id)
        
        alert = self.alert_manager.acknowledge_alert(fingerprint, user)
        
        if alert:
            await update.message.reply_text(
                f"✅ **Alert Acknowledged**\n\n"
                f"**Alert:** {alert.name}\n"
                f"**Instance:** {alert.instance}\n"
                f"**Acknowledged by:** {user}\n\n"
                f"Alert will no longer send notifications.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Alert `{fingerprint}` not found or already acknowledged.",
                parse_mode='Markdown'
            )

    async def silence_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /silence command - silence an alert"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/silence <fingerprint> [duration_minutes]`\n\n"
                "Example: `/silence a1b2c3d4 60`",
                parse_mode='Markdown'
            )
            return
        
        fingerprint = context.args[0]
        duration = int(context.args[1]) if len(context.args) > 1 else 60
        
        alert = self.alert_manager.silence_alert(fingerprint, duration)
        
        if alert:
            await update.message.reply_text(
                f"🔕 **Alert Silenced**\n\n"
                f"**Alert:** {alert.name}\n"
                f"**Instance:** {alert.instance}\n"
                f"**Duration:** {duration} minutes\n\n"
                f"Alert notifications suppressed for {duration}m.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Alert `{fingerprint}` not found.",
                parse_mode='Markdown'
            )

    # === VM/CONTAINER CONTROL COMMANDS (Phase B) ===

    async def start_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_vm command - start a VM or container"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/start_vm <vmid>`\n\nExample: `/start_vm 101`",
                parse_mode='Markdown'
            )
            return
        
        vmid = context.args[0]
        msg = await update.message.reply_text(f"🔄 Starting VM/Container {vmid}...")
        
        try:
            result = await self.infrastructure_agent.execute(f"Start VM or container {vmid}")
            
            if result.get("success"):
                await msg.edit_text(
                    f"✅ **VM/Container Started**\n\n"
                    f"**ID:** {vmid}\n"
                    f"**Status:** Running\n\n"
                    f"{result.get('summary', 'Started successfully')}",
                    parse_mode='Markdown'
                )
            else:
                await msg.edit_text(
                    f"❌ **Failed to Start**\n\n"
                    f"**ID:** {vmid}\n"
                    f"**Error:** {result.get('error', 'Unknown error')}",
                    parse_mode='Markdown'
                )
        except Exception as e:
            self.logger.error(f"Error starting VM: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def stop_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_vm command - stop a VM or container"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/stop_vm <vmid>`\n\nExample: `/stop_vm 101`",
                parse_mode='Markdown'
            )
            return
        
        vmid = context.args[0]
        
        confirmation_id = f"stop_{vmid}_{update.effective_user.id}"
        self.pending_confirmations[confirmation_id] = {
            'action': 'stop_vm',
            'vmid': vmid,
            'user_id': update.effective_user.id,
            'expires': datetime.now() + timedelta(minutes=5)
        }
        
        await update.message.reply_text(
            f"⚠️ **Confirm VM Stop**\n\n"
            f"**ID:** {vmid}\n\n"
            f"This will stop the VM/container.\n"
            f"Send `/confirm {confirmation_id[:8]}` to proceed.",
            parse_mode='Markdown'
        )

    async def restart_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /restart_vm command - restart a VM or container"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/restart_vm <vmid>`\n\nExample: `/restart_vm 101`",
                parse_mode='Markdown'
            )
            return
        
        vmid = context.args[0]
        msg = await update.message.reply_text(f"🔄 Restarting VM/Container {vmid}...")
        
        try:
            result = await self.infrastructure_agent.execute(f"Restart VM or container {vmid}")
            
            if result.get("success"):
                await msg.edit_text(
                    f"✅ **VM/Container Restarted**\n\n"
                    f"**ID:** {vmid}\n"
                    f"**Status:** Restarting\n\n"
                    f"{result.get('summary', 'Restarted successfully')}",
                    parse_mode='Markdown'
                )
            else:
                await msg.edit_text(
                    f"❌ **Failed to Restart**\n\n"
                    f"**ID:** {vmid}\n"
                    f"**Error:** {result.get('error', 'Unknown error')}",
                    parse_mode='Markdown'
                )
        except Exception as e:
            self.logger.error(f"Error restarting VM: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def confirm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /confirm command - confirm destructive actions"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/confirm <confirmation_id>`",
                parse_mode='Markdown'
            )
            return
        
        conf_prefix = context.args[0]
        
        confirmation = None
        conf_id = None
        for cid, conf in list(self.pending_confirmations.items()):
            if cid.startswith(conf_prefix) and conf['user_id'] == update.effective_user.id:
                confirmation = conf
                conf_id = cid
                break
        
        if not confirmation:
            await update.message.reply_text(
                "❌ No pending confirmation found or expired.",
                parse_mode='Markdown'
            )
            return
        
        if datetime.now() > confirmation['expires']:
            del self.pending_confirmations[conf_id]
            await update.message.reply_text(
                "❌ Confirmation expired. Please try again.",
                parse_mode='Markdown'
            )
            return
        
        action = confirmation['action']
        vmid = confirmation['vmid']
        
        del self.pending_confirmations[conf_id]
        
        msg = await update.message.reply_text(f"✅ Confirmed. Executing {action}...")
        
        try:
            if action == 'stop_vm':
                result = await self.infrastructure_agent.execute(f"Stop VM or container {vmid}")
                
                if result.get("success"):
                    await msg.edit_text(
                        f"✅ **VM/Container Stopped**\n\n"
                        f"**ID:** {vmid}\n"
                        f"**Status:** Stopped\n\n"
                        f"{result.get('summary', 'Stopped successfully')}",
                        parse_mode='Markdown'
                    )
                else:
                    await msg.edit_text(
                        f"❌ **Failed to Stop**\n\n"
                        f"**ID:** {vmid}\n"
                        f"**Error:** {result.get('error', 'Unknown error')}",
                        parse_mode='Markdown'
                    )
        except Exception as e:
            self.logger.error(f"Error executing confirmed action: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    # === SCHEDULED REPORTS COMMANDS (Phase D) ===

    async def daily_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /daily_report command - generate daily summary on demand"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("📊 Generating daily summary report...")

        try:
            report = await self.report_scheduler.generate_daily_summary(
                self.infrastructure_agent,
                self.monitoring_agent
            )
            await msg.edit_text(report, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"Error in daily_report command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def weekly_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weekly_report command - generate weekly trends on demand"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("📈 Generating weekly trends report...")

        try:
            report = await self.report_scheduler.generate_weekly_trends(
                self.infrastructure_agent,
                self.monitoring_agent
            )
            await msg.edit_text(report, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"Error in weekly_report command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule command - view and configure scheduled reports"""
        if not self.is_authorized(update.effective_user.id):
            return

        config = self.report_scheduler.get_config()

        response = "⏰ **Scheduled Reports Configuration**\n\n"

        # Daily summary
        daily_enabled = config['enabled'].get('daily_summary', False)
        daily_schedule = config['schedules'].get('daily_summary', 'Not set')
        daily_last = config['last_runs'].get('daily_summary')

        response += f"**📊 Daily System Summary**\n"
        response += f"Status: {'✅ Enabled' if daily_enabled else '⭕ Disabled'}\n"
        response += f"Schedule: {daily_schedule}\n"
        if daily_last:
            response += f"Last run: {daily_last.strftime('%Y-%m-%d %H:%M UTC')}\n"
        response += "\n"

        # Weekly trends
        weekly_enabled = config['enabled'].get('weekly_trends', False)
        weekly_schedule = config['schedules'].get('weekly_trends', 'Not set')
        weekly_last = config['last_runs'].get('weekly_trends')

        response += f"**📈 Weekly Resource Trends**\n"
        response += f"Status: {'✅ Enabled' if weekly_enabled else '⭕ Disabled'}\n"
        response += f"Schedule: {weekly_schedule}\n"
        if weekly_last:
            response += f"Last run: {weekly_last.strftime('%Y-%m-%d %H:%M UTC')}\n"
        response += "\n"

        response += "**Commands:**\n"
        response += "`/daily_report` - Generate daily summary now\n"
        response += "`/weekly_report` - Generate weekly trends now\n"
        response += "`/schedule_enable <daily|weekly>` - Enable report\n"
        response += "`/schedule_disable <daily|weekly>` - Disable report"

        await update.message.reply_text(response, parse_mode='Markdown')

    async def schedule_enable_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule_enable command - enable a scheduled report"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: `/schedule_enable <daily|weekly>`\n\nExample: `/schedule_enable daily`",
                parse_mode='Markdown'
            )
            return

        report_type = context.args[0].lower()
        type_map = {
            'daily': 'daily_summary',
            'weekly': 'weekly_trends'
        }

        if report_type not in type_map:
            await update.message.reply_text(
                "❌ Invalid report type. Use `daily` or `weekly`",
                parse_mode='Markdown'
            )
            return

        self.report_scheduler.enable_report(type_map[report_type], True)
        await update.message.reply_text(
            f"✅ {report_type.title()} reports enabled",
            parse_mode='Markdown'
        )

    async def schedule_disable_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule_disable command - disable a scheduled report"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: `/schedule_disable <daily|weekly>`\n\nExample: `/schedule_disable weekly`",
                parse_mode='Markdown'
            )
            return

        report_type = context.args[0].lower()
        type_map = {
            'daily': 'daily_summary',
            'weekly': 'weekly_trends'
        }

        if report_type not in type_map:
            await update.message.reply_text(
                "❌ Invalid report type. Use `daily` or `weekly`",
                parse_mode='Markdown'
            )
            return

        self.report_scheduler.enable_report(type_map[report_type], False)
        await update.message.reply_text(
            f"⭕ {report_type.title()} reports disabled",
            parse_mode='Markdown'
        )

    # === NETWORK MONITORING COMMANDS (Phase E) ===

    async def network_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /network command - comprehensive network status"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🌐 Getting network status...")

        try:
            status = await self.network_agent.get_network_status()

            if status.get("success"):
                network_data = status.get("network", {})
                services = status.get("services", {})

                response = "🌐 **Network Status**\n\n"
                response += f"**Overall:** {network_data.get('status', 'Unknown').title()}\n"
                response += f"**Connected Devices:** {network_data.get('connected_devices', 0)}\n"
                response += f"**Bandwidth:** {network_data.get('current_usage_mbps', 0):.1f} / {network_data.get('total_bandwidth_mbps', 0)} Mbps\n"
                response += f"**Uptime:** {network_data.get('uptime_hours', 0):.1f} hours\n\n"

                response += "**Services:**\n"
                for service, state in services.items():
                    emoji = "✅" if state == "available" else "⭕"
                    response += f"{emoji} {service.title()}: {state}\n"

                if status.get("message"):
                    response += f"\n_{status.get('message')}_"

                await msg.edit_text(response, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {status.get('error', 'Unknown error')}",
                    parse_mode='Markdown'
                )

        except Exception as e:
            self.logger.error(f"Error in network command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def devices_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /devices command - list connected network devices"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("📱 Getting connected devices...")

        try:
            devices_data = await self.network_agent.get_connected_devices()

            if devices_data.get("success"):
                total = devices_data.get("total_devices", 0)
                devices = devices_data.get("devices", [])

                response = f"📱 **Connected Devices** ({total})\n\n"

                if not devices:
                    response += "No devices found\n\n"
                else:
                    for device in devices[:20]:  # Limit to 20 devices
                        name = device.get("name", "Unknown")
                        ip = device.get("ip_address", "N/A")
                        conn_type = device.get("connection_type", "unknown")
                        emoji = "📡" if conn_type == "wireless" else "🔌"

                        response += f"{emoji} **{name}**\n"
                        response += f"    IP: `{ip}`\n"
                        response += f"    Type: {conn_type}\n\n"

                    if total > 20:
                        response += f"_... and {total - 20} more devices_\n\n"

                if devices_data.get("message"):
                    response += f"_{devices_data.get('message')}_"

                await msg.edit_text(response, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {devices_data.get('error', 'Unknown error')}",
                    parse_mode='Markdown'
                )

        except Exception as e:
            self.logger.error(f"Error in devices command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def bandwidth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bandwidth command - show bandwidth usage"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("📊 Getting bandwidth statistics...")

        try:
            stats = await self.network_agent.get_bandwidth_stats()

            if stats.get("success"):
                bandwidth = stats.get("bandwidth", {})

                response = "📊 **Bandwidth Usage**\n\n"
                response += f"⬇️ Download: {bandwidth.get('download_mbps', 0):.1f} Mbps\n"
                response += f"⬆️ Upload: {bandwidth.get('upload_mbps', 0):.1f} Mbps\n"
                response += f"📈 Total: {bandwidth.get('total_mbps', 0):.1f} Mbps\n\n"

                if stats.get("message"):
                    response += f"_{stats.get('message')}_"

                await msg.edit_text(response, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {stats.get('error', 'Unknown error')}",
                    parse_mode='Markdown'
                )

        except Exception as e:
            self.logger.error(f"Error in bandwidth command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    # === EXISTING COMMANDS (Phases already complete) ===

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id

        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ Unauthorized. This bot is for authorized users only."
            )
            self.logger.warning(f"Unauthorized access attempt from user {user_id}")
            return

        welcome_message = """🤖 **Homelab Agent System**

Welcome! I'm your autonomous homelab management assistant.

**📊 System Commands:**
/status - Complete system overview
/uptime - Bot and system uptime
/monitor - Resource monitoring

**🖥️ Proxmox Commands:**
/node - Proxmox node status
/vms - List all VMs and containers
/infra - Infrastructure overview

**🐳 Docker Commands:**
/docker - Docker system info
/containers - List all containers

**🚨 Alert Commands:**
/alerts - Show active alerts
/ack <fingerprint> - Acknowledge alert
/silence <fingerprint> [min] - Silence alert

**🎮 VM Control:**
/start_vm <vmid> - Start VM/container
/stop_vm <vmid> - Stop VM/container (requires confirmation)
/restart_vm <vmid> - Restart VM/container
/confirm <id> - Confirm destructive action

**⚙️ Management:**
/update - Update bot code
/help - Show command reference

You can also send natural language requests!
        """

        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        self.logger.info(f"Start command from user {user_id}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.is_authorized(update.effective_user.id):
            return

        help_text = """📚 **Command Reference**

**System Status:**
/status - Overall system status
/uptime - System and bot uptime
/monitor - Real-time resource monitoring

**Proxmox Management:**
/node - Detailed node status
/vms - List all VMs and LXC containers
/infra - Infrastructure overview

**Docker Management:**
/docker - Docker system information
/containers - List all containers with status

**Alert Management:**
/alerts - View active alerts
/ack <fingerprint> - Acknowledge an alert
/silence <fingerprint> [min] - Silence alert notifications

**VM/Container Control:**
/start_vm <vmid> - Start a VM or container
/stop_vm <vmid> - Stop (requires confirmation)
/restart_vm <vmid> - Restart a VM or container
/confirm <id> - Confirm a destructive action

**Scheduled Reports:**
/daily_report - Generate daily system summary
/weekly_report - Generate weekly trends report
/schedule - View report schedule configuration
/schedule_enable <daily|weekly> - Enable a report
/schedule_disable <daily|weekly> - Disable a report

**Network Monitoring:**
/network - Comprehensive network status
/devices - List connected network devices
/bandwidth - Current bandwidth usage statistics

**Bot Management:**
/update - Pull latest code and restart
/help - Show this help message

**💬 Natural Language:**
Just send me a message like:
• "Show status of LXC 101"
• "List running Docker containers"
• "Check system resources"
        """

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - comprehensive system status"""
        if not self.is_authorized(update.effective_user.id):
            return

        status_msg = await update.message.reply_text("🔄 Gathering system status...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                proxmox_data = result.get('proxmox_node', '')
                proxmox_formatted = self.parse_proxmox_node_status(proxmox_data)

                docker_data = result.get('docker', '')
                docker_formatted = self.parse_docker_info(docker_data)

                uptime_delta = datetime.now() - self.start_time
                bot_uptime = self.format_uptime(int(uptime_delta.total_seconds()))

                # Get alert stats
                alert_stats = self.alert_manager.get_stats()
                alert_summary = ""
                if alert_stats['firing'] > 0:
                    alert_summary = f"\n\n🚨 **Alerts:** {alert_stats['firing']} active (🔴 {alert_stats['critical']} critical)"

                response = f"""📊 **System Status Report**
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

{proxmox_formatted}

{docker_formatted}

🤖 **Bot Status**
**Uptime:** {bot_uptime}
**Health:** 🟢 Operational{alert_summary}
                """

                await status_msg.edit_text(response, parse_mode='Markdown')
            else:
                await status_msg.edit_text(
                    f"❌ Error retrieving status: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in status command: {e}")
            await status_msg.edit_text(f"❌ Error: {str(e)}")

    async def uptime_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /uptime command"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            uptime_delta = datetime.now() - self.start_time
            bot_uptime = self.format_uptime(int(uptime_delta.total_seconds()))

            response = f"""⏱️ **Uptime Information**

🤖 **Bot Uptime:** {bot_uptime}
**Started:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}

Getting system uptime..."""

            msg = await update.message.reply_text(response, parse_mode='Markdown')

            result = await self.infrastructure_agent.monitor_resources()
            if result.get("success"):
                node_data = self.parse_json_response(result.get('proxmox_node', ''))
                if node_data and 'uptime' in node_data:
                    system_uptime = self.format_uptime(node_data['uptime'])
                    response += f"\n🖥️ **System Uptime:** {system_uptime}"
                    await msg.edit_text(response, parse_mode='Markdown')

        except Exception as e:
            self.logger.error(f"Error in uptime command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def node_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /node command - Proxmox node status"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🖥️ Checking Proxmox node...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                node_data = result.get('proxmox_node', '')
                formatted = self.parse_proxmox_node_status(node_data)
                await msg.edit_text(formatted, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in node command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def vms_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /vms command - list all VMs and containers"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🔄 Fetching VM and container list...")

        try:
            result = await self.infrastructure_agent.execute("List all VMs and containers with detailed status")

            if result.get("success"):
                vms_data = result.get("data_collected", {}).get("vms", "")
                formatted = self.parse_vm_list(vms_data)

                await msg.edit_text(formatted, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in vms command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def docker_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /docker command - Docker system info"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🐳 Checking Docker status...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                docker_data = result.get('docker', '')
                formatted = self.parse_docker_info(docker_data)
                await msg.edit_text(formatted, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in docker command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def containers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /containers command - list all Docker containers"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🐳 Listing Docker containers...")

        try:
            result = await self.infrastructure_agent.execute("List all Docker containers with status")

            if result.get("success"):
                containers_data = result.get("data_collected", {}).get("containers", "")
                formatted = self.parse_container_list(containers_data)

                await msg.edit_text(formatted, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in containers command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /monitor command - resource monitoring"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("📊 Monitoring resources...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                proxmox_data = result.get('proxmox_node', '')
                docker_data = result.get('docker', '')

                proxmox_formatted = self.parse_proxmox_node_status(proxmox_data)
                docker_formatted = self.parse_docker_info(docker_data)

                response = f"""📊 **Resource Monitoring**
🕐 {datetime.now().strftime('%H:%M:%S')}

{proxmox_formatted}

{docker_formatted}
                """

                await msg.edit_text(response, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in monitor command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def infra_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /infra command - infrastructure overview"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🏗️ Gathering infrastructure overview...")

        try:
            result = await self.infrastructure_agent.execute("Show comprehensive infrastructure overview")

            if result.get("success"):
                summary = result.get('summary', 'Infrastructure overview retrieved')

                response = f"""🏗️ **Infrastructure Overview**

{summary}

Use these commands for details:
/vms - VM and container details
/docker - Docker system info
/node - Proxmox node status
                """

                await msg.edit_text(response, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error in infra command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /update command - pull latest code and restart"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🔄 Updating bot code...")

        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd="/root/homelab-agents",
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                update_output = result.stdout.strip()

                if "Already up to date" in update_output:
                    await msg.edit_text("✅ Bot is already up to date!")
                else:
                    await msg.edit_text(f"""✅ **Update Complete**

{update_output}

🔄 Restarting bot in 3 seconds...""")

                    await asyncio.sleep(3)

                    subprocess.run(
                        ["systemctl", "restart", "homelab-telegram-bot"],
                        timeout=10
                    )
            else:
                await msg.edit_text(f"❌ Update failed:\n```\n{result.stderr}\n```", parse_mode='Markdown')

        except Exception as e:
            self.logger.error(f"Error in update command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages"""
        if not self.is_authorized(update.effective_user.id):
            return

        message_text = update.message.text
        self.logger.info(f"Received message: {message_text}")

        msg = await update.message.reply_text("🤔 Processing your request...")

        try:
            result = await self.infrastructure_agent.execute(message_text)

            if result.get("success"):
                summary = result.get('summary', 'Task completed successfully')
                response = f"✅ {summary}"

                if result.get("data_collected"):
                    response += "\n\n📋 **Results:**"
                    for key, value in result["data_collected"].items():
                        if key == "vms":
                            formatted = self.parse_vm_list(value)
                            response += f"\n\n{formatted}"
                        elif key == "containers":
                            formatted = self.parse_container_list(value)
                            response += f"\n\n{formatted}"
                        elif key == "node_status":
                            formatted = self.parse_proxmox_node_status(value)
                            response += f"\n\n{formatted}"
                        else:
                            response += f"\n\n**{key.title()}:**\n{self._format_text_data(value)}"

                await msg.edit_text(response, parse_mode='Markdown')
            else:
                await msg.edit_text(
                    f"❌ Error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await msg.edit_text(f"❌ Error processing request: {str(e)}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        self.logger.error(f"Update {update} caused error {context.error}")

    async def _run_daily_report(self, context):
        """Job queue callback for daily report"""
        try:
            await self.report_scheduler.run_daily_summary(
                self.infrastructure_agent,
                self.monitoring_agent,
                self.allowed_users
            )
        except Exception as e:
            self.logger.error(f"Error running scheduled daily report: {e}")

    async def _run_weekly_report(self, context):
        """Job queue callback for weekly report"""
        try:
            await self.report_scheduler.run_weekly_trends(
                self.infrastructure_agent,
                self.monitoring_agent,
                self.allowed_users
            )
        except Exception as e:
            self.logger.error(f"Error running scheduled weekly report: {e}")

    async def run_async(self):
        """Async run method with webhook server"""
        try:
            # Start webhook server
            await self.webhook_server.start()
            self.logger.info("Webhook server started on port 8001")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("uptime", self.uptime_command))
            self.application.add_handler(CommandHandler("node", self.node_command))
            self.application.add_handler(CommandHandler("vms", self.vms_command))
            self.application.add_handler(CommandHandler("docker", self.docker_command))
            self.application.add_handler(CommandHandler("containers", self.containers_command))
            self.application.add_handler(CommandHandler("monitor", self.monitor_command))
            self.application.add_handler(CommandHandler("infra", self.infra_command))
            self.application.add_handler(CommandHandler("update", self.update_command))
            
            # Alert commands (Phase A)
            self.application.add_handler(CommandHandler("alerts", self.alerts_command))
            self.application.add_handler(CommandHandler("ack", self.ack_command))
            self.application.add_handler(CommandHandler("silence", self.silence_command))
            
            # VM control commands (Phase B)
            self.application.add_handler(CommandHandler("start_vm", self.start_vm_command))
            self.application.add_handler(CommandHandler("stop_vm", self.stop_vm_command))
            self.application.add_handler(CommandHandler("restart_vm", self.restart_vm_command))
            self.application.add_handler(CommandHandler("confirm", self.confirm_command))

            # Scheduled reports commands (Phase D)
            self.application.add_handler(CommandHandler("daily_report", self.daily_report_command))
            self.application.add_handler(CommandHandler("weekly_report", self.weekly_report_command))
            self.application.add_handler(CommandHandler("schedule", self.schedule_command))
            self.application.add_handler(CommandHandler("schedule_enable", self.schedule_enable_command))
            self.application.add_handler(CommandHandler("schedule_disable", self.schedule_disable_command))

            # Network monitoring commands (Phase E)
            self.application.add_handler(CommandHandler("network", self.network_command))
            self.application.add_handler(CommandHandler("devices", self.devices_command))
            self.application.add_handler(CommandHandler("bandwidth", self.bandwidth_command))

            # Natural language handler
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            
            # Error handler
            self.application.add_error_handler(self.error_handler)
            
            # Initialize and start bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

            # Set up report scheduler callback
            async def send_report_message(chat_id, text, parse_mode):
                """Send report message via bot"""
                try:
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode
                    )
                except Exception as e:
                    self.logger.error(f"Failed to send report to {chat_id}: {e}")

            self.report_scheduler.send_message_callback = send_report_message

            # Schedule daily reports (8 AM UTC)
            if self.application.job_queue:
                from datetime import time
                self.application.job_queue.run_daily(
                    self._run_daily_report,
                    time=time(hour=8, minute=0),
                    name='daily_report'
                )
                self.logger.info("Daily report scheduled for 08:00 UTC")

                # Schedule weekly reports (Monday 9 AM UTC)
                self.application.job_queue.run_daily(
                    self._run_weekly_report,
                    days=(0,),  # Monday
                    time=time(hour=9, minute=0),
                    name='weekly_report'
                )
                self.logger.info("Weekly report scheduled for Monday 09:00 UTC")

            self.logger.info("Telegram bot is running with alert integration and scheduled reports...")

            # Keep running
            await asyncio.Event().wait()
            
        except Exception as e:
            self.logger.error(f"Error in bot run: {e}")
            raise
        finally:
            if self.webhook_server:
                await self.webhook_server.stop()

    def run(self):
        """Start the Telegram bot and webhook server"""
        self.logger.info("Starting Telegram bot with webhook server...")
        asyncio.run(self.run_async())


def main():
    """Main entry point"""
    # Start metrics server
    logger.info("Starting metrics server on port 8000...")
    start_metrics_server(port=8000)

    bot = TelegramBotInterface()
    bot.run()


if __name__ == "__main__":
    main()
