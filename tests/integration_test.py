#!/usr/bin/env python3
"""
Comprehensive integration tests for homelab agent system
"""

import asyncio
import sys
import os
import requests
import time
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.infrastructure_agent import InfrastructureAgent
from agents.monitoring_agent import MonitoringAgent
from shared.logging import get_logger

logger = get_logger(__name__)


class IntegrationTests:
    """Comprehensive integration test suite"""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

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

    def test_prometheus_targets(self):
        """Test Prometheus target scraping"""
        print("\n=== Testing Prometheus Targets ===")
        try:
            resp = requests.get("http://192.168.1.107:9090/api/v1/targets", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                targets = data['data']['activeTargets']

                # Check each target
                for target in targets:
                    job = target['labels']['job']
                    health = target['health']
                    instance = target['labels']['instance']

                    self.test(
                        f"Prometheus Target: {job}",
                        health == "up",
                        f"Instance: {instance}, Health: {health}"
                    )
            else:
                self.test("Prometheus API", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Prometheus API", False, str(e))

    def test_metrics_endpoints(self):
        """Test metrics endpoint accessibility"""
        print("\n=== Testing Metrics Endpoints ===")

        endpoints = [
            ("Agent Metrics", "http://192.168.1.102:8000/metrics"),
            ("Docker Metrics", "http://192.168.1.101:9323/metrics"),
            ("Node Exporter", "http://192.168.1.107:9100/metrics"),
        ]

        for name, url in endpoints:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    # Check if we got Prometheus format
                    has_metrics = "# HELP" in resp.text or "# TYPE" in resp.text
                    self.test(
                        f"Metrics Endpoint: {name}",
                        has_metrics,
                        f"URL: {url}, Size: {len(resp.text)} bytes"
                    )
                else:
                    self.test(f"Metrics Endpoint: {name}", False, f"HTTP {resp.status_code}")
            except Exception as e:
                self.test(f"Metrics Endpoint: {name}", False, str(e))

    def test_custom_metrics(self):
        """Test custom agent metrics are being exposed"""
        print("\n=== Testing Custom Agent Metrics ===")

        try:
            resp = requests.get("http://192.168.1.102:8000/metrics", timeout=5)
            if resp.status_code == 200:
                metrics_text = resp.text

                expected_metrics = [
                    "agent_health_status",
                    "agent_tasks_total",
                    "agent_errors_total",
                    "mcp_connections_active",
                ]

                for metric in expected_metrics:
                    found = metric in metrics_text
                    self.test(
                        f"Custom Metric: {metric}",
                        found,
                        "Found in metrics output" if found else "Not found"
                    )
            else:
                self.test("Custom Metrics", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Custom Metrics", False, str(e))

    async def test_infrastructure_agent(self):
        """Test infrastructure agent execution"""
        print("\n=== Testing Infrastructure Agent ===")

        try:
            agent = InfrastructureAgent()
            self.test("Infrastructure Agent Init", True, "Agent initialized successfully")

            # Test resource monitoring
            result = await agent.monitor_resources()

            has_proxmox = "proxmox_node" in result
            has_docker = "docker" in result
            success = result.get("success", False)

            self.test(
                "Agent Resource Monitoring",
                success and has_proxmox and has_docker,
                f"Success: {success}, Proxmox data: {has_proxmox}, Docker data: {has_docker}"
            )

            # Test simple execution
            exec_result = await agent.execute("Get Docker system information")
            exec_success = exec_result.get("success", False)

            self.test(
                "Agent Task Execution",
                exec_success,
                f"Task completed: {exec_success}"
            )

        except Exception as e:
            self.test("Infrastructure Agent", False, str(e))

    async def test_monitoring_agent(self):
        """Test monitoring agent"""
        print("\n=== Testing Monitoring Agent ===")

        try:
            agent = MonitoringAgent()
            self.test("Monitoring Agent Init", True, "Agent initialized successfully")

            # Test health check
            health = await agent.check_system_health()
            health_success = health.get("success", False)

            self.test(
                "Monitoring Agent Health Check",
                health_success,
                f"Health check completed: {health_success}"
            )

        except Exception as e:
            self.test("Monitoring Agent", False, str(e))

    def test_prometheus_rules(self):
        """Test alert rules are loaded"""
        print("\n=== Testing Prometheus Alert Rules ===")

        try:
            resp = requests.get("http://192.168.1.107:9090/api/v1/rules", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                groups = data['data']['groups']

                total_rules = sum(len(g['rules']) for g in groups)

                self.test(
                    "Alert Rules Loaded",
                    total_rules > 0,
                    f"Total groups: {len(groups)}, Total rules: {total_rules}"
                )

                # Check specific rule groups exist
                group_names = [g['name'] for g in groups]
                expected_groups = ['infrastructure_alerts', 'agent_alerts', 'docker_alerts']

                for group in expected_groups:
                    found = group in group_names
                    self.test(
                        f"Alert Group: {group}",
                        found,
                        "Found" if found else "Not found"
                    )
            else:
                self.test("Alert Rules", False, f"HTTP {resp.status_code}")
        except Exception as e:
            self.test("Alert Rules", False, str(e))

    def test_grafana_access(self):
        """Test Grafana accessibility"""
        print("\n=== Testing Grafana Access ===")

        try:
            # Test Grafana is responding
            resp = requests.get("http://192.168.1.107:3000/api/health", timeout=5)
            if resp.status_code == 200:
                health = resp.json()
                self.test(
                    "Grafana Health",
                    health.get('database') == 'ok',
                    f"Database: {health.get('database')}"
                )
            else:
                self.test("Grafana Health", False, f"HTTP {resp.status_code}")

            # Test datasource
            resp = requests.get(
                "http://admin:admin@192.168.1.107:3000/api/datasources",
                timeout=5
            )
            if resp.status_code == 200:
                datasources = resp.json()
                has_prometheus = any(ds['type'] == 'prometheus' for ds in datasources)
                self.test(
                    "Grafana Prometheus Datasource",
                    has_prometheus,
                    f"Found {len(datasources)} datasources"
                )
            else:
                self.test("Grafana Datasources", False, f"HTTP {resp.status_code}")

        except Exception as e:
            self.test("Grafana Access", False, str(e))

    def test_lxc_services(self):
        """Test LXC service status"""
        print("\n=== Testing LXC Service Status ===")

        import subprocess

        services = [
            ("LXC 104 - Telegram Bot", "104", "homelab-telegram-bot"),
            ("LXC 107 - Prometheus", "107", "prometheus"),
            ("LXC 107 - Grafana", "107", "grafana-server"),
            ("LXC 107 - Node Exporter", "107", "node_exporter"),
            ("LXC 101 - Docker", "101", "docker"),
        ]

        for name, lxc_id, service in services:
            try:
                result = subprocess.run(
                    ["sudo", "pct", "exec", lxc_id, "--", "systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                is_active = result.stdout.strip() == "active"
                self.test(
                    f"Service: {name}",
                    is_active,
                    f"Status: {result.stdout.strip()}"
                )
            except Exception as e:
                self.test(f"Service: {name}", False, str(e))

    def test_system_connectivity(self):
        """Test network connectivity to all services"""
        print("\n=== Testing System Connectivity ===")

        services = [
            ("Proxmox API", "https://192.168.1.99:8006"),
            ("Docker API", "http://192.168.1.101:2375/_ping"),
            ("Prometheus", "http://192.168.1.107:9090/-/healthy"),
            ("Grafana", "http://192.168.1.107:3000/api/health"),
            ("Agent Metrics", "http://192.168.1.102:8000/metrics"),
        ]

        for name, url in services:
            try:
                resp = requests.get(url, timeout=5, verify=False)
                self.test(
                    f"Connectivity: {name}",
                    resp.status_code in [200, 201],
                    f"HTTP {resp.status_code}"
                )
            except Exception as e:
                self.test(f"Connectivity: {name}", False, str(e))

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("HOMELAB AGENT SYSTEM - INTEGRATION TEST SUITE")
        print("="*60)

        start_time = time.time()

        # Run sync tests
        self.test_system_connectivity()
        self.test_lxc_services()
        self.test_prometheus_targets()
        self.test_metrics_endpoints()
        self.test_custom_metrics()
        self.test_prometheus_rules()
        self.test_grafana_access()

        # Run async tests
        await self.test_infrastructure_agent()
        await self.test_monitoring_agent()

        duration = time.time() - start_time

        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print(f"Duration: {duration:.2f}s")
        print("="*60)

        return self.failed == 0


async def main():
    """Main entry point"""
    tests = IntegrationTests()
    success = await tests.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
