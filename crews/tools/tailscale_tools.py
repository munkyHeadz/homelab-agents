"""Tailscale VPN integration tools for network visibility and monitoring."""

import os
import requests
from crewai.tools import tool
from dotenv import load_dotenv
from typing import Optional, List, Dict
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Tailscale API configuration
TAILSCALE_API_BASE = "https://api.tailscale.com/api/v2"
TAILSCALE_API_KEY = os.getenv('TAILSCALE_API_KEY')
TAILSCALE_TAILNET = os.getenv('TAILSCALE_TAILNET', 'mariusmyklevik@gmail.com')

def _make_tailscale_request(endpoint: str) -> dict:
    """
    Make authenticated request to Tailscale API.

    Args:
        endpoint: API endpoint path

    Returns:
        JSON response as dictionary
    """
    url = f"{TAILSCALE_API_BASE}/tailnet/{TAILSCALE_TAILNET}/{endpoint}"
    response = requests.get(url, auth=(TAILSCALE_API_KEY, ''))
    response.raise_for_status()
    return response.json()


@tool("List Tailscale Devices")
def list_tailscale_devices(filter_online: Optional[bool] = None) -> str:
    """
    List all devices in the Tailscale network (tailnet).

    Args:
        filter_online: If True, show only online devices. If False, only offline.
                      If None (default), show all devices.

    Returns:
        Formatted list of devices with status, IP addresses, and last seen time

    Examples:
        - list_tailscale_devices() - Show all devices
        - list_tailscale_devices(filter_online=True) - Only online devices
        - list_tailscale_devices(filter_online=False) - Only offline devices
    """
    try:
        data = _make_tailscale_request("devices")
        devices = data.get('devices', [])

        if not devices:
            return "No Tailscale devices found"

        # Filter by online status if specified
        if filter_online is not None:
            devices = [d for d in devices if d.get('connectedToControl') == filter_online]

        # Format device list
        result = []
        online_count = 0
        offline_count = 0

        for device in devices:
            name = device.get('hostname', 'unknown')
            ip = device.get('addresses', ['no-ip'])[0]
            online = device.get('connectedToControl', False)
            status = "🟢 ONLINE" if online else "🔴 OFFLINE"
            last_seen = device.get('lastSeen', 'never')
            os_type = device.get('os', 'unknown')
            client_version = device.get('clientVersion', 'unknown')

            # Parse last seen time
            if last_seen != 'never':
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    now = datetime.now(last_seen_dt.tzinfo)
                    delta = now - last_seen_dt

                    if delta < timedelta(minutes=5):
                        last_seen_str = "just now"
                    elif delta < timedelta(hours=1):
                        last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                    elif delta < timedelta(days=1):
                        last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                    else:
                        last_seen_str = f"{delta.days}d ago"
                except Exception:
                    last_seen_str = last_seen
            else:
                last_seen_str = "never"

            result.append(f"{status} {name} ({ip}) - {os_type} - Last seen: {last_seen_str}")

            if online:
                online_count += 1
            else:
                offline_count += 1

        summary = f"\n\n📊 Summary: {online_count} online, {offline_count} offline, {len(devices)} total"
        return "\n".join(result) + summary

    except requests.exceptions.HTTPError as e:
        return f"✗ Tailscale API error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"✗ Error listing Tailscale devices: {str(e)}"


@tool("Check Device Connectivity")
def check_device_connectivity(hostname: str) -> str:
    """
    Check the connectivity status and details of a specific Tailscale device.

    Args:
        hostname: Device hostname to check (e.g., 'docker-gateway', 'postgres')

    Returns:
        Detailed status information for the specified device

    Examples:
        - check_device_connectivity('docker-gateway')
        - check_device_connectivity('postgres')
    """
    try:
        data = _make_tailscale_request("devices")
        devices = data.get('devices', [])

        # Find device by hostname
        device = None
        for d in devices:
            if d.get('hostname', '').lower() == hostname.lower():
                device = d
                break

        if not device:
            # Try searching by name field
            for d in devices:
                if hostname.lower() in d.get('name', '').lower():
                    device = d
                    break

        if not device:
            available = [d.get('hostname', 'unknown') for d in devices[:10]]
            return f"✗ Device '{hostname}' not found. Available devices: {', '.join(available)}"

        # Extract device details
        name = device.get('hostname', 'unknown')
        ip_v4 = device.get('addresses', ['no-ip'])[0]
        ip_v6 = device.get('addresses', ['no-ipv6'])[1] if len(device.get('addresses', [])) > 1 else 'no-ipv6'
        online = device.get('connectedToControl', False)
        last_seen = device.get('lastSeen', 'never')
        os_type = device.get('os', 'unknown')
        client_version = device.get('clientVersion', 'unknown')
        update_available = device.get('updateAvailable', False)
        created = device.get('created', 'unknown')
        expires = device.get('expires', 'never')
        key_expiry_disabled = device.get('keyExpiryDisabled', False)

        status = "🟢 ONLINE" if online else "🔴 OFFLINE"
        update_status = "⚠️ Update available" if update_available else "✓ Up to date"

        result = f"""
Device: {name}
Status: {status}
IPv4: {ip_v4}
IPv6: {ip_v6}
OS: {os_type}
Client Version: {client_version} ({update_status})
Last Seen: {last_seen}
Created: {created}
Key Expires: {expires if not key_expiry_disabled else 'Never (disabled)'}
"""
        return result.strip()

    except requests.exceptions.HTTPError as e:
        return f"✗ Tailscale API error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"✗ Error checking device connectivity: {str(e)}"


@tool("Monitor VPN Health")
def monitor_vpn_health() -> str:
    """
    Monitor overall Tailscale VPN health and provide summary statistics.

    Returns:
        Health summary with device counts, offline devices, and alerts

    Use this tool to get a quick overview of the entire Tailscale network health.
    """
    try:
        data = _make_tailscale_request("devices")
        devices = data.get('devices', [])

        if not devices:
            return "⚠️ No Tailscale devices found"

        # Calculate statistics
        total = len(devices)
        online = sum(1 for d in devices if d.get('connectedToControl'))
        offline = total - online

        # Find devices offline for more than 24 hours
        critical_offline = []
        warning_offline = []
        updates_needed = []

        now = datetime.now(datetime.now().astimezone().tzinfo)

        for device in devices:
            hostname = device.get('hostname', 'unknown')

            # Check offline status
            if not device.get('connectedToControl'):
                last_seen = device.get('lastSeen', '')
                if last_seen:
                    try:
                        last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                        delta = now - last_seen_dt

                        if delta > timedelta(days=7):
                            critical_offline.append(f"{hostname} (offline {delta.days}d)")
                        elif delta > timedelta(days=1):
                            warning_offline.append(f"{hostname} (offline {delta.days}d)")
                    except Exception:
                        pass

            # Check for updates
            if device.get('updateAvailable'):
                updates_needed.append(hostname)

        # Build health report
        health_status = "✅ HEALTHY" if offline == 0 else "⚠️ WARNING" if offline < total * 0.2 else "🔴 CRITICAL"

        result = f"""
=== Tailscale VPN Health ===
Overall Status: {health_status}

📊 Statistics:
  Total Devices: {total}
  Online: {online} ({online/total*100:.1f}%)
  Offline: {offline} ({offline/total*100:.1f}%)

"""

        if critical_offline:
            result += f"🔴 Critical (offline >7 days): {len(critical_offline)}\n"
            for device in critical_offline[:5]:
                result += f"  - {device}\n"

        if warning_offline:
            result += f"⚠️ Warning (offline >1 day): {len(warning_offline)}\n"
            for device in warning_offline[:5]:
                result += f"  - {device}\n"

        if updates_needed:
            result += f"\n🔄 Updates Available: {len(updates_needed)}\n"
            for device in updates_needed[:5]:
                result += f"  - {device}\n"

        if not critical_offline and not warning_offline and not updates_needed:
            result += "\n✓ All devices healthy and up to date"

        return result.strip()

    except requests.exceptions.HTTPError as e:
        return f"✗ Tailscale API error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"✗ Error monitoring VPN health: {str(e)}"


@tool("Get Critical Infrastructure Status")
def get_critical_infrastructure_status() -> str:
    """
    Check the Tailscale connectivity status of critical infrastructure devices.

    Returns:
        Status of critical homelab infrastructure (Proxmox, docker-gateway,
        monitoring, postgres, etc.)

    Use this tool to quickly verify that all essential infrastructure is online.
    """
    try:
        data = _make_tailscale_request("devices")
        devices = data.get('devices', [])

        # Define critical infrastructure
        critical_hostnames = [
            'fjeld',  # Proxmox host
            'docker-gateway',
            'postgres',
            'grafana',
            'prometheus',
            'portal'
        ]

        # Find critical devices
        critical_devices = {}
        for hostname in critical_hostnames:
            for device in devices:
                if device.get('hostname', '').lower() == hostname.lower():
                    critical_devices[hostname] = device
                    break

        # Build status report
        result = "=== Critical Infrastructure Status ===\n\n"
        all_online = True

        for hostname in critical_hostnames:
            device = critical_devices.get(hostname)

            if not device:
                result += f"🔴 {hostname}: NOT FOUND\n"
                all_online = False
                continue

            online = device.get('connectedToControl', False)
            ip = device.get('addresses', ['no-ip'])[0]

            if online:
                result += f"✅ {hostname}: ONLINE ({ip})\n"
            else:
                last_seen = device.get('lastSeen', 'never')
                result += f"🔴 {hostname}: OFFLINE - Last seen: {last_seen}\n"
                all_online = False

        if all_online:
            result += "\n✅ All critical infrastructure online"
        else:
            result += "\n⚠️ Some critical infrastructure offline - immediate attention required"

        return result.strip()

    except requests.exceptions.HTTPError as e:
        return f"✗ Tailscale API error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"✗ Error checking critical infrastructure: {str(e)}"
