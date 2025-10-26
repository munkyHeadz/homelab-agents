"""Cloudflare monitoring and management tools for AI agents."""

import os
import requests
from crewai.tools import tool
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Cloudflare API Configuration
CLOUDFLARE_ENABLED = os.getenv("CLOUDFLARE_ENABLED", "false").lower() == "true"
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


def _make_cloudflare_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Make a request to the Cloudflare API.

    Args:
        endpoint: API endpoint path (e.g., "zones" or "zones/{zone_id}/dns_records")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Optional request body data

    Returns:
        API response as dictionary

    Raises:
        Exception: If API request fails
    """
    if not CLOUDFLARE_ENABLED:
        raise Exception("Cloudflare integration is disabled. Set CLOUDFLARE_ENABLED=true in .env")

    if not CLOUDFLARE_API_TOKEN:
        raise Exception("Cloudflare API token not configured. Set CLOUDFLARE_API_TOKEN in .env")

    url = f"{CLOUDFLARE_API_BASE}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise Exception(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception(
                "Cloudflare API authentication failed (401 Unauthorized). "
                "The API token may be invalid or expired. "
                "Generate a new token at https://dash.cloudflare.com/profile/api-tokens"
            )
        elif e.response.status_code == 403:
            raise Exception(
                "Cloudflare API permission denied (403 Forbidden). "
                "The API token doesn't have permission for this operation. "
                "Check token permissions at https://dash.cloudflare.com/profile/api-tokens"
            )
        elif e.response.status_code == 404:
            raise Exception(f"Cloudflare API endpoint not found (404): {endpoint}")
        else:
            raise Exception(f"Cloudflare API error ({e.response.status_code}): {e.response.text}")

    except requests.exceptions.Timeout:
        raise Exception("Cloudflare API request timed out after 10 seconds")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Cloudflare API request failed: {str(e)}")


@tool("List Cloudflare Zones")
def list_cloudflare_zones() -> str:
    """
    List all Cloudflare zones (domains) in the account.

    Returns:
        Formatted string with zone information including:
        - Zone name (domain)
        - Zone ID
        - Status (active/pending/deactivated)
        - Nameservers
        - Plan level

    Use cases:
    - Inventory all managed domains
    - Check zone status
    - Get zone IDs for other operations
    - Monitor DNS configuration
    """
    try:
        data = _make_cloudflare_request("zones")

        if not data.get("success"):
            errors = data.get("errors", [])
            error_messages = ", ".join([e.get("message", "Unknown error") for e in errors])
            return f"❌ Failed to list zones: {error_messages}"

        zones = data.get("result", [])

        if not zones:
            return "ℹ️ No Cloudflare zones found in this account"

        output = [f"📊 Cloudflare Zones ({len(zones)} total)\n"]

        for zone in zones:
            zone_name = zone.get("name", "Unknown")
            zone_id = zone.get("id", "Unknown")
            status = zone.get("status", "unknown")
            plan = zone.get("plan", {}).get("name", "Unknown")
            nameservers = zone.get("name_servers", [])

            status_emoji = "✅" if status == "active" else "⚠️"

            output.append(f"\n{status_emoji} **{zone_name}**")
            output.append(f"  Zone ID: {zone_id}")
            output.append(f"  Status: {status}")
            output.append(f"  Plan: {plan}")
            if nameservers:
                output.append(f"  Nameservers: {', '.join(nameservers[:2])}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error listing Cloudflare zones: {str(e)}"


@tool("Check Cloudflare Zone Health")
def check_zone_health(zone_name: Optional[str] = None) -> str:
    """
    Check the health and status of Cloudflare zones.

    Args:
        zone_name: Optional specific zone (domain) to check. If None, checks all zones.

    Returns:
        Formatted string with zone health information:
        - Zone status (active/inactive/pending)
        - DNS configuration status
        - SSL/TLS status
        - Security settings status
        - Recent activity

    Health indicators:
    - ✅ Active and properly configured
    - ⚠️ Pending changes or configuration issues
    - ❌ Inactive or security concerns

    Use cases:
    - Verify zone is operational
    - Check DNS is properly configured
    - Monitor SSL/TLS certificate status
    - Detect configuration drift
    """
    try:
        zones_data = _make_cloudflare_request("zones")

        if not zones_data.get("success"):
            errors = zones_data.get("errors", [])
            error_messages = ", ".join([e.get("message", "Unknown error") for e in errors])
            return f"❌ Failed to get zone health: {error_messages}"

        zones = zones_data.get("result", [])

        if zone_name:
            zones = [z for z in zones if z.get("name") == zone_name]
            if not zones:
                return f"❌ Zone '{zone_name}' not found"

        if not zones:
            return "ℹ️ No zones to check"

        output = [f"🏥 Cloudflare Zone Health ({len(zones)} zone(s))\n"]

        for zone in zones:
            name = zone.get("name", "Unknown")
            zone_id = zone.get("id")
            status = zone.get("status", "unknown")
            paused = zone.get("paused", False)

            # Determine overall health
            if status == "active" and not paused:
                health_emoji = "✅"
                health_status = "Healthy"
            elif status == "pending":
                health_emoji = "⚠️"
                health_status = "Pending Setup"
            elif paused:
                health_emoji = "⏸️"
                health_status = "Paused"
            else:
                health_emoji = "❌"
                health_status = "Unhealthy"

            output.append(f"\n{health_emoji} **{name}** - {health_status}")
            output.append(f"  Status: {status}")
            output.append(f"  Paused: {paused}")

            # Get zone settings
            try:
                settings_data = _make_cloudflare_request(f"zones/{zone_id}/settings")
                if settings_data.get("success"):
                    settings = {s["id"]: s["value"] for s in settings_data.get("result", [])}

                    # SSL/TLS status
                    ssl_mode = settings.get("ssl", "unknown")
                    output.append(f"  SSL/TLS: {ssl_mode}")

                    # Security level
                    security_level = settings.get("security_level", "unknown")
                    output.append(f"  Security Level: {security_level}")

                    # WAF status
                    waf = settings.get("waf", "unknown")
                    output.append(f"  WAF: {waf}")

                    # DDoS protection (always on for all Cloudflare zones)
                    output.append(f"  DDoS Protection: ✅ Active")

            except Exception as e:
                output.append(f"  ⚠️ Could not fetch detailed settings: {str(e)}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking zone health: {str(e)}"


@tool("Get Cloudflare Analytics")
def get_cloudflare_analytics(zone_name: Optional[str] = None, hours: int = 24) -> str:
    """
    Get analytics and traffic statistics for Cloudflare zones.

    Args:
        zone_name: Optional specific zone to analyze. If None, shows all zones.
        hours: Number of hours to look back (default: 24)

    Returns:
        Formatted string with analytics including:
        - Total requests
        - Bandwidth usage
        - Unique visitors
        - Threats blocked
        - Cache hit rate
        - Status code distribution

    Use cases:
    - Monitor traffic patterns
    - Detect traffic spikes or drops
    - Track security threat blocking
    - Analyze cache performance
    - Troubleshoot availability issues
    """
    try:
        zones_data = _make_cloudflare_request("zones")

        if not zones_data.get("success"):
            return "❌ Failed to get zones for analytics"

        zones = zones_data.get("result", [])

        if zone_name:
            zones = [z for z in zones if z.get("name") == zone_name]
            if not zones:
                return f"❌ Zone '{zone_name}' not found"

        if not zones:
            return "ℹ️ No zones to analyze"

        # Calculate time range
        since = datetime.utcnow() - timedelta(hours=hours)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        until_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        output = [f"📊 Cloudflare Analytics (Last {hours} hours)\n"]

        for zone in zones:
            zone_id = zone.get("id")
            name = zone.get("name", "Unknown")

            try:
                # Get analytics dashboard
                analytics_endpoint = (
                    f"zones/{zone_id}/analytics/dashboard"
                    f"?since={since_str}&until={until_str}"
                )
                analytics_data = _make_cloudflare_request(analytics_endpoint)

                if not analytics_data.get("success"):
                    output.append(f"\n⚠️ **{name}**: Could not fetch analytics")
                    continue

                result = analytics_data.get("result", {})
                totals = result.get("totals", {})

                # Extract key metrics
                requests = totals.get("requests", {}).get("all", 0)
                bandwidth = totals.get("bandwidth", {}).get("all", 0)
                threats = totals.get("threats", {}).get("all", 0)
                unique_visitors = totals.get("uniques", {}).get("all", 0)

                # Cache stats
                cached_requests = totals.get("requests", {}).get("cached", 0)
                cache_hit_rate = (cached_requests / requests * 100) if requests > 0 else 0

                # Format bandwidth (bytes to GB)
                bandwidth_gb = bandwidth / (1024 ** 3)

                output.append(f"\n📈 **{name}**")
                output.append(f"  Requests: {requests:,}")
                output.append(f"  Bandwidth: {bandwidth_gb:.2f} GB")
                output.append(f"  Unique Visitors: {unique_visitors:,}")
                output.append(f"  Threats Blocked: {threats:,}")
                output.append(f"  Cache Hit Rate: {cache_hit_rate:.1f}%")

                # Status codes
                http_status = totals.get("requests", {}).get("http_status", {})
                status_2xx = sum(v for k, v in http_status.items() if k.startswith("2"))
                status_4xx = sum(v for k, v in http_status.items() if k.startswith("4"))
                status_5xx = sum(v for k, v in http_status.items() if k.startswith("5"))

                if status_5xx > 0:
                    output.append(f"  ⚠️ 5xx Errors: {status_5xx:,} ({status_5xx/requests*100:.1f}%)")
                if status_4xx > 0:
                    output.append(f"  4xx Errors: {status_4xx:,} ({status_4xx/requests*100:.1f}%)")

            except Exception as e:
                output.append(f"\n⚠️ **{name}**: Error fetching analytics: {str(e)}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting analytics: {str(e)}"


@tool("Check Cloudflare Security Events")
def check_security_events(zone_name: Optional[str] = None, hours: int = 1) -> str:
    """
    Check recent security events and threats blocked by Cloudflare.

    Args:
        zone_name: Optional specific zone to check. If None, checks all zones.
        hours: Number of hours to look back (default: 1)

    Returns:
        Formatted string with security event information:
        - Firewall events (blocks, challenges, logs)
        - Rate limiting triggers
        - Bot traffic patterns
        - DDoS mitigation events
        - WAF rule matches

    Security indicators:
    - 🛡️ Normal threat blocking
    - ⚠️ Elevated threat activity
    - 🚨 Active attack detected

    Use cases:
    - Detect ongoing attacks
    - Monitor firewall effectiveness
    - Investigate blocked traffic
    - Track bot activity
    - Audit security posture
    """
    try:
        zones_data = _make_cloudflare_request("zones")

        if not zones_data.get("success"):
            return "❌ Failed to get zones for security check"

        zones = zones_data.get("result", [])

        if zone_name:
            zones = [z for z in zones if z.get("name") == zone_name]
            if not zones:
                return f"❌ Zone '{zone_name}' not found"

        if not zones:
            return "ℹ️ No zones to check"

        # Calculate time range
        since = datetime.utcnow() - timedelta(hours=hours)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        output = [f"🛡️ Cloudflare Security Events (Last {hours} hour(s))\n"]

        total_events = 0

        for zone in zones:
            zone_id = zone.get("id")
            name = zone.get("name", "Unknown")

            try:
                # Get firewall events
                firewall_endpoint = (
                    f"zones/{zone_id}/firewall/events"
                    f"?since={since_str}&per_page=100"
                )
                firewall_data = _make_cloudflare_request(firewall_endpoint)

                if not firewall_data.get("success"):
                    output.append(f"\n⚠️ **{name}**: Could not fetch security events")
                    continue

                events = firewall_data.get("result", [])
                event_count = len(events)
                total_events += event_count

                if event_count == 0:
                    output.append(f"\n✅ **{name}**: No security events")
                    continue

                # Analyze event types
                actions = {}
                sources = {}

                for event in events:
                    action = event.get("action", "unknown")
                    source = event.get("source", "unknown")

                    actions[action] = actions.get(action, 0) + 1
                    sources[source] = sources.get(source, 0) + 1

                # Determine threat level
                blocked = actions.get("block", 0) + actions.get("challenge", 0)
                if blocked > 100:
                    threat_emoji = "🚨"
                    threat_level = "High Activity"
                elif blocked > 10:
                    threat_emoji = "⚠️"
                    threat_level = "Elevated"
                else:
                    threat_emoji = "🛡️"
                    threat_level = "Normal"

                output.append(f"\n{threat_emoji} **{name}** - {threat_level}")
                output.append(f"  Total Events: {event_count}")

                # Show action breakdown
                for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
                    output.append(f"  {action.title()}: {count}")

                # Show top sources
                top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_sources:
                    output.append(f"  Top Sources: {', '.join([f'{s} ({c})' for s, c in top_sources])}")

            except Exception as e:
                output.append(f"\n⚠️ **{name}**: Error checking security: {str(e)}")

        if total_events == 0:
            output.append("\n✅ No security events detected across all zones")
        else:
            output.append(f"\n📊 Total security events: {total_events}")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking security events: {str(e)}"


@tool("Monitor Cloudflare DNS Records")
def monitor_dns_records(zone_name: str) -> str:
    """
    Monitor DNS records for a specific Cloudflare zone.

    Args:
        zone_name: Domain name to check DNS records for

    Returns:
        Formatted string with DNS record information:
        - Record type (A, AAAA, CNAME, MX, TXT, etc.)
        - Record name
        - Record content/value
        - Proxied status (orange cloud)
        - TTL

    Use cases:
    - Audit DNS configuration
    - Verify record changes
    - Troubleshoot DNS issues
    - Monitor for unauthorized changes
    - Check proxy status
    """
    try:
        # Get zone ID first
        zones_data = _make_cloudflare_request("zones")

        if not zones_data.get("success"):
            return "❌ Failed to get zones"

        zones = [z for z in zones_data.get("result", []) if z.get("name") == zone_name]

        if not zones:
            return f"❌ Zone '{zone_name}' not found"

        zone_id = zones[0].get("id")

        # Get DNS records
        dns_data = _make_cloudflare_request(f"zones/{zone_id}/dns_records?per_page=100")

        if not dns_data.get("success"):
            errors = dns_data.get("errors", [])
            error_messages = ", ".join([e.get("message", "Unknown error") for e in errors])
            return f"❌ Failed to get DNS records: {error_messages}"

        records = dns_data.get("result", [])

        if not records:
            return f"ℹ️ No DNS records found for {zone_name}"

        output = [f"🌐 DNS Records for **{zone_name}** ({len(records)} records)\n"]

        # Group records by type
        by_type = {}
        for record in records:
            record_type = record.get("type", "UNKNOWN")
            if record_type not in by_type:
                by_type[record_type] = []
            by_type[record_type].append(record)

        # Display records grouped by type
        for record_type in sorted(by_type.keys()):
            records_of_type = by_type[record_type]
            output.append(f"\n**{record_type} Records ({len(records_of_type)}):**")

            for record in records_of_type[:10]:  # Limit to first 10 per type
                name = record.get("name", "Unknown")
                content = record.get("content", "")
                proxied = record.get("proxied", False)
                ttl = record.get("ttl", 1)

                proxy_status = "🟠 Proxied" if proxied else "⚪ DNS Only"
                ttl_display = "Auto" if ttl == 1 else f"{ttl}s"

                # Truncate long content
                if len(content) > 60:
                    content = content[:57] + "..."

                output.append(f"  • {name}")
                output.append(f"    → {content}")
                output.append(f"    {proxy_status} | TTL: {ttl_display}")

            if len(records_of_type) > 10:
                output.append(f"  ... and {len(records_of_type) - 10} more")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error monitoring DNS records: {str(e)}"


@tool("Get Cloudflare Status Summary")
def get_cloudflare_status() -> str:
    """
    Get a comprehensive status summary of all Cloudflare services.

    Returns:
        Formatted string with overall Cloudflare status:
        - Zone count and health
        - Recent traffic statistics
        - Security event summary
        - SSL/TLS status
        - Cache performance
        - Any warnings or alerts

    Use cases:
    - Quick health check
    - Dashboard overview
    - Incident detection
    - Status reporting
    - Proactive monitoring
    """
    try:
        zones_data = _make_cloudflare_request("zones")

        if not zones_data.get("success"):
            return "❌ Failed to get Cloudflare status"

        zones = zones_data.get("result", [])

        if not zones:
            return "ℹ️ No Cloudflare zones configured"

        output = ["🌐 Cloudflare Status Summary\n"]

        # Zone overview
        active_zones = sum(1 for z in zones if z.get("status") == "active" and not z.get("paused"))
        total_zones = len(zones)

        if active_zones == total_zones:
            zone_status = f"✅ All zones active ({total_zones})"
        else:
            zone_status = f"⚠️ {active_zones}/{total_zones} zones active"

        output.append(f"**Zones**: {zone_status}")

        # Quick stats from last hour
        since = datetime.utcnow() - timedelta(hours=1)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        until_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        total_requests = 0
        total_threats = 0
        total_bandwidth = 0
        zones_with_errors = []

        for zone in zones:
            zone_id = zone.get("id")
            name = zone.get("name")

            try:
                analytics_endpoint = (
                    f"zones/{zone_id}/analytics/dashboard"
                    f"?since={since_str}&until={until_str}"
                )
                analytics_data = _make_cloudflare_request(analytics_endpoint)

                if analytics_data.get("success"):
                    totals = analytics_data.get("result", {}).get("totals", {})

                    requests = totals.get("requests", {}).get("all", 0)
                    threats = totals.get("threats", {}).get("all", 0)
                    bandwidth = totals.get("bandwidth", {}).get("all", 0)

                    total_requests += requests
                    total_threats += threats
                    total_bandwidth += bandwidth

                    # Check for 5xx errors
                    http_status = totals.get("requests", {}).get("http_status", {})
                    status_5xx = sum(v for k, v in http_status.items() if k.startswith("5"))

                    if status_5xx > 0:
                        error_rate = status_5xx / requests * 100 if requests > 0 else 0
                        if error_rate > 5:
                            zones_with_errors.append(f"{name} ({error_rate:.1f}% errors)")

            except Exception:
                pass

        # Display metrics
        bandwidth_gb = total_bandwidth / (1024 ** 3)

        output.append(f"**Requests (1h)**: {total_requests:,}")
        output.append(f"**Bandwidth (1h)**: {bandwidth_gb:.2f} GB")
        output.append(f"**Threats Blocked (1h)**: {total_threats:,}")

        # Warnings
        if zones_with_errors:
            output.append(f"\n⚠️ **Zones with Errors**:")
            for zone_error in zones_with_errors:
                output.append(f"  • {zone_error}")
        else:
            output.append(f"\n✅ **No errors detected**")

        # Overall status
        if active_zones == total_zones and not zones_with_errors:
            output.append(f"\n🎯 **Overall Status**: ✅ Healthy")
        elif zones_with_errors:
            output.append(f"\n🎯 **Overall Status**: ⚠️ Degraded")
        else:
            output.append(f"\n🎯 **Overall Status**: ⚠️ Issues Detected")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting Cloudflare status: {str(e)}"
