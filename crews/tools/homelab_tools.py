"""Custom tools for homelab agents to interact with infrastructure."""

import os
from typing import Optional

import docker
from crewai.tools import tool
from dotenv import load_dotenv
from prometheus_api_client import PrometheusConnect
from proxmoxer import ProxmoxAPI

# Import AdGuard tools
from crews.tools.adguard_tools import (check_adguard_status,
                                       check_blocklist_status,
                                       get_adguard_protection_summary,
                                       get_dns_query_stats,
                                       monitor_dns_clients)
# Import Alertmanager tools
from crews.tools.alertmanager_tools import (check_alert_routing,
                                            create_alert_silence,
                                            delete_alert_silence,
                                            get_alertmanager_status,
                                            list_active_alerts,
                                            list_alert_silences)
# Import Cloudflare tools
from crews.tools.cloudflare_tools import (check_security_events,
                                          check_zone_health,
                                          get_cloudflare_analytics,
                                          get_cloudflare_status,
                                          list_cloudflare_zones,
                                          monitor_dns_records)
# Import expanded Docker tools
from crews.tools.docker_tools import (check_docker_system_health,
                                      check_docker_volumes,
                                      get_container_resource_usage,
                                      inspect_docker_network,
                                      list_docker_images, prune_docker_images,
                                      update_docker_resources)
# Import Grafana tools
from crews.tools.grafana_tools import (add_annotation, create_snapshot,
                                       get_dashboard, get_grafana_status,
                                       list_dashboards, list_datasources)
# Import Home Assistant tools
from crews.tools.homeassistant_tools import (check_automation_status,
                                             check_homeassistant_status,
                                             get_entity_history,
                                             get_entity_state,
                                             get_homeassistant_summary,
                                             list_homeassistant_entities)
# Import PostgreSQL tools
from crews.tools.postgres_tools import (analyze_slow_queries,
                                        check_database_locks,
                                        check_database_sizes,
                                        check_index_health,
                                        check_postgres_health,
                                        check_replication_status,
                                        check_specific_database,
                                        check_table_bloat,
                                        clear_postgres_connections,
                                        monitor_database_connections,
                                        monitor_vacuum_status,
                                        query_database_performance,
                                        vacuum_postgres_table)
# Import expanded Prometheus tools
from crews.tools.prometheus_tools import (check_prometheus_rules,
                                          check_prometheus_targets,
                                          check_prometheus_tsdb,
                                          get_prometheus_alerts,
                                          get_prometheus_config_status,
                                          get_prometheus_runtime_info)
# Import expanded Proxmox tools
from crews.tools.proxmox_tools import (check_lxc_logs, check_lxc_network,
                                       check_lxc_snapshots,
                                       check_proxmox_node_health,
                                       check_proxmox_vm_status,
                                       create_lxc_snapshot, get_lxc_config,
                                       get_lxc_resource_usage,
                                       get_proxmox_cluster_status,
                                       get_proxmox_storage_status,
                                       get_proxmox_system_summary,
                                       list_lxc_containers, list_proxmox_vms,
                                       restart_postgres_service,
                                       update_lxc_resources)
# Import Tailscale tools
from crews.tools.tailscale_tools import (check_device_connectivity,
                                         get_critical_infrastructure_status,
                                         list_tailscale_devices,
                                         monitor_vpn_health)
# Import UniFi tools
from crews.tools.unifi_tools import (check_ap_health, check_wan_connectivity,
                                     get_network_performance,
                                     list_unifi_devices,
                                     monitor_network_clients,
                                     monitor_switch_ports)

# Load environment variables
load_dotenv()

# Initialize clients
prom = PrometheusConnect(url="http://100.67.169.111:9090", disable_ssl=True)
docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")


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
        logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
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
            os.getenv("PROXMOX_HOST"),
            user="root@pam",
            token_name="terraform",
            token_value=os.getenv("PROXMOX_TOKEN_SECRET"),
            verify_ssl=False,
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
            os.getenv("PROXMOX_HOST"),
            user="root@pam",
            token_name="terraform",
            token_value=os.getenv("PROXMOX_TOKEN_SECRET"),
            verify_ssl=False,
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
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return "✓ Telegram notification sent successfully"
    except Exception as e:
        return f"✗ Error sending Telegram notification: {str(e)}"
