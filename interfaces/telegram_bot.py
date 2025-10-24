#!/usr/bin/env python3
"""
Telegram Bot Interface for Homelab Agent System

Provides a Telegram bot interface to interact with the autonomous agent system.
Allows users to:
- Check system status
- Execute infrastructure commands
- Monitor resources
- Get alerts and notifications
- Automatic updates
"""

import asyncio
import os
import json
import re
import subprocess
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.infrastructure_agent import InfrastructureAgent
from agents.monitoring_agent import MonitoringAgent
from agents.autonomous_health_agent import AutonomousHealthAgent
from shared.config import config
from shared.logging import get_logger
from shared.metrics import start_metrics_server, get_metrics_collector, telegram_messages_received_total, telegram_messages_sent_total

logger = get_logger(__name__)


class TelegramBotInterface:
    """
    Telegram bot interface for agent system

    Integrates with:
    - Infrastructure Agent: VM/Container management
    - Monitoring Agent: Resource monitoring and alerts
    - Autonomous Health Agent: Self-healing and monitoring
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.token = config.telegram.bot_token
        self.allowed_users = config.telegram.admin_ids
        self.start_time = datetime.now()

        # Application instance (set when bot starts)
        self.application = None

        # Initialize agents
        self.infrastructure_agent = InfrastructureAgent()
        self.monitoring_agent = MonitoringAgent()

        # Initialize autonomous health agent with this bot as notifier
        self.health_agent = AutonomousHealthAgent(telegram_notifier=self)

        # Store scheduled health reports job
        self.health_monitoring_task = None

        self.logger.info("Telegram bot interface initialized")

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot"""
        return str(user_id) in self.allowed_users

    def parse_json_response(self, text: str) -> Optional[Dict]:
        """Extract and parse JSON from MCP response"""
        try:
            # Try direct JSON parse
            return json.loads(text)
        except:
            # Try to find JSON in text
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

        # Visual indicator
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
                # Try to extract key info from text
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
                    status_emoji = "🟢" if item.get('status') == 'running' else "🔴"
                    name = item.get('name', f"ID {item.get('vmid', 'Unknown')}")
                    vmid = item.get('vmid', '?')
                    mem = self.format_bytes(item.get('mem', 0))
                    cpu = item.get('cpu', 0) * 100

                    line = f"{status_emoji} **{vmid}** - {name}\n  └ CPU: {cpu:.1f}% | Mem: {mem}"

                    if item.get('type') == 'lxc':
                        lxc_containers.append(line)
                    else:
                        vms.append(line)

                result = "📦 **LXC Containers**\n" + "\n".join(lxc_containers) if lxc_containers else ""
                if vms:
                    result += "\n\n🖥️ **Virtual Machines**\n" + "\n".join(vms)

                return result if result else "No VMs or containers found"
            else:
                return self._format_text_data(raw_data)
        except Exception as e:
            self.logger.error(f"Error parsing VM list: {e}")
            return raw_data[:500]

    def parse_container_list(self, raw_data: str) -> str:
        """Parse and format Docker container list"""
        try:
            data = self.parse_json_response(raw_data)
            if isinstance(data, list):
                if not data:
                    return "No containers found"

                result = "🐳 **Docker Containers**\n\n"
                for container in data:
                    status = container.get('State', 'unknown')
                    status_emoji = "🟢" if status == 'running' else "🔴"
                    name = container.get('Names', ['Unknown'])[0].lstrip('/')
                    image = container.get('Image', 'Unknown')

                    result += f"{status_emoji} **{name}**\n"
                    result += f"  └ Image: {image}\n"
                    result += f"  └ Status: {container.get('Status', 'Unknown')}\n\n"

                return result
            else:
                return self._format_text_data(raw_data)
        except Exception as e:
            self.logger.error(f"Error parsing container list: {e}")
            return raw_data[:500]

    def _format_text_data(self, text: str) -> str:
        """Format plain text data for better readability"""
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n', '\n', text)
        # Limit length
        if len(text) > 1000:
            text = text[:1000] + "\n\n... (truncated)"
        return text

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id

        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ Unauthorized. This bot is for authorized users only."
            )
            self.logger.warning(f"Unauthorized access attempt from user {user_id}")
            return

        welcome_message = """🤖 **Homelab Agent System v2.5**

Welcome! I'm your autonomous homelab management assistant with self-healing capabilities.

**📊 System Commands:**
/status - Complete system overview
/uptime - Bot and system uptime
/monitor - Resource monitoring
/menu - Interactive control menu

**🖥️ Proxmox Commands:**
/node - Proxmox node status
/vms - List all VMs and containers
/start_vm <id> - Start VM/Container
/stop_vm <id> - Stop VM/Container
/restart_vm <id> - Restart VM/Container

**🐳 Docker Commands:**
/docker - Docker system info
/containers - List all containers
/restart_container <name> - Restart container
/stop_container <name> - Stop container

**🏥 Auto-Healing:**
/health - System health report
/enable_autohealing - Enable auto-healing
/disable_autohealing - Disable auto-healing

**💾 Backup:**
/backup - Show backup status
/backup <vmid> - Status for specific VM

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
/menu - Interactive control menu 🎮

**Proxmox Management:**
/node - Detailed node status
/vms - List all VMs and LXC containers
/start_vm <id> - Start a VM or container
/stop_vm <id> - Stop a VM or container
/restart_vm <id> - Restart a VM or container
/infra - Infrastructure overview

**Docker Management:**
/docker - Docker system information
/containers - List all containers with status
/restart_container <name> - Restart Docker container
/stop_container <name> - Stop Docker container

**🏥 Auto-Healing System:**
/health - View system health report
/enable_autohealing - Start autonomous monitoring
/disable_autohealing - Stop autonomous monitoring

The auto-healing system will:
• Monitor infrastructure every 60 seconds
• Auto-fix low-risk issues (restart containers, clean disk)
• Request approval for risky actions (VM reboots, etc.)
• Learn from successful fixes

**💾 Backup Status:**
/backup - Show recent backup status for all VMs
/backup <vmid> - Show backup status for specific VM

**Bot Management:**
/update - Pull latest code and restart
/help - Show this help message

**💬 Natural Language:**
Just send me a message like:
• "Show status of LXC 101"
• "List running Docker containers"
• "Restart nginx-proxy container"
• "Check system resources"
        """

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - comprehensive system status"""
        if not self.is_authorized(update.effective_user.id):
            return

        status_msg = await update.message.reply_text("🔄 Gathering system status...")

        try:
            # Get infrastructure status
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                # Parse Proxmox node data
                proxmox_data = result.get('proxmox_node', '')
                proxmox_formatted = self.parse_proxmox_node_status(proxmox_data)

                # Parse Docker data
                docker_data = result.get('docker', '')
                docker_formatted = self.parse_docker_info(docker_data)

                # Bot uptime
                uptime_delta = datetime.now() - self.start_time
                bot_uptime = self.format_uptime(int(uptime_delta.total_seconds()))

                response = f"""📊 **System Status Report**
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

{proxmox_formatted}

{docker_formatted}

🤖 **Bot Status**
**Uptime:** {bot_uptime}
**Health:** 🟢 Operational
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

            # Get system uptime from Proxmox
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
                # Try to get formatted data from data_collected
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
                # Parse both Proxmox and Docker data
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
            # Get comprehensive infrastructure data
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
            repo_dir = "/root/homelab-agents"

            # Step 1: Fetch from remote
            await msg.edit_text("🔄 Fetching updates from GitHub...")
            fetch_result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if fetch_result.returncode != 0:
                await msg.edit_text(f"❌ Fetch failed:\n```\n{fetch_result.stderr}\n```", parse_mode='Markdown')
                return

            # Step 2: Check current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            current_branch = branch_result.stdout.strip()

            # Step 3: Ensure we're on main branch
            if current_branch != "main":
                await msg.edit_text(f"🔄 Switching to main branch (currently on {current_branch})...")
                subprocess.run(
                    ["git", "checkout", "main"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                current_branch = "main"

            # Step 4: Set up tracking if not configured
            tracking_result = subprocess.run(
                ["git", "config", "--get", "branch.main.merge"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if tracking_result.returncode != 0:
                # No tracking set up, configure it
                await msg.edit_text("🔄 Setting up branch tracking...")
                subprocess.run(
                    ["git", "branch", "--set-upstream-to=origin/main", "main"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            # Step 5: Pull updates
            await msg.edit_text("🔄 Pulling latest changes...")
            pull_result = subprocess.run(
                ["git", "pull"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if pull_result.returncode == 0:
                update_output = pull_result.stdout.strip()

                if "Already up to date" in update_output or "Already up-to-date" in update_output:
                    await msg.edit_text("✅ Bot is already up to date!")
                else:
                    # Get summary of changes
                    log_result = subprocess.run(
                        ["git", "log", "-1", "--oneline"],
                        cwd=repo_dir,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    latest_commit = log_result.stdout.strip()

                    await msg.edit_text(f"""✅ **Update Complete**

**Latest commit:**
{latest_commit}

🔄 Restarting bot in 3 seconds...""")

                    # Give time for message to be sent
                    await asyncio.sleep(3)

                    # Restart via systemd
                    subprocess.run(
                        ["systemctl", "restart", "homelab-telegram-bot"],
                        timeout=10
                    )
            else:
                error_msg = pull_result.stderr.strip()
                await msg.edit_text(f"❌ Update failed:\n```\n{error_msg}\n```", parse_mode='Markdown')

        except subprocess.TimeoutExpired:
            self.logger.error("Git command timeout in update")
            await msg.edit_text("❌ Update timed out. Please try again or check git status manually.")
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
            # Use infrastructure agent to process natural language request
            result = await self.infrastructure_agent.execute(message_text)

            if result.get("success"):
                summary = result.get('summary', 'Task completed successfully')
                response = f"✅ {summary}"

                # Add formatted data if available
                if result.get("data_collected"):
                    response += "\n\n📋 **Results:**"
                    for key, value in result["data_collected"].items():
                        # Try to format based on data type
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
                            # Generic text formatting
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

    # ========== Telegram Notifier Interface for Health Agent ==========

    async def send_message(self, text: str, parse_mode: str = 'Markdown'):
        """Send a message to all authorized users"""
        if self.application:
            for user_id in self.allowed_users:
                try:
                    await self.application.bot.send_message(
                        chat_id=int(user_id),
                        text=text,
                        parse_mode=parse_mode
                    )
                except Exception as e:
                    self.logger.error(f"Error sending message to {user_id}: {e}")

    async def send_approval_request(self, issue):
        """Send approval request with buttons to authorized users"""
        from agents.autonomous_health_agent import HealthStatus

        # Format severity emoji
        severity_emoji = {
            HealthStatus.CRITICAL: "🔴",
            HealthStatus.UNHEALTHY: "🟠",
            HealthStatus.DEGRADED: "🟡",
            HealthStatus.HEALTHY: "🟢"
        }

        message = f"""⚠️ **Action Approval Required**

**Component:** {issue.component}
**Issue:** {issue.description}
**Severity:** {severity_emoji.get(issue.severity, '⚪')} {issue.severity.value.upper()}
**Risk Level:** {issue.risk_level.value.upper()}

**Suggested Fix:**
{issue.suggested_fix}

**Metrics:**
```
{json.dumps(issue.metrics, indent=2)}
```

Should I proceed with this action?"""

        # Create approval buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{issue.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{issue.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if self.application:
            for user_id in self.allowed_users:
                try:
                    await self.application.bot.send_message(
                        chat_id=int(user_id),
                        text=message,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    self.logger.error(f"Error sending approval request to {user_id}: {e}")

    async def handle_approval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle approval button callbacks"""
        query = update.callback_query
        await query.answer()

        if not self.is_authorized(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized")
            return

        # Parse callback data
        action, approval_id = query.data.split("_", 1)

        approved = (action == "approve")

        # Handle approval
        self.health_agent.handle_approval_response(approval_id, approved)

        # Update message
        result = "✅ APPROVED" if approved else "❌ REJECTED"
        await query.edit_message_text(
            f"{query.message.text}\n\n**Decision:** {result} by {query.from_user.first_name}"
        )

    # ========== New VM/Container Control Commands ==========

    async def start_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_vm command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("Usage: /start_vm <vmid>\nExample: /start_vm 104")
            return

        try:
            vmid = int(context.args[0])
            msg = await update.message.reply_text(f"🔄 Starting VM/Container {vmid}...")

            result = await self.infrastructure_agent.execute(f"Start VM or container with ID {vmid}")

            if result.get("success"):
                await msg.edit_text(f"✅ Successfully started VM/Container {vmid}")
            else:
                await msg.edit_text(f"❌ Failed to start VM/Container {vmid}: {result.get('error', 'Unknown error')}")

        except ValueError:
            await update.message.reply_text("❌ Invalid VM ID. Must be a number.")
        except Exception as e:
            self.logger.error(f"Error in start_vm command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def stop_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_vm command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("Usage: /stop_vm <vmid>\nExample: /stop_vm 104")
            return

        try:
            vmid = int(context.args[0])
            msg = await update.message.reply_text(f"🛑 Stopping VM/Container {vmid}...")

            result = await self.infrastructure_agent.execute(f"Stop VM or container with ID {vmid}")

            if result.get("success"):
                await msg.edit_text(f"✅ Successfully stopped VM/Container {vmid}")
            else:
                await msg.edit_text(f"❌ Failed to stop VM/Container {vmid}: {result.get('error', 'Unknown error')}")

        except ValueError:
            await update.message.reply_text("❌ Invalid VM ID. Must be a number.")
        except Exception as e:
            self.logger.error(f"Error in stop_vm command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def restart_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /restart_vm command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("Usage: /restart_vm <vmid>\nExample: /restart_vm 104")
            return

        try:
            vmid = int(context.args[0])
            msg = await update.message.reply_text(f"🔄 Restarting VM/Container {vmid}...")

            result = await self.infrastructure_agent.execute(f"Restart VM or container with ID {vmid}")

            if result.get("success"):
                await msg.edit_text(f"✅ Successfully restarted VM/Container {vmid}")
            else:
                await msg.edit_text(f"❌ Failed to restart VM/Container {vmid}: {result.get('error', 'Unknown error')}")

        except ValueError:
            await update.message.reply_text("❌ Invalid VM ID. Must be a number.")
        except Exception as e:
            self.logger.error(f"Error in restart_vm command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def restart_container_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /restart_container command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("Usage: /restart_container <container_name>\nExample: /restart_container nginx-proxy")
            return

        try:
            container_name = context.args[0]
            msg = await update.message.reply_text(f"🔄 Restarting Docker container '{container_name}'...")

            result = await self.infrastructure_agent.execute(f"Restart Docker container named {container_name}")

            if result.get("success"):
                await msg.edit_text(f"✅ Successfully restarted container '{container_name}'")
            else:
                await msg.edit_text(f"❌ Failed to restart container '{container_name}': {result.get('error', 'Unknown error')}")

        except Exception as e:
            self.logger.error(f"Error in restart_container command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def stop_container_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_container command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("Usage: /stop_container <container_name>\nExample: /stop_container nginx-proxy")
            return

        try:
            container_name = context.args[0]
            msg = await update.message.reply_text(f"🛑 Stopping Docker container '{container_name}'...")

            result = await self.infrastructure_agent.execute(f"Stop Docker container named {container_name}")

            if result.get("success"):
                await msg.edit_text(f"✅ Successfully stopped container '{container_name}'")
            else:
                await msg.edit_text(f"❌ Failed to stop container '{container_name}': {result.get('error', 'Unknown error')}")

        except Exception as e:
            self.logger.error(f"Error in stop_container command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    # ========== Health Monitoring Commands ==========

    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /health command - show health report"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text("🏥 Generating health report...")

        try:
            report = await self.health_agent.generate_health_report()

            # Format the report
            response = f"""🏥 **System Health Report**
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

**Active Issues:** {report['active_issues']}
**Resolved Today:** {report['resolved_today']}
**Pending Approvals:** {report['pending_approvals']}

**Issues by Severity:**
🔴 Critical: {report['issues_by_severity']['critical']}
🟠 Unhealthy: {report['issues_by_severity']['unhealthy']}
🟡 Degraded: {report['issues_by_severity']['degraded']}
"""

            # Add active issues details
            if report['issues']:
                response += "\n**📋 Active Issues:**\n"
                for issue in report['issues'][:5]:  # Show first 5
                    response += f"\n• {issue['component']}: {issue['description']}"

            # Add recent resolutions
            if report['recent_resolutions']:
                response += "\n\n**✅ Recent Resolutions:**\n"
                for issue in report['recent_resolutions'][:3]:  # Show first 3
                    response += f"\n• {issue['component']}: {issue['description']}"

            await msg.edit_text(response, parse_mode='Markdown')

        except Exception as e:
            self.logger.error(f"Error in health command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def enable_autohealing_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /enable_autohealing command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if self.health_monitoring_task:
            await update.message.reply_text("✅ Auto-healing is already enabled!")
            return

        try:
            # Start health monitoring loop in background
            self.health_monitoring_task = asyncio.create_task(
                self.health_agent.run_monitoring_loop(interval=60)
            )

            await update.message.reply_text("""✅ **Auto-Healing Enabled**

The system will now:
• Monitor infrastructure every 60 seconds
• Auto-fix low-risk issues automatically
• Request approval for risky actions
• Send notifications to this chat

Use /health to view current status
Use /disable_autohealing to stop""")

            self.logger.info("Auto-healing enabled")

        except Exception as e:
            self.logger.error(f"Error enabling auto-healing: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def disable_autohealing_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /disable_autohealing command"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not self.health_monitoring_task:
            await update.message.reply_text("Auto-healing is not currently running")
            return

        try:
            # Cancel the monitoring task
            self.health_monitoring_task.cancel()
            self.health_monitoring_task = None

            await update.message.reply_text("🛑 Auto-healing disabled")
            self.logger.info("Auto-healing disabled")

        except Exception as e:
            self.logger.error(f"Error disabling auto-healing: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    # ========== Backup Status Command ==========

    async def backup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command - show backup status"""
        if not self.is_authorized(update.effective_user.id):
            return

        # Check if specific VM requested
        vmid = None
        if context.args and len(context.args) >= 1:
            try:
                vmid = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Invalid VM ID. Must be a number.")
                return

        msg = await update.message.reply_text("💾 Checking backup status...")

        try:
            if vmid:
                result = await self.infrastructure_agent.execute(f"Show backup status for VM {vmid}")
            else:
                result = await self.infrastructure_agent.execute("Show recent backup status for all VMs")

            if result.get("success"):
                summary = result.get('summary', 'Backup status retrieved')
                await msg.edit_text(f"💾 **Backup Status**\n\n{summary}", parse_mode='Markdown')
            else:
                await msg.edit_text(f"❌ Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            self.logger.error(f"Error in backup command: {e}")
            await msg.edit_text(f"❌ Error: {str(e)}")

    # ========== Interactive Menu Commands ==========

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - show interactive menu"""
        if not self.is_authorized(update.effective_user.id):
            return

        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="menu_status"),
                InlineKeyboardButton("🖥️ Node", callback_data="menu_node")
            ],
            [
                InlineKeyboardButton("📦 VMs", callback_data="menu_vms"),
                InlineKeyboardButton("🐳 Docker", callback_data="menu_docker")
            ],
            [
                InlineKeyboardButton("🏥 Health", callback_data="menu_health"),
                InlineKeyboardButton("💾 Backups", callback_data="menu_backup")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="menu_refresh")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🤖 **Homelab Control Menu**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu button callbacks"""
        query = update.callback_query
        await query.answer()

        if not self.is_authorized(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized")
            return

        action = query.data.replace("menu_", "")

        # Execute the corresponding command
        if action == "status":
            await self._execute_status_inline(query)
        elif action == "node":
            await self._execute_node_inline(query)
        elif action == "vms":
            await self._execute_vms_inline(query)
        elif action == "docker":
            await self._execute_docker_inline(query)
        elif action == "health":
            await self._execute_health_inline(query)
        elif action == "backup":
            await self._execute_backup_inline(query)
        elif action == "refresh":
            # Recreate menu
            keyboard = [
                [
                    InlineKeyboardButton("📊 Status", callback_data="menu_status"),
                    InlineKeyboardButton("🖥️ Node", callback_data="menu_node")
                ],
                [
                    InlineKeyboardButton("📦 VMs", callback_data="menu_vms"),
                    InlineKeyboardButton("🐳 Docker", callback_data="menu_docker")
                ],
                [
                    InlineKeyboardButton("🏥 Health", callback_data="menu_health"),
                    InlineKeyboardButton("💾 Backups", callback_data="menu_backup")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="menu_refresh")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🤖 **Homelab Control Menu**\n\nSelect an option:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def _execute_status_inline(self, query):
        """Execute status command inline"""
        await query.edit_message_text("🔄 Gathering system status...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                proxmox_data = result.get('proxmox_node', '')
                docker_data = result.get('docker', '')

                proxmox_formatted = self.parse_proxmox_node_status(proxmox_data)
                docker_formatted = self.parse_docker_info(docker_data)

                uptime_delta = datetime.now() - self.start_time
                bot_uptime = self.format_uptime(int(uptime_delta.total_seconds()))

                response = f"""📊 **System Status Report**
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

{proxmox_formatted}

{docker_formatted}

🤖 **Bot Status**
**Uptime:** {bot_uptime}
**Health:** 🟢 Operational
"""
                await query.edit_message_text(response, parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            self.logger.error(f"Error in status inline: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def _execute_node_inline(self, query):
        """Execute node command inline"""
        await query.edit_message_text("🖥️ Checking Proxmox node...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                node_data = result.get('proxmox_node', '')
                formatted = self.parse_proxmox_node_status(node_data)
                await query.edit_message_text(formatted, parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def _execute_vms_inline(self, query):
        """Execute vms command inline"""
        await query.edit_message_text("🔄 Fetching VM and container list...")

        try:
            result = await self.infrastructure_agent.execute("List all VMs and containers with detailed status")

            if result.get("success"):
                vms_data = result.get("data_collected", {}).get("vms", "")
                formatted = self.parse_vm_list(vms_data)
                await query.edit_message_text(formatted, parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def _execute_docker_inline(self, query):
        """Execute docker command inline"""
        await query.edit_message_text("🐳 Checking Docker status...")

        try:
            result = await self.infrastructure_agent.monitor_resources()

            if result.get("success"):
                docker_data = result.get('docker', '')
                formatted = self.parse_docker_info(docker_data)
                await query.edit_message_text(formatted, parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def _execute_health_inline(self, query):
        """Execute health command inline"""
        await query.edit_message_text("🏥 Generating health report...")

        try:
            report = await self.health_agent.generate_health_report()

            response = f"""🏥 **System Health Report**
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

**Active Issues:** {report['active_issues']}
**Resolved Today:** {report['resolved_today']}
**Pending Approvals:** {report['pending_approvals']}

**Issues by Severity:**
🔴 Critical: {report['issues_by_severity']['critical']}
🟠 Unhealthy: {report['issues_by_severity']['unhealthy']}
🟡 Degraded: {report['issues_by_severity']['degraded']}
"""

            if report['issues']:
                response += "\n**📋 Active Issues:**\n"
                for issue in report['issues'][:5]:
                    response += f"\n• {issue['component']}: {issue['description']}"

            await query.edit_message_text(response, parse_mode='Markdown')

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def _execute_backup_inline(self, query):
        """Execute backup command inline"""
        await query.edit_message_text("💾 Checking backup status...")

        try:
            result = await self.infrastructure_agent.execute("Show recent backup status for all VMs")

            if result.get("success"):
                summary = result.get('summary', 'Backup status retrieved')
                await query.edit_message_text(f"💾 **Backup Status**\n\n{summary}", parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    def run(self):
        """Start the Telegram bot"""
        self.logger.info("Starting Telegram bot...")

        # Create application
        application = Application.builder().token(self.token).build()

        # Store application instance for notifier interface
        self.application = application

        # Add basic command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("uptime", self.uptime_command))
        application.add_handler(CommandHandler("monitor", self.monitor_command))
        application.add_handler(CommandHandler("menu", self.menu_command))

        # Proxmox management handlers
        application.add_handler(CommandHandler("node", self.node_command))
        application.add_handler(CommandHandler("vms", self.vms_command))
        application.add_handler(CommandHandler("infra", self.infra_command))
        application.add_handler(CommandHandler("start_vm", self.start_vm_command))
        application.add_handler(CommandHandler("stop_vm", self.stop_vm_command))
        application.add_handler(CommandHandler("restart_vm", self.restart_vm_command))

        # Docker management handlers
        application.add_handler(CommandHandler("docker", self.docker_command))
        application.add_handler(CommandHandler("containers", self.containers_command))
        application.add_handler(CommandHandler("restart_container", self.restart_container_command))
        application.add_handler(CommandHandler("stop_container", self.stop_container_command))

        # Health monitoring handlers
        application.add_handler(CommandHandler("health", self.health_command))
        application.add_handler(CommandHandler("enable_autohealing", self.enable_autohealing_command))
        application.add_handler(CommandHandler("disable_autohealing", self.disable_autohealing_command))

        # Backup status handler
        application.add_handler(CommandHandler("backup", self.backup_command))

        # Bot management
        application.add_handler(CommandHandler("update", self.update_command))

        # Callback query handlers for interactive buttons
        application.add_handler(CallbackQueryHandler(self.handle_approval_callback, pattern=r"^(approve|reject)_"))
        application.add_handler(CallbackQueryHandler(self.handle_menu_callback, pattern=r"^menu_"))

        # Add message handler for natural language
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Add error handler
        application.add_error_handler(self.error_handler)

        # Start bot
        self.logger.info("Telegram bot is running with all features enabled...")
        self.logger.info("Features: Auto-healing, VM/Container control, Interactive menus, Backup status")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    # Start metrics server
    logger.info("Starting metrics server on port 8000...")
    start_metrics_server(port=8000)

    bot = TelegramBotInterface()
    bot.run()


if __name__ == "__main__":
    main()
