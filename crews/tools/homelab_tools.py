"""Custom tools for homelab agents to interact with infrastructure."""

import os
import docker
from crewai.tools import tool
from prometheus_api_client import PrometheusConnect
from proxmoxer import ProxmoxAPI
from dotenv import load_dotenv
from typing import Optional

# Import Tailscale tools
from crews.tools.tailscale_tools import (
    list_tailscale_devices,
    check_device_connectivity,
    monitor_vpn_health,
    get_critical_infrastructure_status
)

# Import PostgreSQL tools
from crews.tools.postgres_tools import (
    check_postgres_health,
    query_database_performance,
    check_database_sizes,
    monitor_database_connections,
    check_specific_database
)

# Import UniFi tools
from crews.tools.unifi_tools import (
    list_unifi_devices,
    check_ap_health,
    monitor_network_clients,
    check_wan_connectivity,
    monitor_switch_ports,
    get_network_performance
)

# Import Cloudflare tools
from crews.tools.cloudflare_tools import (
    list_cloudflare_zones,
    check_zone_health,
    get_cloudflare_analytics,
    check_security_events,
    monitor_dns_records,
    get_cloudflare_status
)

# Import AdGuard tools
from crews.tools.adguard_tools import (
    check_adguard_status,
    get_dns_query_stats,
    check_blocklist_status,
    monitor_dns_clients,
    get_adguard_protection_summary
)

# Load environment variables
load_dotenv()

# Initialize clients
prom = PrometheusConnect(url="http://100.67.169.111:9090", disable_ssl=True)
docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')


@tool("Query Prometheus Metrics")
def query_prometheus(query: str) -> str:
    """
    Query Prometheus for metrics using PromQL syntax.

    Args:
        query: PromQL query string (e.g., 'up', 'container_cpu_usage_seconds_total')

    Returns:
        String representation of query results

    Examples:
        - "up" - Get all targets and their up/down status
        - "rate(container_cpu_usage_seconds_total[5m])" - CPU usage rate
        - "container_memory_usage_bytes" - Memory usage
    """
    try:
        result = prom.custom_query(query)
        if not result:
            return f"No data returned for query: {query}"
        return str(result)
    except Exception as e:
        return f"Error querying Prometheus: {str(e)}"


@tool("Check Docker Container Status")
def check_container_status(container_name: Optional[str] = None) -> str:
    """
    Check the status of Docker containers.

    Args:
        container_name: Optional name of specific container to check.
                       If None, returns status of all containers.

    Returns:
        String with container status information
    """
    try:
        if container_name:
            container = docker_client.containers.get(container_name)
            return f"Container {container_name}: Status={container.status}, State={container.attrs['State']}"
        else:
            containers = docker_client.containers.list(all=True)
            status_list = []
            for c in containers:
                status_list.append(f"{c.name}: {c.status}")
            return "\n".join(status_list) if status_list else "No containers found"
    except docker.errors.NotFound:
        return f"Container {container_name} not found"
    except Exception as e:
        return f"Error checking container status: {str(e)}"


@tool("Restart Docker Container")
def restart_container(container_name: str) -> str:
    """
    Restart a Docker container.

    Args:
        container_name: Name of the container to restart

    Returns:
        Success or error message
    """
    try:
        container = docker_client.containers.get(container_name)
        container.restart()
        return f"✓ Successfully restarted container: {container_name}"
    except docker.errors.NotFound:
        return f"✗ Container {container_name} not found"
    except Exception as e:
        return f"✗ Error restarting container: {str(e)}"


@tool("Check Container Logs")
def check_container_logs(container_name: str, tail: int = 50) -> str:
    """
    Retrieve logs from a Docker container.

    Args:
        container_name: Name of the container
        tail: Number of lines to retrieve from the end (default 50)

    Returns:
        Container logs as string
    """
    try:
        container = docker_client.containers.get(container_name)
        logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
        return f"Last {tail} lines from {container_name}:\n{logs}"
    except docker.errors.NotFound:
        return f"✗ Container {container_name} not found"
    except Exception as e:
        return f"✗ Error retrieving logs: {str(e)}"


@tool("Query Proxmox LXC Status")
def check_lxc_status(node: str = "homelab", vmid: Optional[int] = None) -> str:
    """
    Check the status of Proxmox LXC containers.

    Args:
        node: Proxmox node name (default: homelab)
        vmid: Optional specific LXC container ID. If None, returns all containers.

    Returns:
        LXC container status information
    """
    try:
        proxmox = ProxmoxAPI(
            os.getenv('PROXMOX_HOST'),
            user='root@pam',
            token_name='terraform',
            token_value=os.getenv('PROXMOX_TOKEN_SECRET'),
            verify_ssl=False
        )

        if vmid:
            status = proxmox.nodes(node).lxc(vmid).status.current.get()
            return f"LXC {vmid}: Status={status['status']}, CPU={status.get('cpu', 'N/A')}, Memory={status.get('mem', 'N/A')}/{status.get('maxmem', 'N/A')}"
        else:
            containers = proxmox.nodes(node).lxc.get()
            status_list = []
            for c in containers:
                status_list.append(f"LXC {c['vmid']} ({c['name']}): {c['status']}")
            return "\n".join(status_list) if status_list else "No LXC containers found"
    except Exception as e:
        return f"✗ Error checking LXC status: {str(e)}"


@tool("Restart Proxmox LXC Container")
def restart_lxc(node: str, vmid: int) -> str:
    """
    Restart a Proxmox LXC container.

    Args:
        node: Proxmox node name
        vmid: LXC container ID to restart

    Returns:
        Success or error message
    """
    try:
        proxmox = ProxmoxAPI(
            os.getenv('PROXMOX_HOST'),
            user='root@pam',
            token_name='terraform',
            token_value=os.getenv('PROXMOX_TOKEN_SECRET'),
            verify_ssl=False
        )

        proxmox.nodes(node).lxc(vmid).status.reboot.post()
        return f"✓ Successfully initiated restart of LXC {vmid} on node {node}"
    except Exception as e:
        return f"✗ Error restarting LXC: {str(e)}"


@tool("Send Telegram Notification")
def send_telegram(message: str) -> str:
    """
    Send a notification via Telegram bot.

    Args:
        message: Message to send

    Returns:
        Success or error message
    """
    import requests

    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return "✓ Telegram notification sent successfully"
    except Exception as e:
        return f"✗ Error sending Telegram notification: {str(e)}"
