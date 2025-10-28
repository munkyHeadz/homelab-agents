"""AdGuard Home DNS monitoring tools for AI agents."""

import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from crewai.tools import tool
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

# AdGuard Home Configuration
ADGUARD_ENABLED = os.getenv("ADGUARD_ENABLED", "false").lower() == "true"
ADGUARD_USE_CLOUD_API = os.getenv("ADGUARD_USE_CLOUD_API", "false").lower() == "true"
ADGUARD_HOST = os.getenv("ADGUARD_HOST", "192.168.1.104")
ADGUARD_PORT = os.getenv("ADGUARD_PORT", "3000")
ADGUARD_USERNAME = os.getenv("ADGUARD_USERNAME", "")
ADGUARD_PASSWORD = os.getenv("ADGUARD_PASSWORD", "")

# Construct base URL
ADGUARD_BASE_URL = f"http://{ADGUARD_HOST}:{ADGUARD_PORT}"


def _make_adguard_request(
    endpoint: str, method: str = "GET", data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Make a request to the AdGuard Home API.

    Args:
        endpoint: API endpoint path (e.g., "control/status" or "control/stats")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Optional request body data

    Returns:
        API response as dictionary

    Raises:
        Exception: If API request fails
    """
    if not ADGUARD_ENABLED:
        raise Exception(
            "AdGuard integration is disabled. Set ADGUARD_ENABLED=true in .env"
        )

    if not ADGUARD_USERNAME or not ADGUARD_PASSWORD:
        raise Exception(
            "AdGuard credentials not configured. "
            "Set ADGUARD_USERNAME and ADGUARD_PASSWORD in .env"
        )

    url = f"{ADGUARD_BASE_URL}/{endpoint}"
    auth = HTTPBasicAuth(ADGUARD_USERNAME, ADGUARD_PASSWORD)

    try:
        if method == "GET":
            response = requests.get(url, auth=auth, timeout=10)
        elif method == "POST":
            response = requests.post(url, auth=auth, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, auth=auth, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, auth=auth, timeout=10)
        else:
            raise Exception(f"Unsupported HTTP method: {method}")

        response.raise_for_status()

        # Some endpoints return empty responses
        if response.text:
            return response.json()
        return {}

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception(
                "AdGuard API authentication failed (401 Unauthorized). "
                "Check ADGUARD_USERNAME and ADGUARD_PASSWORD in .env"
            )
        elif e.response.status_code == 403:
            raise Exception(
                "AdGuard API permission denied (403 Forbidden). "
                "User may not have admin privileges."
            )
        elif e.response.status_code == 404:
            raise Exception(f"AdGuard API endpoint not found (404): {endpoint}")
        else:
            raise Exception(
                f"AdGuard API error ({e.response.status_code}): {e.response.text}"
            )

    except requests.exceptions.Timeout:
        raise Exception(
            f"AdGuard API request timed out after 10 seconds (host: {ADGUARD_HOST}:{ADGUARD_PORT})"
        )

    except requests.exceptions.ConnectionError:
        raise Exception(
            f"Cannot connect to AdGuard Home at {ADGUARD_HOST}:{ADGUARD_PORT}. "
            "Check that AdGuard Home is running and accessible."
        )

    except requests.exceptions.RequestException as e:
        raise Exception(f"AdGuard API request failed: {str(e)}")


@tool("Check AdGuard Status")
def check_adguard_status() -> str:
    """
    Check the status and health of AdGuard Home DNS service.

    Returns:
        Formatted string with AdGuard status including:
        - Running status
        - Protection enabled/disabled
        - Version information
        - DNS addresses and port
        - HTTP interface port
        - DHCP availability

    Health indicators:
    - ✅ Running with protection enabled
    - ⚠️ Running but protection disabled
    - ❌ Not running or errors

    Use cases:
    - Verify AdGuard service is operational
    - Check DNS filtering protection status
    - Monitor service configuration
    - Detect service failures
    - Troubleshoot DNS issues
    """
    try:
        status = _make_adguard_request("control/status")

        running = status.get("running", False)
        protection_enabled = status.get("protection_enabled", False)
        version = status.get("version", "Unknown")
        dns_addresses = status.get("dns_addresses", [])
        dns_port = status.get("dns_port", 53)
        http_port = status.get("http_port", 3000)
        dhcp_available = status.get("dhcp_available", False)

        output = ["🛡️ AdGuard Home Status\n"]

        # Determine overall health
        if running and protection_enabled:
            health_emoji = "✅"
            health_status = "Healthy - Protection Active"
        elif running and not protection_enabled:
            health_emoji = "⚠️"
            health_status = "Running - Protection Disabled"
        else:
            health_emoji = "❌"
            health_status = "Not Running"

        output.append(f"{health_emoji} **Status**: {health_status}")
        output.append(f"**Version**: {version}")
        output.append(f"**DNS Port**: {dns_port}")
        output.append(f"**Web Interface**: {http_port}")

        if dns_addresses:
            # Show first 3 DNS addresses
            dns_display = dns_addresses[:3]
            output.append(f"**DNS Addresses**:")
            for addr in dns_display:
                output.append(f"  • {addr}")
            if len(dns_addresses) > 3:
                output.append(f"  ... and {len(dns_addresses) - 3} more")

        output.append(
            f"**DHCP Server**: {'Available' if dhcp_available else 'Not Available'}"
        )

        if not protection_enabled:
            output.append(
                f"\n⚠️ **Warning**: DNS filtering protection is currently disabled!"
            )
            output.append(f"   Ads and trackers are NOT being blocked.")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking AdGuard status: {str(e)}"


@tool("Get DNS Query Statistics")
def get_dns_query_stats() -> str:
    """
    Get DNS query statistics and analytics from AdGuard Home.

    Returns:
        Formatted string with DNS query statistics including:
        - Total DNS queries
        - Blocked queries count and percentage
        - Top queried domains
        - Top blocked domains
        - Query types distribution
        - Average processing time

    Use cases:
    - Monitor DNS query volume
    - Track blocking effectiveness
    - Identify most queried domains
    - Detect suspicious DNS activity
    - Analyze DNS traffic patterns
    - Capacity planning
    """
    try:
        stats = _make_adguard_request("control/stats")

        time_units = stats.get("time_units", "hours")
        num_dns_queries = stats.get("num_dns_queries", 0)
        num_blocked_filtering = stats.get("num_blocked_filtering", 0)
        num_replaced_safebrowsing = stats.get("num_replaced_safebrowsing", 0)
        num_replaced_parental = stats.get("num_replaced_parental", 0)
        avg_processing_time = stats.get("avg_processing_time", 0)

        top_queried_domains = stats.get("top_queried_domains", [])
        top_blocked_domains = stats.get("top_blocked_domains", [])

        output = ["📊 DNS Query Statistics\n"]

        # Calculate total blocked
        total_blocked = (
            num_blocked_filtering + num_replaced_safebrowsing + num_replaced_parental
        )
        block_percentage = (
            (total_blocked / num_dns_queries * 100) if num_dns_queries > 0 else 0
        )

        output.append(f"**Time Period**: Last 24 {time_units}")
        output.append(f"**Total Queries**: {num_dns_queries:,}")
        output.append(
            f"**Blocked Queries**: {total_blocked:,} ({block_percentage:.1f}%)"
        )

        if num_blocked_filtering > 0:
            output.append(f"  • Ad/Tracker Blocking: {num_blocked_filtering:,}")
        if num_replaced_safebrowsing > 0:
            output.append(f"  • Malware/Phishing: {num_replaced_safebrowsing:,}")
        if num_replaced_parental > 0:
            output.append(f"  • Parental Control: {num_replaced_parental:,}")

        output.append(f"**Avg Processing Time**: {avg_processing_time:.2f}ms")

        # Blocking effectiveness indicator
        if block_percentage > 20:
            output.append(f"\n🛡️ **High blocking rate** - Excellent protection")
        elif block_percentage > 10:
            output.append(f"\n✅ **Good blocking rate** - Effective protection")
        elif block_percentage > 0:
            output.append(f"\n⚠️ **Low blocking rate** - Check blocklists")
        else:
            output.append(f"\n❌ **No blocking** - Protection may be disabled")

        # Top queried domains
        if top_queried_domains:
            output.append(f"\n**Top Queried Domains**:")
            for i, domain_dict in enumerate(top_queried_domains[:5], 1):
                for domain, count in domain_dict.items():
                    output.append(f"  {i}. {domain}: {count:,} queries")

        # Top blocked domains
        if top_blocked_domains:
            output.append(f"\n**Top Blocked Domains**:")
            for i, domain_dict in enumerate(top_blocked_domains[:5], 1):
                for domain, count in domain_dict.items():
                    output.append(f"  {i}. {domain}: {count:,} blocks")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting DNS statistics: {str(e)}"


@tool("Check AdGuard Blocklist Status")
def check_blocklist_status() -> str:
    """
    Check the status of DNS blocklists and filtering rules.

    Returns:
        Formatted string with blocklist information including:
        - Number of active filters
        - Total rules count
        - Last update timestamp
        - Enabled/disabled filters
        - Filter sources

    Use cases:
    - Verify blocklists are up to date
    - Check filter counts
    - Monitor filter updates
    - Troubleshoot blocking issues
    - Audit filtering configuration
    """
    try:
        filtering = _make_adguard_request("control/filtering/status")

        enabled = filtering.get("enabled", False)
        interval = filtering.get("interval", 0)
        filters = filtering.get("filters", [])
        whitelist_filters = filtering.get("whitelist_filters", [])
        user_rules_count = filtering.get("user_rules", [])

        output = ["📋 AdGuard Blocklist Status\n"]

        if enabled:
            output.append(f"✅ **Filtering**: Enabled")
        else:
            output.append(f"❌ **Filtering**: Disabled")

        output.append(f"**Update Interval**: Every {interval} hours")

        # Count active filters and total rules
        active_filters = [f for f in filters if f.get("enabled", False)]
        total_rules = sum(f.get("rules_count", 0) for f in active_filters)

        output.append(f"**Active Filters**: {len(active_filters)} of {len(filters)}")
        output.append(f"**Total Rules**: {total_rules:,}")

        if isinstance(user_rules_count, list):
            output.append(f"**Custom Rules**: {len(user_rules_count)}")

        if whitelist_filters:
            output.append(f"**Whitelist Filters**: {len(whitelist_filters)}")

        # Show filter details
        if active_filters:
            output.append(f"\n**Active Blocklists**:")
            for f in active_filters[:5]:  # Show first 5
                name = f.get("name", "Unknown")
                rules_count = f.get("rules_count", 0)
                last_updated = f.get("last_updated", "")

                if last_updated:
                    # Parse timestamp
                    try:
                        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                        time_ago = datetime.now().replace(tzinfo=dt.tzinfo) - dt
                        days_ago = time_ago.days
                        if days_ago == 0:
                            updated_str = "Today"
                        elif days_ago == 1:
                            updated_str = "Yesterday"
                        else:
                            updated_str = f"{days_ago} days ago"
                    except:
                        updated_str = "Unknown"
                else:
                    updated_str = "Never"

                output.append(f"  • {name}")
                output.append(f"    Rules: {rules_count:,} | Updated: {updated_str}")

            if len(active_filters) > 5:
                output.append(f"  ... and {len(active_filters) - 5} more filters")

        # Warnings
        if not enabled:
            output.append(
                f"\n⚠️ **Warning**: Filtering is disabled - no blocking active!"
            )
        elif total_rules < 10000:
            output.append(
                f"\n⚠️ **Warning**: Low rule count - consider enabling more blocklists"
            )

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error checking blocklist status: {str(e)}"


@tool("Monitor DNS Clients")
def monitor_dns_clients() -> str:
    """
    Monitor DNS client activity and query patterns.

    Returns:
        Formatted string with DNS client information including:
        - Top clients by query count
        - Client query statistics
        - Per-client blocking stats
        - Unusual activity detection

    Use cases:
    - Identify most active DNS clients
    - Track client query patterns
    - Detect DNS abuse or misconfiguration
    - Troubleshoot client-specific issues
    - Monitor device activity
    """
    try:
        stats = _make_adguard_request("control/stats")

        top_clients = stats.get("top_clients", [])

        if not top_clients:
            return "ℹ️ No DNS client data available"

        output = ["👥 DNS Client Activity\n"]

        total_queries = sum(
            count for client_dict in top_clients for count in client_dict.values()
        )

        output.append(f"**Total Queries**: {total_queries:,}")
        output.append(f"**Active Clients**: {len(top_clients)}")

        output.append(f"\n**Top Clients by Query Count**:")

        for i, client_dict in enumerate(top_clients[:10], 1):
            for client, count in client_dict.items():
                percentage = (count / total_queries * 100) if total_queries > 0 else 0

                # Determine if activity is unusual
                if percentage > 40:
                    warning = " ⚠️ Very high activity"
                elif percentage > 20:
                    warning = " 📊 High activity"
                else:
                    warning = ""

                output.append(f"  {i}. {client}")
                output.append(f"     {count:,} queries ({percentage:.1f}%){warning}")

        # Warnings
        if len(top_clients) > 0:
            top_client = list(top_clients[0].values())[0]
            top_percentage = (
                (top_client / total_queries * 100) if total_queries > 0 else 0
            )

            if top_percentage > 50:
                output.append(
                    f"\n⚠️ **Alert**: One client is generating over 50% of DNS traffic!"
                )
                output.append(f"   This may indicate misconfiguration or DNS abuse.")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error monitoring DNS clients: {str(e)}"


@tool("Get AdGuard Protection Summary")
def get_adguard_protection_summary() -> str:
    """
    Get a comprehensive summary of AdGuard Home protection status.

    Returns:
        Formatted string with overall protection summary including:
        - Service health status
        - Protection enabled/disabled
        - Query statistics overview
        - Blocking effectiveness
        - Active filter count
        - Recent activity summary
        - Any warnings or alerts

    Use cases:
    - Quick health check dashboard
    - Overall protection status
    - Incident detection
    - Status reporting
    - Proactive monitoring
    """
    try:
        # Get status
        status = _make_adguard_request("control/status")
        running = status.get("running", False)
        protection_enabled = status.get("protection_enabled", False)
        version = status.get("version", "Unknown")

        # Get stats
        stats = _make_adguard_request("control/stats")
        num_dns_queries = stats.get("num_dns_queries", 0)
        num_blocked_filtering = stats.get("num_blocked_filtering", 0)
        num_replaced_safebrowsing = stats.get("num_replaced_safebrowsing", 0)
        num_replaced_parental = stats.get("num_replaced_parental", 0)

        # Get filtering status
        filtering = _make_adguard_request("control/filtering/status")
        filters = filtering.get("filters", [])
        active_filters = [f for f in filters if f.get("enabled", False)]
        total_rules = sum(f.get("rules_count", 0) for f in active_filters)

        output = ["🛡️ AdGuard Protection Summary\n"]

        # Overall health
        if running and protection_enabled:
            output.append(f"**Status**: ✅ Fully Protected")
        elif running and not protection_enabled:
            output.append(f"**Status**: ⚠️ Running Without Protection")
        else:
            output.append(f"**Status**: ❌ Service Down")

        output.append(f"**Version**: {version}")

        # Query statistics (last 24 hours)
        total_blocked = (
            num_blocked_filtering + num_replaced_safebrowsing + num_replaced_parental
        )
        block_percentage = (
            (total_blocked / num_dns_queries * 100) if num_dns_queries > 0 else 0
        )

        output.append(f"\n**DNS Queries (24h)**: {num_dns_queries:,}")
        output.append(f"**Blocked (24h)**: {total_blocked:,} ({block_percentage:.1f}%)")

        # Blocking breakdown
        if total_blocked > 0:
            output.append(f"\n**Blocking Breakdown**:")
            if num_blocked_filtering > 0:
                output.append(f"  • Ads/Trackers: {num_blocked_filtering:,}")
            if num_replaced_safebrowsing > 0:
                output.append(f"  • Malware/Phishing: {num_replaced_safebrowsing:,}")
            if num_replaced_parental > 0:
                output.append(f"  • Parental Control: {num_replaced_parental:,}")

        # Filtering configuration
        output.append(f"\n**Active Blocklists**: {len(active_filters)}")
        output.append(f"**Total Rules**: {total_rules:,}")

        # Overall assessment
        output.append(f"\n**Protection Assessment**:")

        issues = []
        if not running:
            issues.append("❌ Service not running")
        if not protection_enabled:
            issues.append("❌ Protection disabled")
        if running and protection_enabled and total_rules < 10000:
            issues.append("⚠️ Low rule count - consider more blocklists")
        if (
            running
            and protection_enabled
            and block_percentage < 5
            and num_dns_queries > 1000
        ):
            issues.append("⚠️ Low blocking rate - check configuration")

        if issues:
            for issue in issues:
                output.append(f"  {issue}")
        else:
            output.append(f"  ✅ All systems operational")
            output.append(f"  ✅ Blocking {total_blocked:,} threats per day")
            output.append(f"  ✅ {total_rules:,} protection rules active")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error getting protection summary: {str(e)}"
