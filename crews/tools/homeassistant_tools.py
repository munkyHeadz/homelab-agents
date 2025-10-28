"""Home Assistant monitoring tools for homelab agents.

Home Assistant REST API integration for smart home device monitoring,
automation tracking, and entity state management.

API Documentation: https://developers.home-assistant.io/docs/api/rest/
"""

import os
from typing import Any, Dict, List, Optional

import requests
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Home Assistant configuration
HOMEASSISTANT_ENABLED = os.getenv("HOMEASSISTANT_ENABLED", "false").lower() == "true"
HOMEASSISTANT_URL = os.getenv("HOMEASSISTANT_URL", "http://192.168.1.108:8123")
HOMEASSISTANT_TOKEN = os.getenv("HOMEASSISTANT_TOKEN", "")

# Common error messages
ERROR_NOT_CONFIGURED = (
    "❌ Home Assistant not configured (HOMEASSISTANT_TOKEN missing in .env)"
)
ERROR_DISABLED = "⚠️ Home Assistant monitoring disabled (HOMEASSISTANT_ENABLED=false)"


def _make_homeassistant_request(
    endpoint: str, method: str = "GET", data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Make HTTP request to Home Assistant REST API.

    Args:
        endpoint: API endpoint (e.g., 'states', 'services')
        method: HTTP method (GET, POST, etc.)
        data: Optional request payload

    Returns:
        JSON response as dictionary

    Raises:
        Exception: On API errors with detailed messages
    """
    if not HOMEASSISTANT_ENABLED:
        raise Exception(ERROR_DISABLED)

    if not HOMEASSISTANT_TOKEN:
        raise Exception(ERROR_NOT_CONFIGURED)

    url = f"{HOMEASSISTANT_URL}/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {HOMEASSISTANT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise Exception(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        raise Exception(
            f"⏱️ Home Assistant API timeout. Service may be down or unreachable.\n"
            f"URL: {HOMEASSISTANT_URL}\n"
            f"💡 Check: Service status, network connectivity, firewall rules"
        )
    except requests.exceptions.ConnectionError:
        raise Exception(
            f"🔌 Cannot connect to Home Assistant API.\n"
            f"URL: {HOMEASSISTANT_URL}\n"
            f"💡 Check: Service is running, URL is correct, network is accessible"
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception(
                f"🔐 Home Assistant API authentication failed (401 Unauthorized).\n"
                f"💡 Action required:\n"
                f"   1. Go to {HOMEASSISTANT_URL}/profile/security\n"
                f"   2. Create a new Long-Lived Access Token\n"
                f"   3. Update HOMEASSISTANT_TOKEN in .env\n"
                f"   4. Restart homelab-agents container"
            )
        elif e.response.status_code == 404:
            raise Exception(
                f"❌ Home Assistant API endpoint not found (404).\n"
                f"URL: {url}\n"
                f"💡 Check: API endpoint path, Home Assistant version compatibility"
            )
        else:
            raise Exception(
                f"❌ Home Assistant API error {e.response.status_code}: {e.response.text}"
            )
    except Exception as e:
        raise Exception(
            f"❌ Unexpected error communicating with Home Assistant: {str(e)}"
        )


@tool("Check Home Assistant Status")
def check_homeassistant_status() -> str:
    """
    Check Home Assistant service health and configuration status.

    Returns comprehensive status including:
    - Service availability
    - Version information
    - Configuration validation
    - Component loading status

    Use this for health checks and incident detection.

    Returns:
        Formatted status report or error message
    """
    try:
        # Get config info
        config = _make_homeassistant_request("config")

        version = config.get("version", "Unknown")
        location = config.get("location_name", "Unknown")
        unit_system = config.get("unit_system", {})
        components = config.get("components", [])

        # Get state count
        try:
            states = _make_homeassistant_request("states")
            entity_count = len(states) if isinstance(states, list) else 0
        except:
            entity_count = "Unknown"

        status_report = f"""
✅ Home Assistant Status: ONLINE

🏠 **Instance Information**
   Version: {version}
   Location: {location}
   Temperature: {unit_system.get('temperature', 'Unknown')}

📊 **Entities**
   Total Entities: {entity_count}

🔌 **Components Loaded**
   Count: {len(components)}
   Sample: {', '.join(components[:10])}...

💡 Service is healthy and responding to API requests.
"""
        return status_report.strip()

    except Exception as e:
        return f"""
⚠️ Home Assistant Status: OFFLINE or ERROR

{str(e)}

🔧 **Troubleshooting Steps:**
   1. Check if Home Assistant container/service is running
   2. Verify URL: {HOMEASSISTANT_URL}
   3. Confirm API token is valid
   4. Check network connectivity
   5. Review Home Assistant logs
"""


@tool("List Home Assistant Entities")
def list_homeassistant_entities(domain: Optional[str] = None) -> str:
    """
    List all entities or filter by domain (sensor, switch, light, etc.).

    Args:
        domain: Optional domain filter (e.g., 'sensor', 'switch', 'light', 'binary_sensor')
                If None, lists all entities with domain summary

    Returns:
        Formatted entity list with states and attributes

    Use this for:
    - Discovering available devices
    - Finding specific entity IDs
    - Analyzing entity distribution
    """
    try:
        states = _make_homeassistant_request("states")

        if not isinstance(states, list):
            return "❌ Invalid response format from Home Assistant API"

        # If domain specified, filter
        if domain:
            filtered = [
                s for s in states if s.get("entity_id", "").startswith(f"{domain}.")
            ]
            if not filtered:
                return f"ℹ️ No entities found for domain: {domain}"

            result = [f"📍 **{domain.upper()} Entities** ({len(filtered)} total)\n"]
            for entity in filtered[:50]:  # Limit to 50 for readability
                entity_id = entity.get("entity_id", "unknown")
                state = entity.get("state", "unknown")
                friendly_name = entity.get("attributes", {}).get(
                    "friendly_name", entity_id
                )
                last_changed = entity.get("last_changed", "unknown")

                result.append(
                    f"   • {friendly_name} ({entity_id})\n"
                    f"     State: {state} | Last Changed: {last_changed}"
                )

            if len(filtered) > 50:
                result.append(f"\n... and {len(filtered) - 50} more entities")

            return "\n".join(result)

        # No domain specified - show summary by domain
        domain_counts = {}
        for entity in states:
            entity_domain = entity.get("entity_id", "").split(".")[0]
            domain_counts[entity_domain] = domain_counts.get(entity_domain, 0) + 1

        result = [
            f"📊 **Home Assistant Entity Summary** ({len(states)} total entities)\n"
        ]
        for domain_name, count in sorted(
            domain_counts.items(), key=lambda x: x[1], reverse=True
        ):
            result.append(f"   • {domain_name}: {count} entities")

        result.append("\n💡 Use domain parameter to list specific entity types")
        result.append(
            "   Example domains: sensor, switch, light, binary_sensor, automation"
        )

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error listing Home Assistant entities: {str(e)}"


@tool("Get Entity State")
def get_entity_state(entity_id: str) -> str:
    """
    Get detailed state and attributes for a specific entity.

    Args:
        entity_id: Full entity ID (e.g., 'sensor.temperature_living_room')

    Returns:
        Detailed entity information including state, attributes, and metadata

    Use this for:
    - Checking sensor readings
    - Verifying device states
    - Troubleshooting entity issues
    """
    try:
        state = _make_homeassistant_request(f"states/{entity_id}")

        entity_id = state.get("entity_id", "Unknown")
        current_state = state.get("state", "unknown")
        last_changed = state.get("last_changed", "unknown")
        last_updated = state.get("last_updated", "unknown")
        attributes = state.get("attributes", {})

        # Format attributes
        friendly_name = attributes.get("friendly_name", entity_id)
        unit = attributes.get("unit_of_measurement", "")
        device_class = attributes.get("device_class", "")

        result = [
            f"🔍 **Entity Details: {friendly_name}**\n",
            f"**Entity ID:** {entity_id}",
            f"**Current State:** {current_state} {unit}".strip(),
        ]

        if device_class:
            result.append(f"**Device Class:** {device_class}")

        result.append(f"**Last Changed:** {last_changed}")
        result.append(f"**Last Updated:** {last_updated}")

        # Add interesting attributes
        interesting_attrs = [
            "battery_level",
            "temperature",
            "humidity",
            "brightness",
            "current_position",
            "is_on",
            "available",
            "last_seen",
        ]

        extra_attrs = []
        for key, value in attributes.items():
            if key in interesting_attrs and key not in [
                "friendly_name",
                "unit_of_measurement",
            ]:
                extra_attrs.append(f"   • {key}: {value}")

        if extra_attrs:
            result.append("\n**Additional Attributes:**")
            result.extend(extra_attrs)

        return "\n".join(result)

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return f"❌ Entity not found: {entity_id}\n💡 Use list_homeassistant_entities to find valid entity IDs"
        return f"❌ Error getting entity state: {error_msg}"


@tool("Get Entity History")
def get_entity_history(entity_id: str, hours: int = 24) -> str:
    """
    Get historical state changes for an entity.

    Args:
        entity_id: Full entity ID (e.g., 'sensor.temperature_living_room')
        hours: Number of hours of history to retrieve (default: 24)

    Returns:
        Historical state changes with timestamps

    Use this for:
    - Analyzing trends
    - Investigating state change patterns
    - Troubleshooting flapping sensors
    """
    try:
        from datetime import datetime, timedelta

        # Calculate timestamp for history query
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        timestamp = start_time.isoformat()

        # Note: History endpoint requires timestamp parameter
        history = _make_homeassistant_request(
            f"history/period/{timestamp}?filter_entity_id={entity_id}"
        )

        if not history or not isinstance(history, list) or len(history) == 0:
            return f"ℹ️ No history found for {entity_id} in the last {hours} hours"

        entity_history = history[0] if history else []

        if not entity_history:
            return f"ℹ️ No state changes for {entity_id} in the last {hours} hours"

        result = [
            f"📜 **History for {entity_id}** (last {hours} hours)\n",
            f"Total state changes: {len(entity_history)}\n",
        ]

        # Show last 20 changes
        for i, state in enumerate(entity_history[-20:]):
            state_value = state.get("state", "unknown")
            last_changed = state.get("last_changed", "unknown")
            attributes = state.get("attributes", {})
            unit = attributes.get("unit_of_measurement", "")

            result.append(f"{i + 1}. {last_changed}: {state_value} {unit}".strip())

        if len(entity_history) > 20:
            result.append(f"\n... and {len(entity_history) - 20} earlier changes")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error getting entity history: {str(e)}"


@tool("Check Automation Status")
def check_automation_status() -> str:
    """
    Check status of all Home Assistant automations.

    Returns:
        List of automations with their enabled/disabled status and last triggered time

    Use this for:
    - Verifying automations are running
    - Troubleshooting automation failures
    - Monitoring automation execution
    """
    try:
        states = _make_homeassistant_request("states")

        # Filter for automation entities
        automations = [
            s for s in states if s.get("entity_id", "").startswith("automation.")
        ]

        if not automations:
            return "ℹ️ No automations found in Home Assistant"

        result = [f"🤖 **Home Assistant Automations** ({len(automations)} total)\n"]

        enabled_count = 0
        disabled_count = 0

        for auto in automations:
            entity_id = auto.get("entity_id", "unknown")
            state = auto.get("state", "unknown")
            attributes = auto.get("attributes", {})

            friendly_name = attributes.get("friendly_name", entity_id)
            last_triggered = attributes.get("last_triggered", "Never")

            status_icon = "✅" if state == "on" else "⏸️"

            if state == "on":
                enabled_count += 1
            else:
                disabled_count += 1

            result.append(
                f"{status_icon} **{friendly_name}**\n"
                f"   ID: {entity_id}\n"
                f"   Status: {state.upper()}\n"
                f"   Last Triggered: {last_triggered}"
            )

        result.insert(1, f"Enabled: {enabled_count} | Disabled: {disabled_count}\n")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error checking automation status: {str(e)}"


@tool("Get Home Assistant Summary")
def get_homeassistant_summary() -> str:
    """
    Get comprehensive summary of Home Assistant instance including
    service status, entity counts by domain, and key metrics.

    Returns:
        Dashboard-style summary report

    Use this for:
    - Quick health overview
    - Incident triage
    - Status reporting
    """
    try:
        # Get config
        config = _make_homeassistant_request("config")

        # Get all states
        states = _make_homeassistant_request("states")

        version = config.get("version", "Unknown")
        location = config.get("location_name", "Unknown")

        # Count entities by domain
        domain_counts = {}
        unavailable_count = 0
        for entity in states:
            entity_domain = entity.get("entity_id", "").split(".")[0]
            domain_counts[entity_domain] = domain_counts.get(entity_domain, 0) + 1

            if entity.get("state") == "unavailable":
                unavailable_count += 1

        # Count automations
        automations = [
            s for s in states if s.get("entity_id", "").startswith("automation.")
        ]
        enabled_automations = sum(1 for a in automations if a.get("state") == "on")

        result = [
            "🏠 **Home Assistant Summary Dashboard**\n",
            f"**Instance:** {location}",
            f"**Version:** {version}",
            f"**Total Entities:** {len(states)}",
            f"**Unavailable:** {unavailable_count}",
            "",
        ]

        # Top domains
        result.append("**Entity Breakdown:**")
        for domain, count in sorted(
            domain_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            result.append(f"   • {domain}: {count}")

        # Automation summary
        result.append(
            f"\n**Automations:** {enabled_automations}/{len(automations)} enabled"
        )

        # Health indicator
        health_status = (
            "🟢 HEALTHY"
            if unavailable_count < 5
            else (
                "🟡 CHECK ENTITIES" if unavailable_count < 20 else "🔴 MANY UNAVAILABLE"
            )
        )
        result.append(f"\n**Health:** {health_status}")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error getting Home Assistant summary: {str(e)}"
