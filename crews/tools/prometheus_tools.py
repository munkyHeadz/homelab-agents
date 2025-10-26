"""Expanded Prometheus monitoring tools for homelab agents.

Prometheus API integration for monitoring the monitoring system itself:
targets, rules, alerts, TSDB health, and configuration management.

API Documentation: https://prometheus.io/docs/prometheus/latest/querying/api/
"""

import os
import requests
from typing import Dict, Any, Optional, List
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Prometheus configuration
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://100.67.169.111:9090")

# Common error messages
ERROR_CONNECTION = "❌ Cannot connect to Prometheus API"
ERROR_TIMEOUT = "⏱️ Prometheus API timeout"


def _make_prometheus_request(endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Make HTTP request to Prometheus API.

    Args:
        endpoint: API endpoint (e.g., 'targets', 'rules', 'alerts')
        params: Optional query parameters

    Returns:
        JSON response as dictionary

    Raises:
        Exception: On API errors with detailed messages
    """
    url = f"{PROMETHEUS_URL}/api/v1/{endpoint}"

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        result = response.json()

        if result.get("status") != "success":
            error_type = result.get("errorType", "unknown")
            error_msg = result.get("error", "No error message")
            raise Exception(f"Prometheus API error ({error_type}): {error_msg}")

        return result.get("data", {})

    except requests.exceptions.Timeout:
        raise Exception(
            f"{ERROR_TIMEOUT}\n"
            f"URL: {PROMETHEUS_URL}\n"
            f"💡 Check: Service status, network latency, query complexity"
        )
    except requests.exceptions.ConnectionError:
        raise Exception(
            f"{ERROR_CONNECTION}\n"
            f"URL: {PROMETHEUS_URL}\n"
            f"💡 Check: Service is running, URL is correct, network accessible"
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 503:
            raise Exception(
                f"⚠️ Prometheus service unavailable (503)\n"
                f"Service may be starting up or overloaded\n"
                f"💡 Check: Service logs, resource usage, startup progress"
            )
        else:
            raise Exception(f"❌ Prometheus API HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        if "Prometheus API error" in str(e) or ERROR_CONNECTION in str(e) or ERROR_TIMEOUT in str(e):
            raise
        raise Exception(f"❌ Unexpected error with Prometheus API: {str(e)}")


@tool("Check Prometheus Scrape Targets")
def check_prometheus_targets(state_filter: Optional[str] = None) -> str:
    """
    Monitor Prometheus scrape targets and their health status.

    Args:
        state_filter: Optional filter ('active', 'dropped', or None for all)

    Returns:
        Formatted report of all scrape targets with health status,
        last scrape time, and any errors

    Use this for:
    - Detecting failed scrape targets
    - Monitoring target discovery
    - Troubleshooting data collection issues
    - Verifying service discovery
    """
    try:
        targets = _make_prometheus_request("targets")

        active_targets = targets.get("activeTargets", [])
        dropped_targets = targets.get("droppedTargets", [])

        result = [f"🎯 **Prometheus Scrape Targets**\n"]

        # Active targets
        if state_filter is None or state_filter == "active":
            healthy_count = sum(1 for t in active_targets if t.get("health") == "up")
            unhealthy_count = len(active_targets) - healthy_count

            result.append(f"**Active Targets**: {len(active_targets)}")
            result.append(f"   • Healthy (up): {healthy_count}")
            result.append(f"   • Unhealthy (down): {unhealthy_count}\n")

            # Group by job
            jobs = {}
            for target in active_targets:
                job = target.get("labels", {}).get("job", "unknown")
                if job not in jobs:
                    jobs[job] = {"up": 0, "down": 0, "targets": []}

                health = target.get("health", "unknown")
                if health == "up":
                    jobs[job]["up"] += 1
                else:
                    jobs[job]["down"] += 1
                jobs[job]["targets"].append(target)

            # Show job summaries
            result.append("**Targets by Job:**")
            for job, data in sorted(jobs.items()):
                status_icon = "✅" if data["down"] == 0 else "⚠️"
                result.append(f"{status_icon} {job}: {data['up']} up, {data['down']} down")

                # Show unhealthy targets
                for target in data["targets"]:
                    if target.get("health") != "up":
                        instance = target.get("labels", {}).get("instance", "unknown")
                        last_error = target.get("lastError", "No error message")
                        last_scrape = target.get("lastScrape", "unknown")

                        result.append(f"   ❌ {instance}")
                        result.append(f"      Error: {last_error}")
                        result.append(f"      Last Scrape: {last_scrape}")

        # Dropped targets
        if state_filter is None or state_filter == "dropped":
            if dropped_targets:
                result.append(f"\n**Dropped Targets**: {len(dropped_targets)}")
                result.append("(Targets that were discovered but not scraped due to relabeling)")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error checking Prometheus targets: {str(e)}"


@tool("Check Prometheus Rules")
def check_prometheus_rules(rule_type: Optional[str] = None) -> str:
    """
    Monitor Prometheus recording and alerting rules.

    Args:
        rule_type: Optional filter ('alert' for alerting rules, 'record' for recording rules, None for all)

    Returns:
        Formatted report of all rules with evaluation status, health, and any errors

    Use this for:
    - Detecting rule evaluation failures
    - Monitoring alerting rule health
    - Verifying recording rule execution
    - Troubleshooting rule errors
    """
    try:
        rules_data = _make_prometheus_request("rules")

        groups = rules_data.get("groups", [])

        if not groups:
            return "ℹ️ No Prometheus rules configured"

        result = [f"📋 **Prometheus Rules**\n"]

        total_rules = 0
        healthy_rules = 0
        failed_rules = 0
        alert_rules = 0
        record_rules = 0

        rule_details = []

        for group in groups:
            group_name = group.get("name", "unnamed")
            group_file = group.get("file", "unknown")
            group_interval = group.get("interval", 0)
            group_rules = group.get("rules", [])

            for rule in group_rules:
                total_rules += 1

                rule_name = rule.get("name", "unnamed")
                rule_state = rule.get("state", "unknown")
                rule_health = rule.get("health", "unknown")
                rule_query = rule.get("query", "")
                last_error = rule.get("lastError")
                evaluation_time = rule.get("evaluationTime", 0)

                # Determine rule type
                is_alert = "alerts" in rule
                if is_alert:
                    alert_rules += 1
                    current_type = "alert"
                else:
                    record_rules += 1
                    current_type = "record"

                # Skip if filtering
                if rule_type and rule_type != current_type:
                    continue

                # Count health
                if rule_health == "ok":
                    healthy_rules += 1
                else:
                    failed_rules += 1

                # Build rule detail
                if rule_health != "ok" or (rule_type is None and total_rules <= 20):
                    icon = "🔴" if rule_health != "ok" else "✅" if is_alert else "📊"
                    type_label = "Alert" if is_alert else "Record"

                    rule_detail = [
                        f"{icon} **{rule_name}** ({type_label})",
                        f"   Group: {group_name}",
                        f"   Health: {rule_health}",
                        f"   Evaluation: {evaluation_time:.3f}s"
                    ]

                    if is_alert:
                        rule_detail.append(f"   State: {rule_state}")
                        alerts = rule.get("alerts", [])
                        if alerts:
                            rule_detail.append(f"   Active Alerts: {len(alerts)}")

                    if last_error:
                        rule_detail.append(f"   ❌ Error: {last_error}")

                    rule_details.append("\n".join(rule_detail))

        # Summary
        result.append(f"**Total Rules**: {total_rules}")
        result.append(f"   • Alerting Rules: {alert_rules}")
        result.append(f"   • Recording Rules: {record_rules}")
        result.append(f"   • Healthy: {healthy_rules}")
        result.append(f"   • Failed: {failed_rules}\n")

        # Show rule details
        if rule_details:
            result.append("**Rule Details:**\n")
            result.extend(rule_details)
        elif total_rules > 20:
            result.append("💡 All rules healthy. Use rule_type filter to see specific rules.")

        health_status = "🟢 HEALTHY" if failed_rules == 0 else "🔴 FAILURES DETECTED"
        result.append(f"\n**Status**: {health_status}")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error checking Prometheus rules: {str(e)}"


@tool("Get Prometheus Active Alerts")
def get_prometheus_alerts() -> str:
    """
    Get all active alerts from Prometheus (not Alertmanager).

    Returns:
        Formatted list of firing and pending alerts with labels and annotations

    Use this for:
    - Checking what alerts are currently firing
    - Verifying alert conditions
    - Troubleshooting alerting pipeline
    - Incident triage
    """
    try:
        alerts_data = _make_prometheus_request("alerts")

        alerts = alerts_data.get("alerts", [])

        if not alerts:
            return "✅ No active alerts in Prometheus"

        result = [f"🚨 **Active Prometheus Alerts** ({len(alerts)} total)\n"]

        # Group by state
        firing = [a for a in alerts if a.get("state") == "firing"]
        pending = [a for a in alerts if a.get("state") == "pending"]

        result.append(f"**Firing**: {len(firing)}")
        result.append(f"**Pending**: {len(pending)}\n")

        # Show firing alerts
        if firing:
            result.append("**🔥 Firing Alerts:**\n")
            for alert in firing:
                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})

                alert_name = labels.get("alertname", "Unknown")
                severity = labels.get("severity", "unknown")
                instance = labels.get("instance", "unknown")

                summary = annotations.get("summary", "No summary")
                description = annotations.get("description", "No description")

                result.append(f"🔴 **{alert_name}** ({severity})")
                result.append(f"   Instance: {instance}")
                result.append(f"   Summary: {summary}")
                if description != summary:
                    result.append(f"   Description: {description}")
                result.append("")

        # Show pending alerts
        if pending:
            result.append("**⏳ Pending Alerts:**\n")
            for alert in pending[:5]:  # Limit to 5
                labels = alert.get("labels", {})
                alert_name = labels.get("alertname", "Unknown")
                instance = labels.get("instance", "unknown")

                result.append(f"🟡 **{alert_name}**")
                result.append(f"   Instance: {instance}")
                result.append("")

            if len(pending) > 5:
                result.append(f"... and {len(pending) - 5} more pending alerts")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error getting Prometheus alerts: {str(e)}"


@tool("Check Prometheus TSDB Status")
def check_prometheus_tsdb() -> str:
    """
    Monitor Prometheus Time Series Database (TSDB) health and storage metrics.

    Returns:
        Formatted report with storage stats, series count, chunk count,
        and head stats

    Use this for:
    - Monitoring storage usage and growth
    - Detecting cardinality explosions
    - Verifying TSDB health
    - Capacity planning
    """
    try:
        tsdb_data = _make_prometheus_request("status/tsdb")

        head_stats = tsdb_data.get("headStats", {})
        series_count_by_metric = tsdb_data.get("seriesCountByMetricName", [])
        label_value_counts = tsdb_data.get("labelValueCountByLabelName", [])

        result = [f"💾 **Prometheus TSDB Status**\n"]

        # Head statistics
        num_series = head_stats.get("numSeries", 0)
        num_label_pairs = head_stats.get("numLabelPairs", 0)
        chunk_count = head_stats.get("chunkCount", 0)
        min_time = head_stats.get("minTime", 0)
        max_time = head_stats.get("maxTime", 0)

        result.append(f"**Head Stats:**")
        result.append(f"   • Time Series: {num_series:,}")
        result.append(f"   • Label Pairs: {num_label_pairs:,}")
        result.append(f"   • Chunks: {chunk_count:,}")

        # Calculate time range
        if min_time and max_time:
            time_range_hours = (max_time - min_time) / 1000 / 3600
            result.append(f"   • Head Range: {time_range_hours:.1f} hours")

        # Top metrics by series count
        if series_count_by_metric:
            result.append(f"\n**Top Metrics by Series Count:**")
            for i, metric in enumerate(series_count_by_metric[:10]):
                name = metric.get("name", "unknown")
                count = metric.get("value", 0)
                result.append(f"   {i+1}. {name}: {count:,} series")

        # Label cardinality
        if label_value_counts:
            result.append(f"\n**Label Cardinality (Top 5):**")
            for i, label in enumerate(label_value_counts[:5]):
                name = label.get("name", "unknown")
                count = label.get("value", 0)
                result.append(f"   {i+1}. {name}: {count:,} unique values")

        # Health assessment
        result.append(f"\n**Health Assessment:**")
        if num_series > 1000000:
            result.append("   ⚠️ High series cardinality (>1M) - may impact performance")
        elif num_series > 500000:
            result.append("   🟡 Moderate series cardinality (>500K) - monitor closely")
        else:
            result.append("   ✅ Series cardinality within normal range")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error checking Prometheus TSDB: {str(e)}"


@tool("Get Prometheus Runtime Info")
def get_prometheus_runtime_info() -> str:
    """
    Get Prometheus runtime information and build details.

    Returns:
        Formatted report with version, build info, storage paths,
        and configuration flags

    Use this for:
    - Verifying Prometheus version
    - Checking configuration settings
    - Troubleshooting deployment issues
    - Documentation and compliance
    """
    try:
        runtime_info = _make_prometheus_request("status/runtimeinfo")
        build_info = _make_prometheus_request("status/buildinfo")

        result = [f"ℹ️ **Prometheus Runtime Information**\n"]

        # Build info
        version = build_info.get("version", "unknown")
        revision = build_info.get("revision", "unknown")
        branch = build_info.get("branch", "unknown")
        build_user = build_info.get("buildUser", "unknown")
        build_date = build_info.get("buildDate", "unknown")
        go_version = build_info.get("goVersion", "unknown")

        result.append(f"**Build Information:**")
        result.append(f"   • Version: {version}")
        result.append(f"   • Revision: {revision[:12]}")
        result.append(f"   • Branch: {branch}")
        result.append(f"   • Build Date: {build_date}")
        result.append(f"   • Go Version: {go_version}")

        # Runtime info
        start_time = runtime_info.get("startTime", "unknown")
        cwd = runtime_info.get("CWD", "unknown")
        reload_config_success = runtime_info.get("reloadConfigSuccess", True)
        last_config_time = runtime_info.get("lastConfigTime", "unknown")
        corruption_count = runtime_info.get("corruptionCount", 0)
        goroutine_count = runtime_info.get("goroutineCount", 0)
        gomaxprocs = runtime_info.get("GOMAXPROCS", 0)
        gogc = runtime_info.get("GOGC", "")
        godebug = runtime_info.get("GODEBUG", "")
        storage_retention = runtime_info.get("storageRetention", "unknown")

        result.append(f"\n**Runtime Status:**")
        result.append(f"   • Start Time: {start_time}")
        result.append(f"   • Last Config Reload: {last_config_time}")
        result.append(f"   • Config Reload Success: {'✅' if reload_config_success else '❌'}")
        result.append(f"   • Storage Retention: {storage_retention}")
        result.append(f"   • Goroutines: {goroutine_count}")
        result.append(f"   • GOMAXPROCS: {gomaxprocs}")

        if corruption_count > 0:
            result.append(f"   ⚠️ Corruption Count: {corruption_count}")

        result.append(f"\n**Working Directory:**")
        result.append(f"   {cwd}")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error getting Prometheus runtime info: {str(e)}"


@tool("Get Prometheus Configuration Status")
def get_prometheus_config_status() -> str:
    """
    Get Prometheus configuration status and flag values.

    Returns:
        Formatted report with configuration flags and their values

    Use this for:
    - Verifying configuration settings
    - Troubleshooting configuration issues
    - Auditing Prometheus setup
    - Comparing environments
    """
    try:
        flags = _make_prometheus_request("status/flags")

        if not flags:
            return "ℹ️ No configuration flags returned"

        result = [f"⚙️ **Prometheus Configuration Flags**\n"]

        # Group flags by category
        storage_flags = {}
        query_flags = {}
        web_flags = {}
        other_flags = {}

        for key, value in flags.items():
            if key.startswith("storage."):
                storage_flags[key] = value
            elif key.startswith("query."):
                query_flags[key] = value
            elif key.startswith("web."):
                web_flags[key] = value
            else:
                other_flags[key] = value

        # Show important flags by category
        if storage_flags:
            result.append("**Storage Configuration:**")
            for key, value in sorted(storage_flags.items())[:10]:
                result.append(f"   • {key}: {value}")

        if query_flags:
            result.append("\n**Query Configuration:**")
            for key, value in sorted(query_flags.items()):
                result.append(f"   • {key}: {value}")

        if web_flags:
            result.append("\n**Web Configuration:**")
            for key, value in sorted(web_flags.items())[:5]:
                result.append(f"   • {key}: {value}")

        # Show critical config values
        result.append("\n**Critical Settings:**")
        retention_time = flags.get("storage.tsdb.retention.time", "15d")
        retention_size = flags.get("storage.tsdb.retention.size", "0")
        max_samples = flags.get("query.max-samples", "50000000")
        timeout = flags.get("query.timeout", "2m")

        result.append(f"   • Retention Time: {retention_time}")
        result.append(f"   • Retention Size: {retention_size}")
        result.append(f"   • Max Query Samples: {max_samples}")
        result.append(f"   • Query Timeout: {timeout}")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error getting Prometheus configuration: {str(e)}"
