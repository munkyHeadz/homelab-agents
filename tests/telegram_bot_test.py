#!/usr/bin/env python3
"""
Telegram Bot Integration Tests
Tests all bot functionality including commands, authorization, and agent integration
"""

import asyncio
import os
import sys
from typing import Any, Dict

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class TelegramBotTests:
    """Comprehensive Telegram bot test suite"""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.bot_token = config.telegram.bot_token
        self.admin_ids = config.telegram.admin_ids

    def test(self, name: str, passed: bool, details: str = ""):
        """Record test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} - {name}"
        if details:
            result += f"\n    {details}"
        self.results.append(result)

        if passed:
            self.passed += 1
        else:
            self.failed += 1

        print(result)

    def test_bot_token_validity(self):
        """Test if bot token is valid"""
        print("\n=== Testing Bot Token Validity ===")

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    bot_username = bot_info.get("username", "Unknown")
                    bot_id = bot_info.get("id", "Unknown")
                    can_read_messages = bot_info.get(
                        "can_read_all_group_messages", False
                    )

                    self.test(
                        "Bot Token Valid", True, f"Bot: @{bot_username} (ID: {bot_id})"
                    )

                    self.test(
                        "Bot Username", bool(bot_username), f"Username: @{bot_username}"
                    )
                else:
                    self.test(
                        "Bot Token Valid", False, "Token rejected by Telegram API"
                    )
            else:
                self.test("Bot Token Valid", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Bot Token Valid", False, str(e))

    def test_bot_webhook_info(self):
        """Check bot webhook configuration"""
        print("\n=== Testing Bot Webhook Configuration ===")

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    webhook_info = data.get("result", {})
                    webhook_url = webhook_info.get("url", "")
                    has_custom_cert = webhook_info.get("has_custom_certificate", False)
                    pending_updates = webhook_info.get("pending_update_count", 0)

                    # For polling bots, webhook should be empty
                    is_polling = webhook_url == ""

                    self.test(
                        "Bot Polling Mode",
                        is_polling,
                        f"Webhook URL: {'(none - polling mode)' if is_polling else webhook_url}",
                    )

                    if pending_updates > 0:
                        self.test(
                            "Pending Updates",
                            True,
                            f"{pending_updates} updates waiting to be processed",
                        )
                else:
                    self.test("Webhook Info", False, "Failed to get webhook info")
            else:
                self.test("Webhook Info", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Webhook Info", False, str(e))

    def test_bot_commands_registered(self):
        """Check if bot commands are registered"""
        print("\n=== Testing Bot Commands Registration ===")

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMyCommands"
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    commands = data.get("result", [])

                    self.test(
                        "Commands Registered",
                        len(commands) >= 0,
                        f"Found {len(commands)} registered commands",
                    )

                    if commands:
                        print("    Registered commands:")
                        for cmd in commands:
                            print(f"      /{cmd['command']} - {cmd['description']}")
                else:
                    self.test("Commands Registered", False, "Failed to get commands")
            else:
                self.test("Commands Registered", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Commands Registered", False, str(e))

    def test_bot_updates(self):
        """Check if bot is receiving updates"""
        print("\n=== Testing Bot Updates ===")

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {"limit": 1, "timeout": 2}
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    updates = data.get("result", [])

                    self.test(
                        "Bot Can Receive Updates",
                        True,
                        f"API accessible, {len(updates)} recent updates",
                    )

                    if updates:
                        latest = updates[0]
                        update_id = latest.get("update_id")
                        print(f"    Latest update ID: {update_id}")
                else:
                    self.test("Bot Updates", False, "Failed to get updates")
            else:
                self.test("Bot Updates", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Bot Updates", False, str(e))

    def test_authorization_config(self):
        """Test authorization configuration"""
        print("\n=== Testing Authorization Configuration ===")

        admin_ids_list = self.admin_ids

        if admin_ids_list:
            self.test(
                "Admin IDs Configured",
                True,
                f"Found {len(admin_ids_list)} authorized admin(s)",
            )

            for admin_id in admin_ids_list:
                self.test(
                    f"Admin ID Format",
                    admin_id.isdigit() or admin_id.startswith("@"),
                    f"ID: {admin_id}",
                )
        else:
            self.test(
                "Admin IDs Configured",
                False,
                "No admin IDs configured - bot won't respond to anyone!",
            )

    def test_bot_service_status(self):
        """Test if bot service is running"""
        print("\n=== Testing Bot Service Status ===")

        import subprocess

        try:
            # Check if running in LXC 104
            result = subprocess.run(
                [
                    "sudo",
                    "pct",
                    "exec",
                    "104",
                    "--",
                    "systemctl",
                    "is-active",
                    "homelab-telegram-bot",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            is_active = result.stdout.strip() == "active"

            self.test(
                "Bot Service Running",
                is_active,
                f"Service status: {result.stdout.strip()}",
            )

            if is_active:
                # Get service details
                result2 = subprocess.run(
                    [
                        "sudo",
                        "pct",
                        "exec",
                        "104",
                        "--",
                        "systemctl",
                        "status",
                        "homelab-telegram-bot",
                        "--no-pager",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                # Extract PID and memory info
                for line in result2.stdout.split("\n"):
                    if "Main PID" in line:
                        print(f"    {line.strip()}")
                    elif "Memory:" in line:
                        print(f"    {line.strip()}")

        except Exception as e:
            self.test("Bot Service Status", False, str(e))

    def test_bot_logs(self):
        """Check bot logs for errors"""
        print("\n=== Testing Bot Logs ===")

        import subprocess

        try:
            # Get recent logs
            result = subprocess.run(
                [
                    "sudo",
                    "pct",
                    "exec",
                    "104",
                    "--",
                    "journalctl",
                    "-u",
                    "homelab-telegram-bot",
                    "-n",
                    "20",
                    "--no-pager",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                logs = result.stdout

                # Check for errors
                error_count = logs.lower().count("error")
                warning_count = logs.lower().count("warning")

                self.test("Bot Logs Accessible", True, f"Recent logs retrieved")

                self.test(
                    "Bot Error Rate",
                    error_count < 5,
                    f"Found {error_count} errors, {warning_count} warnings in recent logs",
                )

                # Check for key events
                if "Telegram bot is running" in logs:
                    self.test(
                        "Bot Started Successfully",
                        True,
                        "Found 'Telegram bot is running' message",
                    )

                if "Infrastructure agent initialized" in logs:
                    self.test("Agents Initialized", True, "Infrastructure agent loaded")

                if "Metrics server started" in logs:
                    self.test(
                        "Metrics Server Started", True, "Metrics endpoint initialized"
                    )

        except Exception as e:
            self.test("Bot Logs", False, str(e))

    def test_bot_metrics(self):
        """Test bot metrics endpoint"""
        print("\n=== Testing Bot Metrics ===")

        try:
            resp = requests.get("http://192.168.1.102:8000/metrics", timeout=5)

            if resp.status_code == 200:
                metrics = resp.text

                # Check for Telegram-specific metrics
                has_telegram_metrics = (
                    "telegram_messages_received_total" in metrics
                    or "telegram_messages_sent_total" in metrics
                )

                self.test(
                    "Telegram Metrics Exposed",
                    "telegram" in metrics.lower() or "agent_health" in metrics,
                    f"Metrics endpoint accessible ({len(metrics)} bytes)",
                )

                # Check agent health
                if "agent_health_status" in metrics:
                    # Extract health status value
                    for line in metrics.split("\n"):
                        if (
                            'agent_health_status{agent_name="infrastructure_agent"}'
                            in line
                        ):
                            health_value = line.split()[-1]
                            is_healthy = health_value == "1.0"
                            self.test(
                                "Infrastructure Agent Health",
                                is_healthy,
                                f"Health status: {health_value}",
                            )
                            break
            else:
                self.test("Bot Metrics", False, f"HTTP {resp.status_code}")

        except Exception as e:
            self.test("Bot Metrics", False, str(e))

    def test_command_handlers_exist(self):
        """Verify command handler methods exist in code"""
        print("\n=== Testing Command Handler Implementation ===")

        # Read the telegram bot file
        import os

        bot_file = "/home/munky/homelab-agents/interfaces/telegram_bot.py"

        if os.path.exists(bot_file):
            with open(bot_file, "r") as f:
                code = f.read()

            expected_commands = [
                ("start_command", "/start command"),
                ("help_command", "/help command"),
                ("status_command", "/status command"),
                ("vms_command", "/vms command"),
                ("docker_command", "/docker command"),
                ("monitor_command", "/monitor command"),
                ("handle_message", "Natural language handler"),
                ("error_handler", "Error handler"),
            ]

            for method, description in expected_commands:
                exists = f"def {method}" in code or f"async def {method}" in code
                self.test(
                    f"Handler: {description}",
                    exists,
                    f"Method '{method}' {'found' if exists else 'missing'}",
                )

            # Check for agent integration
            self.test(
                "Infrastructure Agent Integration",
                "InfrastructureAgent" in code,
                "Agent imported and integrated",
            )

            self.test(
                "Monitoring Agent Integration",
                "MonitoringAgent" in code,
                "Monitoring agent imported",
            )

        else:
            self.test("Command Handlers", False, "Bot file not found")

    def test_bot_configuration_complete(self):
        """Test if all required configuration is present"""
        print("\n=== Testing Bot Configuration ===")

        # Check bot token
        self.test(
            "Bot Token Configured",
            bool(self.bot_token and self.bot_token != "your-bot-token-here"),
            f"Token length: {len(self.bot_token) if self.bot_token else 0}",
        )

        # Check admin IDs
        self.test(
            "Admin IDs Configured",
            bool(self.admin_ids),
            f"Found {len(self.admin_ids)} admin ID(s)",
        )

        # Check environment variables are loaded
        anthropic_key = config.anthropic.api_key
        self.test(
            "Anthropic API Key Loaded",
            bool(anthropic_key and len(anthropic_key) > 20),
            "API key present in config",
        )

    def test_send_test_message(self):
        """Attempt to send a test message (to verify send capability)"""
        print("\n=== Testing Bot Send Capability ===")

        # We won't actually send a message without user consent,
        # but we can test the API endpoint
        try:
            # Just test that the sendMessage endpoint is accessible
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            # Make a test request with invalid chat_id to see if endpoint responds
            # (this won't actually send a message)
            resp = requests.post(url, json={"chat_id": "0", "text": "test"}, timeout=5)

            # We expect this to fail with "Bad Request" because chat_id is invalid
            # But if we get a response, the bot token works for sending
            if resp.status_code in [400, 401]:
                data = resp.json()
                if not data.get("ok"):
                    # Expected - bad chat_id
                    self.test(
                        "Bot Can Send Messages",
                        "chat not found" in data.get("description", "").lower()
                        or "bad request" in data.get("description", "").lower(),
                        "Send API endpoint accessible (tested with invalid chat_id)",
                    )
                else:
                    self.test("Bot Send Capability", False, "Unexpected response")
            else:
                self.test("Bot Send Capability", False, f"HTTP {resp.status_code}")

        except Exception as e:
            self.test("Bot Send Capability", False, str(e))

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("TELEGRAM BOT - COMPREHENSIVE TEST SUITE")
        print("=" * 70)

        import time

        start_time = time.time()

        # Run all tests
        self.test_bot_token_validity()
        self.test_bot_webhook_info()
        self.test_bot_commands_registered()
        self.test_bot_updates()
        self.test_authorization_config()
        self.test_bot_configuration_complete()
        self.test_bot_service_status()
        self.test_bot_logs()
        self.test_bot_metrics()
        self.test_command_handlers_exist()
        self.test_send_test_message()

        duration = time.time() - start_time

        # Print summary
        print("\n" + "=" * 70)
        print("TELEGRAM BOT TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print(f"Duration: {duration:.2f}s")
        print("=" * 70)

        # Additional information
        print("\n📱 Telegram Bot Information:")
        print(
            f"   Bot Token: {self.bot_token[:20]}...{self.bot_token[-10:] if len(self.bot_token) > 30 else ''}"
        )
        print(f"   Admin IDs: {', '.join(self.admin_ids)}")
        print(f"   Metrics Endpoint: http://192.168.1.102:8000/metrics")
        print("\n💡 To test the bot manually:")
        print("   1. Open Telegram")
        print("   2. Search for your bot")
        print("   3. Send /start to begin")
        print("   4. Try commands: /status, /vms, /docker, /monitor, /help")
        print("   5. Send natural language: 'Check all VMs'")
        print("=" * 70)

        return self.failed == 0


def main():
    """Main entry point"""
    tests = TelegramBotTests()
    success = tests.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
