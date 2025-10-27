"""Alertmanager management and monitoring tools for homelab agents."""

import requests
from crewai.tools import tool
from typing import Optional
from datetime import datetime, timedelta
import json


ALERTMANAGER_URL = "http://192.168.1.106:9093"
REQUEST_TIMEOUT = 10


@tool("List Active Alerts")
def list_active_alerts(state_filter: Optional[str] = None) -> str:
    """
    List active alerts from Alertmanager.

    Args:
        state_filter: Optional filter - 'active', 'suppressed', 'unprocessed', or None for all

    Returns:
        String with active alerts, their severity, and current state

    Use Cases:
        - Check what alerts are currently firing
        - Verify alert suppression during maintenance
        - Incident triage and prioritization
        - Alert fatigue analysis
    """
    try:
        url = f"{ALERTMANAGER_URL}/api/v2/alerts"

        params = {}
        if state_filter:
            params['filter'] = f'state="{state_filter}"'

        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        alerts = response.json()

        if not alerts:
            return "No active alerts in Alertmanager"

        # Group alerts by state
        active_alerts = []
        suppressed_alerts = []
        unprocessed_alerts = []

        for alert in alerts:
            state = alert.get('status', {}).get('state', 'unknown')
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})

            alertname = labels.get('alertname', 'unknown')
            severity = labels.get('severity', 'unknown')
            instance = labels.get('instance', 'N/A')
            summary = annotations.get('summary', annotations.get('description', 'No description'))

            # Get silenced by info
            silenced_by = alert.get('status', {}).get('silencedBy', [])

            alert_str = f"  • {alertname} ({severity}) - {instance}"
            if summary:
                alert_str += f"\n    {summary}"
            if silenced_by:
                alert_str += f"\n    Silenced by: {', '.join(silenced_by)}"

            if state == 'active':
                active_alerts.append(alert_str)
            elif state == 'suppressed':
                suppressed_alerts.append(alert_str)
            else:
                unprocessed_alerts.append(alert_str)

        output = [
            "=== Alertmanager Active Alerts ===",
            f"Total alerts: {len(alerts)}",
            f"Active: {len(active_alerts)}, Suppressed: {len(suppressed_alerts)}, Unprocessed: {len(unprocessed_alerts)}",
            ""
        ]

        if active_alerts:
            output.append("🔴 Active Alerts:")
            output.extend(active_alerts)
            output.append("")

        if suppressed_alerts:
            output.append("🔕 Suppressed Alerts (silenced):")
            output.extend(suppressed_alerts)
            output.append("")

        if unprocessed_alerts:
            output.append("⚠️ Unprocessed Alerts:")
            output.extend(unprocessed_alerts)

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return "✗ Error: Cannot connect to Alertmanager at " + ALERTMANAGER_URL + "\n  Verify Alertmanager is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Alertmanager request timed out (>10s)\n  Alertmanager may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        return f"✗ HTTP Error from Alertmanager: {e.response.status_code}\n  {e.response.text}"
    except Exception as e:
        return f"✗ Error listing Alertmanager alerts: {str(e)}"


@tool("List Alert Silences")
def list_alert_silences(active_only: bool = True) -> str:
    """
    List alert silences configured in Alertmanager.

    Args:
        active_only: If True, only show active silences. If False, include expired.

    Returns:
        String with configured silences, their matchers, and expiry times

    Use Cases:
        - Check active maintenance windows
        - Verify silence configuration
        - Find expired silences to clean up
        - Audit who created silences
    """
    try:
        url = f"{ALERTMANAGER_URL}/api/v2/silences"

        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        silences = response.json()

        if not silences:
            return "No silences configured in Alertmanager"

        # Filter and categorize silences
        active_silences = []
        pending_silences = []
        expired_silences = []

        now = datetime.utcnow()

        for silence in silences:
            silence_id = silence.get('id', 'unknown')
            status = silence.get('status', {}).get('state', 'unknown')

            matchers = silence.get('matchers', [])
            matcher_strs = []
            for m in matchers:
                name = m.get('name', 'unknown')
                value = m.get('value', 'unknown')
                is_regex = m.get('isRegex', False)
                is_equal = m.get('isEqual', True)

                op = '=~' if is_regex else ('=' if is_equal else '!=')
                matcher_strs.append(f"{name}{op}\"{value}\"")

            starts_at = silence.get('startsAt', '')
            ends_at = silence.get('endsAt', '')
            comment = silence.get('comment', 'No comment')
            created_by = silence.get('createdBy', 'unknown')

            # Parse times
            try:
                ends_at_dt = datetime.fromisoformat(ends_at.replace('Z', '+00:00'))
                time_remaining = ends_at_dt - now
                hours_remaining = time_remaining.total_seconds() / 3600

                if hours_remaining > 0:
                    time_str = f"{hours_remaining:.1f} hours remaining"
                else:
                    time_str = "expired"
            except:
                time_str = "unknown"

            silence_str = f"  • ID: {silence_id} ({status})\n"
            silence_str += f"    Matchers: {', '.join(matcher_strs)}\n"
            silence_str += f"    Expires: {ends_at} ({time_str})\n"
            silence_str += f"    Comment: {comment}\n"
            silence_str += f"    Created by: {created_by}"

            if status == 'active':
                active_silences.append(silence_str)
            elif status == 'pending':
                pending_silences.append(silence_str)
            elif status == 'expired':
                expired_silences.append(silence_str)

        output = [
            "=== Alertmanager Silences ===",
            f"Total silences: {len(silences)}",
            f"Active: {len(active_silences)}, Pending: {len(pending_silences)}, Expired: {len(expired_silences)}",
            ""
        ]

        if active_silences:
            output.append("🔕 Active Silences:")
            output.extend(active_silences)
            output.append("")

        if pending_silences:
            output.append("⏰ Pending Silences (not started yet):")
            output.extend(pending_silences)
            output.append("")

        if not active_only and expired_silences:
            output.append("⏱️ Expired Silences:")
            output.extend(expired_silences[:5])  # Limit to 5 for readability
            if len(expired_silences) > 5:
                output.append(f"  ... and {len(expired_silences) - 5} more")

        if not active_silences and not pending_silences:
            output.append("✓ No active or pending silences - all alerts are being processed")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return "✗ Error: Cannot connect to Alertmanager at " + ALERTMANAGER_URL + "\n  Verify Alertmanager is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Alertmanager request timed out (>10s)\n  Alertmanager may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        return f"✗ HTTP Error from Alertmanager: {e.response.status_code}\n  {e.response.text}"
    except Exception as e:
        return f"✗ Error listing Alertmanager silences: {str(e)}"


@tool("Create Alert Silence")
def create_alert_silence(
    alertname: str,
    duration_hours: int = 2,
    comment: str = "Maintenance window - automated silence"
) -> str:
    """
    Create a silence for alerts during maintenance windows.

    Args:
        alertname: Name of alert to silence (e.g., 'HighMemoryUsage')
        duration_hours: How long to silence (default 2 hours)
        comment: Reason for silence

    Returns:
        Success message with silence ID or error details

    Use Cases:
        - Silence alerts during planned maintenance
        - Prevent alert fatigue during deployments
        - Temporary suppression while investigating issues
        - Automated silence creation by healer agent

    Safety:
        - Maximum 24 hours to prevent accidental long-term silencing
        - Requires explicit alertname (no wildcards by default)
        - Records creator and comment for audit trail
    """
    try:
        # Safety check: limit duration
        if duration_hours > 24:
            return f"✗ Error: Duration too long ({duration_hours}h)\n  Maximum allowed: 24 hours\n  This prevents accidental long-term alert suppression"

        if duration_hours < 1:
            return "✗ Error: Duration must be at least 1 hour"

        url = f"{ALERTMANAGER_URL}/api/v2/silences"

        # Calculate times
        starts_at = datetime.utcnow()
        ends_at = starts_at + timedelta(hours=duration_hours)

        # Create silence payload
        payload = {
            "matchers": [
                {
                    "name": "alertname",
                    "value": alertname,
                    "isRegex": False,
                    "isEqual": True
                }
            ],
            "startsAt": starts_at.isoformat() + "Z",
            "endsAt": ends_at.isoformat() + "Z",
            "createdBy": "homelab-ai-agents",
            "comment": comment
        }

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        result = response.json()
        silence_id = result.get('silenceID', 'unknown')

        output = [
            "✓ Alert silence created successfully",
            f"Silence ID: {silence_id}",
            f"Alert: {alertname}",
            f"Duration: {duration_hours} hours",
            f"Expires: {ends_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"Comment: {comment}",
            "",
            "💡 Use delete_alert_silence() with this ID to remove early"
        ]

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return "✗ Error: Cannot connect to Alertmanager at " + ALERTMANAGER_URL + "\n  Verify Alertmanager is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Alertmanager request timed out (>10s)\n  Alertmanager may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        return f"✗ HTTP Error from Alertmanager: {e.response.status_code}\n  {e.response.text}"
    except Exception as e:
        return f"✗ Error creating alert silence: {str(e)}"


@tool("Delete Alert Silence")
def delete_alert_silence(silence_id: str) -> str:
    """
    Delete an alert silence by ID.

    Args:
        silence_id: The silence ID to delete (from list_alert_silences)

    Returns:
        Success or error message

    Use Cases:
        - End maintenance window early
        - Remove accidental silences
        - Clean up after resolved issues
        - Restore normal alerting

    Safety:
        - Requires explicit silence ID (no wildcards)
        - Returns error if silence doesn't exist
        - Cannot delete already-expired silences
    """
    try:
        url = f"{ALERTMANAGER_URL}/api/v2/silence/{silence_id}"

        response = requests.delete(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        output = [
            "✓ Alert silence deleted successfully",
            f"Silence ID: {silence_id}",
            "",
            "Alerts matching this silence will now fire normally"
        ]

        return "\n".join(output)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"✗ Error: Silence ID '{silence_id}' not found\n  Use list_alert_silences() to see available silences"
        return f"✗ HTTP Error from Alertmanager: {e.response.status_code}\n  {e.response.text}"
    except requests.exceptions.ConnectionError:
        return "✗ Error: Cannot connect to Alertmanager at " + ALERTMANAGER_URL + "\n  Verify Alertmanager is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Alertmanager request timed out (>10s)\n  Alertmanager may be overloaded or unresponsive"
    except Exception as e:
        return f"✗ Error deleting alert silence: {str(e)}"


@tool("Check Alert Routing")
def check_alert_routing(alertname: Optional[str] = None) -> str:
    """
    Check Alertmanager routing configuration and receiver status.

    Args:
        alertname: Optional alert name to check routing for specific alert

    Returns:
        String with routing tree, receivers, and configuration status

    Use Cases:
        - Verify alerts are routed to correct receivers
        - Troubleshoot missing notifications
        - Audit alert routing configuration
        - Validate webhook endpoints
    """
    try:
        # Get Alertmanager status
        status_url = f"{ALERTMANAGER_URL}/api/v2/status"
        status_response = requests.get(status_url, timeout=REQUEST_TIMEOUT)
        status_response.raise_for_status()
        status = status_response.json()

        cluster = status.get('cluster', {})
        config = status.get('config', {})
        version_info = status.get('versionInfo', {})

        output = [
            "=== Alertmanager Routing Status ===",
            f"Version: {version_info.get('version', 'unknown')}",
            f"Cluster: {cluster.get('status', 'unknown')} ({len(cluster.get('peers', []))} peers)",
            ""
        ]

        # Parse routing configuration
        route = config.get('route', {})
        if route:
            receiver = route.get('receiver', 'unknown')
            group_by = route.get('group_by', [])
            group_wait = route.get('group_wait', 'unknown')
            group_interval = route.get('group_interval', 'unknown')
            repeat_interval = route.get('repeat_interval', 'unknown')

            output.append("Root Route Configuration:")
            output.append(f"  Default receiver: {receiver}")
            output.append(f"  Group by: {', '.join(group_by) if group_by else 'none'}")
            output.append(f"  Group wait: {group_wait}")
            output.append(f"  Group interval: {group_interval}")
            output.append(f"  Repeat interval: {repeat_interval}")
            output.append("")

            # Show child routes
            routes = route.get('routes', [])
            if routes:
                output.append(f"Child Routes: {len(routes)}")
                for idx, child_route in enumerate(routes[:5], 1):  # Show first 5
                    child_receiver = child_route.get('receiver', 'unknown')
                    matchers = child_route.get('match', {})
                    match_re = child_route.get('match_re', {})

                    output.append(f"  Route {idx}: → {child_receiver}")
                    if matchers:
                        for k, v in matchers.items():
                            output.append(f"    Match: {k}={v}")
                    if match_re:
                        for k, v in match_re.items():
                            output.append(f"    Match regex: {k}=~{v}")

                if len(routes) > 5:
                    output.append(f"  ... and {len(routes) - 5} more routes")
                output.append("")

        # List receivers
        receivers = config.get('receivers', [])
        if receivers:
            output.append(f"Configured Receivers: {len(receivers)}")
            for receiver in receivers:
                name = receiver.get('name', 'unknown')
                webhook_configs = receiver.get('webhook_configs', [])
                email_configs = receiver.get('email_configs', [])
                slack_configs = receiver.get('slack_configs', [])

                output.append(f"  • {name}:")
                if webhook_configs:
                    for wh in webhook_configs:
                        url = wh.get('url', 'unknown')
                        output.append(f"    Webhook: {url}")
                if email_configs:
                    output.append(f"    Email configs: {len(email_configs)}")
                if slack_configs:
                    output.append(f"    Slack configs: {len(slack_configs)}")

        # If specific alert name provided, check where it would route
        if alertname:
            output.append("")
            output.append(f"Routing for alert '{alertname}':")
            output.append(f"  Would route to: {receiver} (default)")
            output.append("  💡 Use Alertmanager web UI for detailed routing simulation")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return "✗ Error: Cannot connect to Alertmanager at " + ALERTMANAGER_URL + "\n  Verify Alertmanager is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Alertmanager request timed out (>10s)\n  Alertmanager may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        return f"✗ HTTP Error from Alertmanager: {e.response.status_code}\n  {e.response.text}"
    except Exception as e:
        return f"✗ Error checking Alertmanager routing: {str(e)}"


@tool("Get Alertmanager Status")
def get_alertmanager_status() -> str:
    """
    Get overall Alertmanager health and status.

    Returns:
        String with Alertmanager version, uptime, cluster status, and health

    Use Cases:
        - Verify Alertmanager is operational
        - Check cluster health (if clustered)
        - Monitor Alertmanager itself
        - Troubleshoot alert delivery issues
    """
    try:
        # Get status
        status_url = f"{ALERTMANAGER_URL}/api/v2/status"
        status_response = requests.get(status_url, timeout=REQUEST_TIMEOUT)
        status_response.raise_for_status()
        status = status_response.json()

        # Get active alerts count
        alerts_url = f"{ALERTMANAGER_URL}/api/v2/alerts"
        alerts_response = requests.get(alerts_url, timeout=REQUEST_TIMEOUT)
        alerts_response.raise_for_status()
        alerts = alerts_response.json()

        # Get silences count
        silences_url = f"{ALERTMANAGER_URL}/api/v2/silences"
        silences_response = requests.get(silences_url, timeout=REQUEST_TIMEOUT)
        silences_response.raise_for_status()
        silences = silences_response.json()

        # Parse status
        cluster = status.get('cluster', {})
        config = status.get('config', {})
        version_info = status.get('versionInfo', {})
        uptime = status.get('uptime', 'unknown')

        # Count alert states
        active_count = sum(1 for a in alerts if a.get('status', {}).get('state') == 'active')
        suppressed_count = sum(1 for a in alerts if a.get('status', {}).get('state') == 'suppressed')

        # Count silence states
        active_silences = sum(1 for s in silences if s.get('status', {}).get('state') == 'active')

        output = [
            "=== Alertmanager System Status ===",
            f"Version: {version_info.get('version', 'unknown')}",
            f"Branch: {version_info.get('branch', 'unknown')}",
            f"Build Date: {version_info.get('buildDate', 'unknown')}",
            f"Uptime: {uptime}",
            "",
            "Cluster Information:",
            f"  Status: {cluster.get('status', 'unknown')}",
            f"  Peers: {len(cluster.get('peers', []))}",
            f"  Name: {cluster.get('name', 'unknown')}",
            "",
            "Alert Statistics:",
            f"  Total alerts: {len(alerts)}",
            f"  Active: {active_count}",
            f"  Suppressed: {suppressed_count}",
            "",
            "Silence Statistics:",
            f"  Total silences: {len(silences)}",
            f"  Active: {active_silences}",
            "",
            "Configuration:",
            f"  Receivers: {len(config.get('receivers', []))}",
            f"  Routes: {len(config.get('route', {}).get('routes', []))}",
        ]

        # Health check
        output.append("")
        if cluster.get('status') == 'ready':
            output.append("✓ Alertmanager is healthy and operational")
        else:
            output.append("⚠️ Alertmanager cluster status: " + cluster.get('status', 'unknown'))

        if active_count == 0:
            output.append("✓ No active alerts")
        else:
            output.append(f"⚠️ {active_count} active alerts firing")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return "✗ Error: Cannot connect to Alertmanager at " + ALERTMANAGER_URL + "\n  Verify Alertmanager is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Alertmanager request timed out (>10s)\n  Alertmanager may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        return f"✗ HTTP Error from Alertmanager: {e.response.status_code}\n  {e.response.text}"
    except Exception as e:
        return f"✗ Error getting Alertmanager status: {str(e)}"
