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
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.token = config.telegram.bot_token
        self.allowed_users = config.telegram.admin_ids
        self.start_time = datetime.now()

        # Initialize agents
        self.infrastructure_agent = InfrastructureAgent()
        self.monitoring_agent = MonitoringAgent()

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
            # Run git pull
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

                    # Give time for message to be sent
                    await asyncio.sleep(3)

                    # Restart via systemd
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

    def run(self):
        """Start the Telegram bot"""
        self.logger.info("Starting Telegram bot...")

        # Create application
        application = Application.builder().token(self.token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("uptime", self.uptime_command))
        application.add_handler(CommandHandler("node", self.node_command))
        application.add_handler(CommandHandler("vms", self.vms_command))
        application.add_handler(CommandHandler("docker", self.docker_command))
        application.add_handler(CommandHandler("containers", self.containers_command))
        application.add_handler(CommandHandler("monitor", self.monitor_command))
        application.add_handler(CommandHandler("infra", self.infra_command))
        application.add_handler(CommandHandler("update", self.update_command))

        # Add message handler for natural language
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Add error handler
        application.add_error_handler(self.error_handler)

        # Start bot
        self.logger.info("Telegram bot is running...")
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
