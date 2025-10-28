"""Grafana API tools for dashboard management and incident correlation."""

import json
import os
from datetime import datetime
from typing import Optional

import requests
from crewai.tools import tool

GRAFANA_URL = "http://100.120.140.105:3000"
REQUEST_TIMEOUT = 10


def _get_grafana_headers():
    """Get authentication headers for Grafana API."""
    # Try API key first (if configured)
    api_key = os.getenv("GRAFANA_API_KEY")
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}

    # Fallback to basic auth (default admin:admin)
    # In production, should use API key
    return {}


def _get_grafana_auth():
    """Get authentication tuple for requests."""
    api_key = os.getenv("GRAFANA_API_KEY")
    if api_key:
        return None  # Use headers instead

    # Fallback to basic auth
    username = os.getenv("GRAFANA_USERNAME", "admin")
    password = os.getenv("GRAFANA_PASSWORD", "admin")
    return (username, password)


@tool("Add Annotation to Grafana")
def add_annotation(
    text: str, tags: Optional[str] = None, dashboard_id: Optional[int] = None
) -> str:
    """
    Add an annotation to Grafana graphs to mark incidents and events.

    Args:
        text: Annotation text describing the event/incident
        tags: Comma-separated tags (e.g., "incident,resolved,container-restart")
        dashboard_id: Optional specific dashboard ID (None for all dashboards)

    Returns:
        Success message with annotation ID or error details

    Use Cases:
        - Mark incident start/end times on graphs
        - Correlate events with metric changes
        - Track deployments and restarts
        - Document remediation actions
        - Create visual timeline of incidents

    Examples:
        - text="Container nginx restarted", tags="incident,container,restart"
        - text="Deployment started", tags="deployment,maintenance"
        - text="High memory resolved", tags="incident,resolved"
    """
    try:
        url = f"{GRAFANA_URL}/api/annotations"

        # Prepare annotation payload
        payload = {
            "text": text,
            "time": int(datetime.utcnow().timestamp() * 1000),  # Milliseconds
        }

        # Add tags if provided
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            payload["tags"] = tag_list

        # Add dashboard if specified
        if dashboard_id:
            payload["dashboardId"] = dashboard_id

        headers = _get_grafana_headers()
        auth = _get_grafana_auth()

        response = requests.post(
            url, json=payload, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        result = response.json()
        annotation_id = result.get("id", "unknown")

        output = [
            "✓ Annotation added to Grafana",
            f"Annotation ID: {annotation_id}",
            f"Text: {text}",
        ]

        if tags:
            output.append(f"Tags: {tags}")

        if dashboard_id:
            output.append(f"Dashboard: {dashboard_id}")
        else:
            output.append("Scope: All dashboards")

        output.append("")
        output.append(
            "💡 Annotation is now visible on Grafana graphs at the current time"
        )

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return f"✗ Error: Cannot connect to Grafana at {GRAFANA_URL}\n  Verify Grafana is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Grafana request timed out (>10s)\n  Grafana may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "✗ Error: Grafana authentication failed\n  Check GRAFANA_API_KEY or GRAFANA_USERNAME/PASSWORD"
        return (
            f"✗ HTTP Error from Grafana: {e.response.status_code}\n  {e.response.text}"
        )
    except Exception as e:
        return f"✗ Error adding Grafana annotation: {str(e)}"


@tool("Get Grafana Status")
def get_grafana_status() -> str:
    """
    Get Grafana health, version, and configuration status.

    Returns:
        String with Grafana health, version, database status, and stats

    Use Cases:
        - Verify Grafana is operational
        - Check version for compatibility
        - Monitor Grafana health
        - Troubleshoot dashboard loading issues
    """
    try:
        # Get health endpoint
        health_url = f"{GRAFANA_URL}/api/health"
        health_response = requests.get(health_url, timeout=REQUEST_TIMEOUT)
        health_response.raise_for_status()
        health = health_response.json()

        # Get version/stats (requires auth)
        headers = _get_grafana_headers()
        auth = _get_grafana_auth()

        # Get user info (validates auth and gets version)
        user_url = f"{GRAFANA_URL}/api/user"
        user_response = requests.get(
            user_url, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )

        # Get admin stats
        stats_url = f"{GRAFANA_URL}/api/admin/stats"
        stats_response = requests.get(
            stats_url, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )

        output = [
            "=== Grafana Status ===",
        ]

        # Health info
        if health.get("database") == "ok":
            output.append("Database: ✓ OK")
        else:
            output.append(f"Database: ⚠️ {health.get('database', 'unknown')}")

        output.append(f"Version: {health.get('version', 'unknown')}")
        output.append("")

        # User info if auth successful
        if user_response.status_code == 200:
            user = user_response.json()
            output.append("Authentication: ✓ Valid")
            output.append(f"User: {user.get('login', 'unknown')}")
            output.append(f"Role: {user.get('orgRole', 'unknown')}")
            output.append("")
        else:
            output.append("Authentication: ⚠️ Failed (using fallback)")
            output.append("")

        # Stats if available
        if stats_response.status_code == 200:
            stats = stats_response.json()
            output.append("Statistics:")
            output.append(f"  Dashboards: {stats.get('dashboards', 'N/A')}")
            output.append(f"  Users: {stats.get('users', 'N/A')}")
            output.append(f"  Playlists: {stats.get('playlists', 'N/A')}")
            output.append(f"  Datasources: {stats.get('datasources', 'N/A')}")
            output.append(f"  Alerts: {stats.get('alerts', 'N/A')}")
            output.append(f"  Annotations: {stats.get('annotations', 'N/A')}")

        output.append("")
        if health.get("database") == "ok":
            output.append("✓ Grafana is healthy and operational")
        else:
            output.append("⚠️ Grafana may have issues - check database")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return f"✗ Error: Cannot connect to Grafana at {GRAFANA_URL}\n  Verify Grafana is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Grafana request timed out (>10s)\n  Grafana may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        return (
            f"✗ HTTP Error from Grafana: {e.response.status_code}\n  {e.response.text}"
        )
    except Exception as e:
        return f"✗ Error getting Grafana status: {str(e)}"


@tool("List Grafana Dashboards")
def list_dashboards(search: Optional[str] = None) -> str:
    """
    List all Grafana dashboards or search for specific ones.

    Args:
        search: Optional search term to filter dashboards

    Returns:
        String with dashboard names, UIDs, URLs, and tags

    Use Cases:
        - Discover available dashboards
        - Find dashboard UID for annotations
        - Verify dashboard exists
        - Search for relevant dashboards
    """
    try:
        url = f"{GRAFANA_URL}/api/search"
        headers = _get_grafana_headers()
        auth = _get_grafana_auth()

        params = {"type": "dash-db"}
        if search:
            params["query"] = search

        response = requests.get(
            url, params=params, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        dashboards = response.json()

        if not dashboards:
            if search:
                return f"No dashboards found matching '{search}'"
            return "No dashboards found in Grafana"

        output = [
            "=== Grafana Dashboards ===",
            f"Total dashboards: {len(dashboards)}",
        ]

        if search:
            output.append(f"Filter: '{search}'")

        output.append("")

        for dash in dashboards[:20]:  # Limit to 20 for readability
            title = dash.get("title", "unknown")
            uid = dash.get("uid", "unknown")
            url_path = dash.get("url", "")
            tags = dash.get("tags", [])
            folder = dash.get("folderTitle", "General")

            output.append(f"• {title}")
            output.append(f"  UID: {uid}")
            output.append(f"  URL: {GRAFANA_URL}{url_path}")
            if tags:
                output.append(f"  Tags: {', '.join(tags)}")
            output.append(f"  Folder: {folder}")
            output.append("")

        if len(dashboards) > 20:
            output.append(f"... and {len(dashboards) - 20} more dashboards")
            output.append("💡 Use search parameter to filter results")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return f"✗ Error: Cannot connect to Grafana at {GRAFANA_URL}\n  Verify Grafana is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Grafana request timed out (>10s)\n  Grafana may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "✗ Error: Grafana authentication failed\n  Check GRAFANA_API_KEY or GRAFANA_USERNAME/PASSWORD"
        return (
            f"✗ HTTP Error from Grafana: {e.response.status_code}\n  {e.response.text}"
        )
    except Exception as e:
        return f"✗ Error listing Grafana dashboards: {str(e)}"


@tool("Get Dashboard Details")
def get_dashboard(dashboard_uid: str) -> str:
    """
    Get detailed information about a specific Grafana dashboard.

    Args:
        dashboard_uid: Dashboard UID (from list_dashboards)

    Returns:
        String with dashboard configuration, panels, and metadata

    Use Cases:
        - View dashboard panels and queries
        - Check dashboard configuration
        - Verify datasources used
        - Troubleshoot dashboard issues
    """
    try:
        url = f"{GRAFANA_URL}/api/dashboards/uid/{dashboard_uid}"
        headers = _get_grafana_headers()
        auth = _get_grafana_auth()

        response = requests.get(
            url, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        result = response.json()
        dashboard = result.get("dashboard", {})
        meta = result.get("meta", {})

        title = dashboard.get("title", "unknown")
        uid = dashboard.get("uid", "unknown")
        tags = dashboard.get("tags", [])
        panels = dashboard.get("panels", [])

        output = [
            f"=== Dashboard: {title} ===",
            f"UID: {uid}",
            f"URL: {GRAFANA_URL}/d/{uid}",
        ]

        if tags:
            output.append(f"Tags: {', '.join(tags)}")

        output.append(f"Version: {meta.get('version', 'unknown')}")
        output.append(f"Created: {meta.get('created', 'unknown')}")
        output.append(f"Updated: {meta.get('updated', 'unknown')}")
        output.append("")

        # Panel information
        output.append(f"Panels: {len(panels)}")

        if panels:
            output.append("")
            output.append("Panel List:")
            for panel in panels[:10]:  # Limit to 10
                panel_title = panel.get("title", "Untitled")
                panel_type = panel.get("type", "unknown")
                datasource = panel.get("datasource", {})
                if isinstance(datasource, dict):
                    ds_name = datasource.get("uid", "unknown")
                else:
                    ds_name = datasource

                output.append(f"  • {panel_title} ({panel_type})")
                output.append(f"    Datasource: {ds_name}")

            if len(panels) > 10:
                output.append(f"  ... and {len(panels) - 10} more panels")

        # Variables
        templating = dashboard.get("templating", {})
        variables = templating.get("list", [])
        if variables:
            output.append("")
            output.append(f"Variables: {len(variables)}")
            for var in variables[:5]:
                var_name = var.get("name", "unknown")
                var_type = var.get("type", "unknown")
                output.append(f"  • ${var_name} ({var_type})")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return f"✗ Error: Cannot connect to Grafana at {GRAFANA_URL}\n  Verify Grafana is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Grafana request timed out (>10s)\n  Grafana may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"✗ Error: Dashboard UID '{dashboard_uid}' not found\n  Use list_dashboards() to see available dashboards"
        if e.response.status_code == 401:
            return "✗ Error: Grafana authentication failed\n  Check GRAFANA_API_KEY or GRAFANA_USERNAME/PASSWORD"
        return (
            f"✗ HTTP Error from Grafana: {e.response.status_code}\n  {e.response.text}"
        )
    except Exception as e:
        return f"✗ Error getting Grafana dashboard: {str(e)}"


@tool("Create Dashboard Snapshot")
def create_snapshot(
    dashboard_uid: str, name: Optional[str] = None, expires_seconds: int = 3600
) -> str:
    """
    Create a snapshot of a dashboard to capture its state during an incident.

    Args:
        dashboard_uid: Dashboard UID to snapshot
        name: Optional snapshot name (default: auto-generated)
        expires_seconds: Snapshot expiry time in seconds (default 3600 = 1 hour)

    Returns:
        Success message with snapshot URL or error details

    Use Cases:
        - Capture dashboard state during incidents
        - Share dashboard view with stakeholders
        - Preserve evidence of metric state
        - Create incident reports

    Safety:
        - Snapshots expire automatically (default 1 hour)
        - Maximum expiry: 7 days (604800 seconds)
    """
    try:
        # Limit expiry time for safety
        max_expiry = 604800  # 7 days
        if expires_seconds > max_expiry:
            return f"✗ Error: Expiry time too long ({expires_seconds}s)\n  Maximum allowed: {max_expiry}s (7 days)"

        if expires_seconds < 60:
            return "✗ Error: Expiry time must be at least 60 seconds"

        # First, get the dashboard
        dash_url = f"{GRAFANA_URL}/api/dashboards/uid/{dashboard_uid}"
        headers = _get_grafana_headers()
        auth = _get_grafana_auth()

        dash_response = requests.get(
            dash_url, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )
        dash_response.raise_for_status()

        dashboard_data = dash_response.json().get("dashboard", {})

        # Create snapshot
        snapshot_url = f"{GRAFANA_URL}/api/snapshots"

        snapshot_name = (
            name
            or f"Incident snapshot - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        payload = {
            "dashboard": dashboard_data,
            "name": snapshot_name,
            "expires": expires_seconds,
        }

        response = requests.post(
            snapshot_url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        result = response.json()
        snap_url = result.get("url", "unknown")
        snap_key = result.get("key", "unknown")
        delete_key = result.get("deleteKey", "unknown")

        expires_at = datetime.utcnow().timestamp() + expires_seconds
        expires_str = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d %H:%M:%S")

        output = [
            "✓ Dashboard snapshot created",
            f"Name: {snapshot_name}",
            f"URL: {GRAFANA_URL}{snap_url}",
            f"Key: {snap_key}",
            f"Expires: {expires_str} UTC ({expires_seconds}s from now)",
            "",
            f"Delete Key: {delete_key}",
            "💡 Save this URL for incident documentation",
        ]

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return f"✗ Error: Cannot connect to Grafana at {GRAFANA_URL}\n  Verify Grafana is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Grafana request timed out (>10s)\n  Grafana may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"✗ Error: Dashboard UID '{dashboard_uid}' not found\n  Use list_dashboards() to see available dashboards"
        if e.response.status_code == 401:
            return "✗ Error: Grafana authentication failed\n  Check GRAFANA_API_KEY or GRAFANA_USERNAME/PASSWORD"
        return (
            f"✗ HTTP Error from Grafana: {e.response.status_code}\n  {e.response.text}"
        )
    except Exception as e:
        return f"✗ Error creating Grafana snapshot: {str(e)}"


@tool("List Grafana Datasources")
def list_datasources() -> str:
    """
    List all configured Grafana datasources and their health.

    Returns:
        String with datasource names, types, URLs, and health status

    Use Cases:
        - Verify Prometheus datasource configured
        - Check datasource connectivity
        - Troubleshoot dashboard data issues
        - Audit datasource configuration
    """
    try:
        url = f"{GRAFANA_URL}/api/datasources"
        headers = _get_grafana_headers()
        auth = _get_grafana_auth()

        response = requests.get(
            url, headers=headers, auth=auth, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        datasources = response.json()

        if not datasources:
            return "No datasources configured in Grafana"

        output = [
            "=== Grafana Datasources ===",
            f"Total datasources: {len(datasources)}",
            "",
        ]

        for ds in datasources:
            name = ds.get("name", "unknown")
            ds_type = ds.get("type", "unknown")
            url_val = ds.get("url", "N/A")
            uid = ds.get("uid", "unknown")
            is_default = ds.get("isDefault", False)

            output.append(f"• {name} ({ds_type})")
            output.append(f"  UID: {uid}")
            output.append(f"  URL: {url_val}")
            if is_default:
                output.append("  Default: ✓ Yes")
            output.append("")

        # Try to health check Prometheus datasource if exists
        prom_ds = next(
            (ds for ds in datasources if ds.get("type") == "prometheus"), None
        )
        if prom_ds:
            output.append("💡 Prometheus datasource detected")
            output.append(f"   Use query_prometheus tool for direct queries")

        return "\n".join(output)

    except requests.exceptions.ConnectionError:
        return f"✗ Error: Cannot connect to Grafana at {GRAFANA_URL}\n  Verify Grafana is running and accessible"
    except requests.exceptions.Timeout:
        return "✗ Error: Grafana request timed out (>10s)\n  Grafana may be overloaded or unresponsive"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "✗ Error: Grafana authentication failed\n  Check GRAFANA_API_KEY or GRAFANA_USERNAME/PASSWORD"
        return (
            f"✗ HTTP Error from Grafana: {e.response.status_code}\n  {e.response.text}"
        )
    except Exception as e:
        return f"✗ Error listing Grafana datasources: {str(e)}"
