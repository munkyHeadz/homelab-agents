"""UniFi Network integration tools for monitoring WiFi, switches, and network devices."""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# UniFi Cloud API Configuration
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")
UNIFI_SITE_ID = os.getenv("UNIFI_SITE_ID")
UNIFI_USE_CLOUD_API = os.getenv("UNIFI_USE_CLOUD_API", "true").lower() == "true"

# UniFi Cloud API Base URL
UNIFI_CLOUD_API_BASE = "https://api.ui.com/ea"

# Local Controller Configuration (fallback)
UNIFI_HOST = os.getenv("UNIFI_HOST", "unifi.local")
UNIFI_PORT = int(os.getenv("UNIFI_PORT", 443))
UNIFI_USERNAME = os.getenv("UNIFI_USERNAME")
UNIFI_PASSWORD = os.getenv("UNIFI_PASSWORD")
UNIFI_SITE = os.getenv("UNIFI_SITE", "default")
UNIFI_VERIFY_SSL = os.getenv("UNIFI_VERIFY_SSL", "false").lower() == "true"


def _make_unifi_cloud_request(endpoint: str) -> dict:
    """Make authenticated request to UniFi Cloud API."""
    if not UNIFI_API_KEY or not UNIFI_SITE_ID:
        raise Exception("UniFi Cloud API key or Site ID not configured")

    url = f"{UNIFI_CLOUD_API_BASE}/{endpoint}"
    headers = {"X-API-KEY": UNIFI_API_KEY, "Content-Type": "application/json"}

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def _make_unifi_local_request(
    endpoint: str, method: str = "GET", data: dict = None
) -> dict:
    """Make authenticated request to local UniFi Controller."""
    if not UNIFI_USERNAME or not UNIFI_PASSWORD:
        raise Exception("UniFi local controller credentials not configured")

    base_url = f"https://{UNIFI_HOST}:{UNIFI_PORT}"

    # Create session and login
    session = requests.Session()
    session.verify = UNIFI_VERIFY_SSL

    # Login
    login_url = f"{base_url}/api/login"
    login_data = {"username": UNIFI_USERNAME, "password": UNIFI_PASSWORD}
    session.post(login_url, json=login_data, timeout=10)

    # Make request
    url = f"{base_url}/api/s/{UNIFI_SITE}/{endpoint}"
    if method == "GET":
        response = session.get(url, timeout=10)
    elif method == "POST":
        response = session.post(url, json=data, timeout=10)
    else:
        raise ValueError(f"Unsupported method: {method}")

    response.raise_for_status()
    return response.json()


@tool("List UniFi Network Devices")
def list_unifi_devices(device_type: Optional[str] = None) -> str:
    """
    List all UniFi network devices (APs, switches, gateways).

    Args:
        device_type: Optional filter - 'ap', 'switch', 'gateway', or None for all

    Returns:
        Formatted string with device information
    """
    try:
        if UNIFI_USE_CLOUD_API:
            # Cloud API endpoint
            data = _make_unifi_cloud_request(f"sites/{UNIFI_SITE_ID}/devices")
        else:
            # Local Controller API endpoint
            data = _make_unifi_local_request("stat/device")

        devices = data.get("data", [])

        if not devices:
            return "✗ No UniFi devices found"

        # Filter by type if specified
        if device_type:
            devices = [
                d for d in devices if d.get("type", "").lower() == device_type.lower()
            ]

        # Group devices by type
        aps = [d for d in devices if d.get("type") == "uap"]
        switches = [d for d in devices if d.get("type") == "usw"]
        gateways = [d for d in devices if d.get("type") in ["ugw", "udm"]]

        result = "=== UniFi Network Devices ===\n"
        result += f"Total Devices: {len(devices)}\n\n"

        if aps:
            result += f"📡 Access Points ({len(aps)}):\n"
            for ap in aps:
                name = ap.get("name", "Unknown")
                model = ap.get("model", "Unknown")
                state = ap.get("state", 0)
                status = "🟢 Online" if state == 1 else "🔴 Offline"
                clients = ap.get("num_sta", 0)
                uptime = ap.get("uptime", 0)
                uptime_str = f"{uptime // 3600}h" if uptime > 0 else "N/A"

                result += f"  • {name} ({model}): {status}\n"
                result += f"    Clients: {clients}, Uptime: {uptime_str}\n"

        if switches:
            result += f"\n🔌 Switches ({len(switches)}):\n"
            for switch in switches:
                name = switch.get("name", "Unknown")
                model = switch.get("model", "Unknown")
                state = switch.get("state", 0)
                status = "🟢 Online" if state == 1 else "🔴 Offline"
                ports = switch.get("port_table", [])
                active_ports = sum(1 for p in ports if p.get("up", False))

                result += f"  • {name} ({model}): {status}\n"
                result += f"    Active Ports: {active_ports}/{len(ports)}\n"

        if gateways:
            result += f"\n🌐 Gateways ({len(gateways)}):\n"
            for gw in gateways:
                name = gw.get("name", "Unknown")
                model = gw.get("model", "Unknown")
                state = gw.get("state", 0)
                status = "🟢 Online" if state == 1 else "🔴 Offline"
                wan_ip = gw.get("wan1", {}).get("ip", "N/A")

                result += f"  • {name} ({model}): {status}\n"
                result += f"    WAN IP: {wan_ip}\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "✗ UniFi API authentication failed - API key may be invalid or expired. Please regenerate from console.ui.com"
        return f"✗ UniFi API error: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        return f"✗ Failed to list UniFi devices: {str(e)}"


@tool("Check UniFi Access Point Health")
def check_ap_health(ap_name: Optional[str] = None) -> str:
    """
    Check health and status of UniFi Access Points.

    Args:
        ap_name: Optional specific AP name, or None for all APs

    Returns:
        Formatted string with AP health information
    """
    try:
        if UNIFI_USE_CLOUD_API:
            data = _make_unifi_cloud_request(f"sites/{UNIFI_SITE_ID}/devices")
        else:
            data = _make_unifi_local_request("stat/device")

        devices = data.get("data", [])
        aps = [d for d in devices if d.get("type") == "uap"]

        if ap_name:
            aps = [ap for ap in aps if ap.get("name", "").lower() == ap_name.lower()]

        if not aps:
            return (
                f"✗ No Access Points found{f' matching: {ap_name}' if ap_name else ''}"
            )

        result = "=== UniFi Access Point Health ===\n\n"

        online_count = sum(1 for ap in aps if ap.get("state") == 1)
        offline_count = len(aps) - online_count
        total_clients = sum(ap.get("num_sta", 0) for ap in aps)

        # Overall status
        if offline_count > 0:
            result += f"Overall Status: ⚠️ WARNING\n"
        else:
            result += f"Overall Status: ✅ HEALTHY\n"

        result += f"\n📊 Summary:\n"
        result += f"  Total APs: {len(aps)}\n"
        result += f"  Online: {online_count} (🟢)\n"
        result += f"  Offline: {offline_count} (🔴)\n"
        result += f"  Total Connected Clients: {total_clients}\n\n"

        # Details for each AP
        for ap in aps:
            name = ap.get("name", "Unknown")
            model = ap.get("model", "Unknown")
            state = ap.get("state", 0)
            status_icon = "🟢" if state == 1 else "🔴"
            status_text = "Online" if state == 1 else "Offline"

            result += f"{status_icon} {name} ({model}): {status_text}\n"

            if state == 1:
                # Online - show details
                clients = ap.get("num_sta", 0)
                uptime = ap.get("uptime", 0)
                uptime_hours = uptime // 3600

                # Radio stats
                radio_table = ap.get("radio_table", [])
                for radio in radio_table:
                    radio_name = radio.get("name", "")
                    channel = radio.get("channel", "N/A")
                    tx_power = radio.get("tx_power", "N/A")
                    utilization = radio.get("satisfaction", 0)

                    result += (
                        f"    {radio_name}: Channel {channel}, Power {tx_power}dBm, "
                    )
                    result += f"Utilization {utilization}%\n"

                result += f"    Clients: {clients}\n"
                result += f"    Uptime: {uptime_hours}h ({uptime // 86400}d)\n"

                # Check for issues
                if clients > 50:
                    result += f"    ⚠️ High client count\n"

                # Check satisfaction score
                satisfaction = ap.get("satisfaction", 100)
                if satisfaction < 80:
                    result += f"    ⚠️ Low satisfaction: {satisfaction}%\n"

            result += "\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return (
                "✗ UniFi API authentication failed - API key may be invalid or expired"
            )
        return f"✗ UniFi API error: {e.response.status_code}"
    except Exception as e:
        return f"✗ Failed to check AP health: {str(e)}"


@tool("Monitor UniFi Network Clients")
def monitor_network_clients(show_details: bool = False) -> str:
    """
    Monitor connected clients across the UniFi network.

    Args:
        show_details: If True, show individual client details

    Returns:
        Formatted string with client information
    """
    try:
        if UNIFI_USE_CLOUD_API:
            data = _make_unifi_cloud_request(f"sites/{UNIFI_SITE_ID}/clients")
        else:
            data = _make_unifi_local_request("stat/sta")

        clients = data.get("data", [])

        if not clients:
            return "✗ No clients currently connected"

        result = "=== UniFi Network Clients ===\n\n"
        result += f"Total Connected Clients: {len(clients)}\n\n"

        # Group by connection type
        wired = [c for c in clients if not c.get("is_wired", False)]
        wireless = [c for c in clients if c.get("is_wired", False)]

        result += f"📶 Wireless: {len(wireless)}\n"
        result += f"🔌 Wired: {len(wired)}\n\n"

        # Group wireless by AP
        if wireless:
            ap_clients = {}
            for client in wireless:
                ap_mac = client.get("ap_mac", "Unknown")
                if ap_mac not in ap_clients:
                    ap_clients[ap_mac] = []
                ap_clients[ap_mac].append(client)

            result += "Clients by Access Point:\n"
            for ap_mac, ap_client_list in sorted(
                ap_clients.items(), key=lambda x: len(x[1]), reverse=True
            ):
                # Try to get AP name
                ap_name = ap_client_list[0].get("ap_name", ap_mac[:8])
                result += f"  • {ap_name}: {len(ap_client_list)} clients\n"

        # Show high bandwidth clients
        sorted_clients = sorted(
            clients,
            key=lambda c: c.get("rx_bytes", 0) + c.get("tx_bytes", 0),
            reverse=True,
        )
        top_clients = sorted_clients[:5]

        if top_clients:
            result += "\n📊 Top Bandwidth Users:\n"
            for client in top_clients:
                hostname = client.get("hostname", client.get("mac", "Unknown"))
                rx_bytes = client.get("rx_bytes", 0)
                tx_bytes = client.get("tx_bytes", 0)
                total_mb = (rx_bytes + tx_bytes) / 1024 / 1024

                result += f"  • {hostname}: {total_mb:.1f} MB\n"

        if show_details:
            result += "\n📋 Client Details:\n"
            for client in clients[:20]:  # Limit to first 20
                hostname = client.get("hostname", "Unknown")
                mac = client.get("mac", "Unknown")
                ip = client.get("ip", "N/A")
                connection = "WiFi" if not client.get("is_wired") else "Wired"

                result += f"  • {hostname} ({ip}): {connection}\n"
                result += f"    MAC: {mac}\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return (
                "✗ UniFi API authentication failed - API key may be invalid or expired"
            )
        return f"✗ UniFi API error: {e.response.status_code}"
    except Exception as e:
        return f"✗ Failed to monitor clients: {str(e)}"


@tool("Check UniFi WAN Connectivity")
def check_wan_connectivity() -> str:
    """
    Check WAN (Internet) connectivity status through UniFi Gateway.

    Returns:
        Formatted string with WAN status information
    """
    try:
        if UNIFI_USE_CLOUD_API:
            data = _make_unifi_cloud_request(f"sites/{UNIFI_SITE_ID}/devices")
        else:
            data = _make_unifi_local_request("stat/device")

        devices = data.get("data", [])
        gateways = [d for d in devices if d.get("type") in ["ugw", "udm", "uxg"]]

        if not gateways:
            return "✗ No UniFi Gateway found"

        result = "=== UniFi WAN Connectivity ===\n\n"

        for gw in gateways:
            name = gw.get("name", "Gateway")
            state = gw.get("state", 0)

            result += f"Gateway: {name}\n"
            result += f"Status: {'🟢 Online' if state == 1 else '🔴 Offline'}\n\n"

            if state == 1:
                # WAN1 Status
                wan1 = gw.get("wan1", {})
                wan1_up = wan1.get("up", False)
                wan1_ip = wan1.get("ip", "N/A")
                wan1_gateway = wan1.get("gateway", "N/A")
                wan1_dns = ", ".join(wan1.get("dns", ["N/A"]))

                result += "WAN1:\n"
                result += (
                    f"  Status: {'🟢 Connected' if wan1_up else '🔴 Disconnected'}\n"
                )
                result += f"  Public IP: {wan1_ip}\n"
                result += f"  Gateway: {wan1_gateway}\n"
                result += f"  DNS Servers: {wan1_dns}\n"

                # WAN2 if present
                if "wan2" in gw:
                    wan2 = gw.get("wan2", {})
                    wan2_up = wan2.get("up", False)
                    result += (
                        f"\nWAN2: {'🟢 Connected' if wan2_up else '🔴 Disconnected'}\n"
                    )

                # Uptime
                uptime = gw.get("uptime", 0)
                uptime_days = uptime // 86400
                result += f"\nUptime: {uptime_days} days ({uptime // 3600} hours)\n"

                # Check internet connectivity
                speedtest = gw.get("speedtest-status", {})
                if speedtest:
                    download = (
                        speedtest.get("xput_download", 0) / 1000
                    )  # Convert to Mbps
                    upload = speedtest.get("xput_upload", 0) / 1000
                    latency = speedtest.get("latency", 0)

                    result += f"\n📊 Last Speed Test:\n"
                    result += f"  Download: {download:.1f} Mbps\n"
                    result += f"  Upload: {upload:.1f} Mbps\n"
                    result += f"  Latency: {latency} ms\n"

                # Warnings
                if not wan1_up:
                    result += "\n⚠️ WARNING: WAN1 is disconnected\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return (
                "✗ UniFi API authentication failed - API key may be invalid or expired"
            )
        return f"✗ UniFi API error: {e.response.status_code}"
    except Exception as e:
        return f"✗ Failed to check WAN connectivity: {str(e)}"


@tool("Monitor UniFi Switch Ports")
def monitor_switch_ports(switch_name: Optional[str] = None) -> str:
    """
    Monitor UniFi switch port status and statistics.

    Args:
        switch_name: Optional specific switch name, or None for all switches

    Returns:
        Formatted string with switch port information
    """
    try:
        if UNIFI_USE_CLOUD_API:
            data = _make_unifi_cloud_request(f"sites/{UNIFI_SITE_ID}/devices")
        else:
            data = _make_unifi_local_request("stat/device")

        devices = data.get("data", [])
        switches = [d for d in devices if d.get("type") == "usw"]

        if switch_name:
            switches = [
                s for s in switches if s.get("name", "").lower() == switch_name.lower()
            ]

        if not switches:
            return f"✗ No switches found{f' matching: {switch_name}' if switch_name else ''}"

        result = "=== UniFi Switch Port Status ===\n\n"

        for switch in switches:
            name = switch.get("name", "Unknown")
            model = switch.get("model", "Unknown")
            state = switch.get("state", 0)

            result += (
                f"🔌 {name} ({model}): {'🟢 Online' if state == 1 else '🔴 Offline'}\n"
            )

            if state == 1:
                port_table = switch.get("port_table", [])

                # Count port statuses
                total_ports = len(port_table)
                active_ports = sum(1 for p in port_table if p.get("up", False))
                poe_ports = sum(1 for p in port_table if p.get("poe_enable", False))
                poe_active = sum(
                    1
                    for p in port_table
                    if p.get("poe_mode") == "auto" and p.get("up", False)
                )

                result += f"  Total Ports: {total_ports}\n"
                result += f"  Active: {active_ports}, Inactive: {total_ports - active_ports}\n"

                if poe_ports > 0:
                    result += f"  PoE Ports: {poe_ports} ({poe_active} active)\n"

                # Show port errors
                error_ports = [
                    p
                    for p in port_table
                    if p.get("rx_errors", 0) > 100 or p.get("tx_errors", 0) > 100
                ]
                if error_ports:
                    result += f"\n  ⚠️ Ports with Errors:\n"
                    for port in error_ports:
                        port_idx = port.get("port_idx", "N/A")
                        rx_errors = port.get("rx_errors", 0)
                        tx_errors = port.get("tx_errors", 0)
                        result += f"    Port {port_idx}: RX Errors: {rx_errors}, TX Errors: {tx_errors}\n"

                # Show high traffic ports
                busy_ports = sorted(
                    [p for p in port_table if p.get("up", False)],
                    key=lambda p: p.get("rx_bytes", 0) + p.get("tx_bytes", 0),
                    reverse=True,
                )[:3]

                if busy_ports:
                    result += f"\n  📊 Highest Traffic Ports:\n"
                    for port in busy_ports:
                        port_idx = port.get("port_idx", "N/A")
                        name_port = port.get("name", f"Port {port_idx}")
                        rx_mb = port.get("rx_bytes", 0) / 1024 / 1024
                        tx_mb = port.get("tx_bytes", 0) / 1024 / 1024
                        result += (
                            f"    {name_port}: RX {rx_mb:.1f}MB, TX {tx_mb:.1f}MB\n"
                        )

            result += "\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return (
                "✗ UniFi API authentication failed - API key may be invalid or expired"
            )
        return f"✗ UniFi API error: {e.response.status_code}"
    except Exception as e:
        return f"✗ Failed to monitor switch ports: {str(e)}"


@tool("Get UniFi Network Performance")
def get_network_performance() -> str:
    """
    Get overall UniFi network performance metrics.

    Returns:
        Formatted string with network performance information
    """
    try:
        if UNIFI_USE_CLOUD_API:
            data = _make_unifi_cloud_request(f"sites/{UNIFI_SITE_ID}/health")
        else:
            data = _make_unifi_local_request("stat/health")

        health_data = data.get("data", [])

        if not health_data:
            return "✗ No health data available"

        result = "=== UniFi Network Performance ===\n\n"

        # Process health data
        for subsystem in health_data:
            subsystem_name = subsystem.get("subsystem", "Unknown")
            status = subsystem.get("status", "unknown")

            status_icon = (
                "🟢" if status == "ok" else "⚠️" if status == "warning" else "🔴"
            )

            if subsystem_name == "wan":
                result += f"{status_icon} WAN: {status.upper()}\n"
                latency = subsystem.get("latency", "N/A")
                uptime = subsystem.get("uptime", "N/A")
                result += f"  Latency: {latency} ms\n"
                result += f"  Uptime: {uptime}%\n"

            elif subsystem_name == "wlan":
                result += f"\n{status_icon} WLAN: {status.upper()}\n"
                num_user = subsystem.get("num_user", 0)
                num_ap = subsystem.get("num_adopted", 0)
                result += f"  Connected Clients: {num_user}\n"
                result += f"  Active APs: {num_ap}\n"

            elif subsystem_name == "lan":
                result += f"\n{status_icon} LAN: {status.upper()}\n"
                num_user = subsystem.get("num_user", 0)
                result += f"  Connected Devices: {num_user}\n"

            elif subsystem_name == "www":
                result += f"\n{status_icon} Internet: {status.upper()}\n"

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return (
                "✗ UniFi API authentication failed - API key may be invalid or expired"
            )
        return f"✗ UniFi API error: {e.response.status_code}"
    except Exception as e:
        return f"✗ Failed to get network performance: {str(e)}"
