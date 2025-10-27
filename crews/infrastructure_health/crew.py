"""Infrastructure Health Crew - Autonomous homelab monitoring and self-healing."""

import os
import time
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from crews.tools import (
    query_prometheus,
    check_container_status,
    restart_container,
    check_container_logs,
    check_lxc_status,
    restart_lxc,
    send_telegram,
    list_tailscale_devices,
    check_device_connectivity,
    monitor_vpn_health,
    get_critical_infrastructure_status,
    check_postgres_health,
    query_database_performance,
    check_database_sizes,
    monitor_database_connections,
    check_specific_database,
    list_unifi_devices,
    check_ap_health,
    monitor_network_clients,
    check_wan_connectivity,
    monitor_switch_ports,
    get_network_performance,
    list_cloudflare_zones,
    check_zone_health,
    get_cloudflare_analytics,
    check_security_events,
    monitor_dns_records,
    get_cloudflare_status,
    check_adguard_status,
    get_dns_query_stats,
    check_blocklist_status,
    monitor_dns_clients,
    get_adguard_protection_summary,
    check_proxmox_node_health,
    list_proxmox_vms,
    check_proxmox_vm_status,
    get_proxmox_storage_status,
    get_proxmox_cluster_status,
    get_proxmox_system_summary,
    check_homeassistant_status,
    list_homeassistant_entities,
    get_entity_state,
    get_entity_history,
    check_automation_status,
    get_homeassistant_summary,
    check_prometheus_targets,
    check_prometheus_rules,
    get_prometheus_alerts,
    check_prometheus_tsdb,
    get_prometheus_runtime_info,
    get_prometheus_config_status,
    list_docker_images,
    prune_docker_images,
    inspect_docker_network,
    check_docker_volumes,
    get_container_resource_usage,
    check_docker_system_health,
    list_active_alerts,
    list_alert_silences,
    create_alert_silence,
    delete_alert_silence,
    check_alert_routing,
    get_alertmanager_status,
    add_annotation,
    get_grafana_status,
    list_dashboards,
    get_dashboard,
    create_snapshot,
    list_datasources,
)
from crews.memory.incident_memory import IncidentMemory

# Load environment variables
load_dotenv()

# Initialize LLM - Using GPT-4o-mini (fast, cheap, works with CrewAI)
# Optimized for minimal token usage
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
    max_tokens=500,  # Limit response length to reduce costs
    model_kwargs={"top_p": 0.9}  # Reduce sampling diversity
)

# Initialize incident memory for learning from past incidents
try:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    incident_memory = IncidentMemory(qdrant_url=qdrant_url)
    print(f"✓ Incident memory system initialized (Qdrant: {qdrant_url})")
except Exception as e:
    print(f"⚠ Warning: Could not initialize incident memory: {e}")
    incident_memory = None

# Agent 1: Infrastructure Monitor
monitor_agent = Agent(
    role="Infrastructure Monitor",
    goal="Detect issues across homelab systems",
    backstory="Expert SRE monitoring distributed systems. Scan metrics, identify problems, escalate to Analyst.",
    tools=[
        query_prometheus,
        check_container_status,
        check_lxc_status,
        monitor_vpn_health,
        get_critical_infrastructure_status,
        list_tailscale_devices,
        check_postgres_health,
        monitor_database_connections,
        check_ap_health,
        check_wan_connectivity,
        get_network_performance,
        check_zone_health,
        check_security_events,
        get_cloudflare_status,
        check_adguard_status,
        get_adguard_protection_summary,
        check_proxmox_node_health,
        get_proxmox_system_summary,
        check_homeassistant_status,
        get_homeassistant_summary,
        check_prometheus_targets,
        get_prometheus_alerts,
        check_prometheus_tsdb,
        get_prometheus_runtime_info,
        check_docker_system_health,
        list_docker_images,
        check_docker_volumes,
        list_active_alerts,
        get_alertmanager_status,
        get_grafana_status,
        list_dashboards,
    ],
    llm=llm,
    verbose=False,  # Reduced verbosity to minimize token usage
    allow_delegation=False,  # Disable delegation to reduce LLM calls
)

# Agent 2: Root Cause Analyst
analyst_agent = Agent(
    role="Root Cause Analyst",
    goal="Diagnose infrastructure issues",
    backstory="Infrastructure detective. Analyze logs and metrics to find root causes.",
    tools=[
        query_prometheus,
        check_container_logs,
        check_lxc_status,
        check_container_status,
        check_device_connectivity,
        list_tailscale_devices,
        query_database_performance,
        check_database_sizes,
        check_specific_database,
        list_unifi_devices,
        monitor_network_clients,
        monitor_switch_ports,
        list_cloudflare_zones,
        get_cloudflare_analytics,
        monitor_dns_records,
        get_dns_query_stats,
        check_blocklist_status,
        monitor_dns_clients,
        list_proxmox_vms,
        check_proxmox_vm_status,
        get_proxmox_storage_status,
        get_proxmox_cluster_status,
        list_homeassistant_entities,
        get_entity_state,
        get_entity_history,
        check_automation_status,
        check_prometheus_rules,
        get_prometheus_config_status,
        get_container_resource_usage,
        inspect_docker_network,
        list_alert_silences,
        check_alert_routing,
        get_dashboard,
        list_datasources,
    ],
    llm=llm,
    verbose=False,  # Reduced verbosity to minimize token usage
    allow_delegation=False,  # Disable delegation to reduce LLM calls
)

# Agent 3: Self-Healing Engineer
healer_agent = Agent(
    role="Self-Healing Engineer",
    goal="Remediate infrastructure issues",
    backstory="Automation engineer. Execute fixes based on diagnosis. Verify success.",
    tools=[restart_container, restart_lxc, check_container_status, check_lxc_status, prune_docker_images, create_alert_silence, delete_alert_silence, add_annotation, create_snapshot],
    llm=llm,
    verbose=False,  # Reduced verbosity to minimize token usage
    allow_delegation=False,
)

# Agent 4: Communications Coordinator
communicator_agent = Agent(
    role="Communications Coordinator",
    goal="Inform humans of incidents and resolutions",
    backstory="Technical communicator. Translate events into clear, concise summaries.",
    tools=[send_telegram],
    llm=llm,
    verbose=False,  # Reduced verbosity to minimize token usage
    allow_delegation=False,
)


def handle_alert(alert_data: dict):
    """
    Main entry point for handling Alertmanager alerts.

    Args:
        alert_data: Alert payload from Alertmanager
    """
    start_time = time.time()

    alert_name = alert_data.get('alerts', [{}])[0].get('labels', {}).get('alertname', 'Unknown')
    alert_desc = alert_data.get('alerts', [{}])[0].get('annotations', {}).get('description', 'No description')
    severity = alert_data.get('alerts', [{}])[0].get('labels', {}).get('severity', 'unknown')

    # Retrieve similar past incidents for learning
    historical_context = ""
    if incident_memory:
        try:
            similar_incidents = incident_memory.find_similar_incidents(
                query_text=f"{alert_name}: {alert_desc}",
                limit=1,  # Reduced from 3 to 1 to save tokens
                severity_filter=severity if severity != 'unknown' else None
            )
            if similar_incidents:
                historical_context = incident_memory.format_historical_context(similar_incidents)
                print(f"✓ Found {len(similar_incidents)} similar past incident for context")
        except Exception as e:
            print(f"⚠ Warning: Could not retrieve historical context: {e}")

    # Task 1: Detection and Initial Assessment
    detection_task = Task(
        description=f"""Alert: {alert_name}
Desc: {alert_desc}

1. Verify alert validity
2. Identify affected systems
3. Assess severity

Return: validity, systems, severity, observations""",
        agent=monitor_agent,
        expected_output="Detection report: validity, systems, severity"
    )

    # Task 2: Root Cause Analysis
    analysis_task = Task(
        description=f"""Based on Monitor report, find root cause:
1. Check logs
2. Check metrics
3. Correlate events

{historical_context}

Return: cause, timeline, fix recommendation""",
        agent=analyst_agent,
        expected_output="Root cause with fix recommendation",
        context=[detection_task]
    )

    # Task 3: Auto-Remediation
    healing_task = Task(
        description="""Execute fix from diagnosis:
1. Choose least disruptive fix
2. Execute action
3. Verify fix worked

Return: action, status, verification""",
        agent=healer_agent,
        expected_output="Remediation status",
        context=[analysis_task]
    )

    # Task 4: Human Communication
    communication_task = Task(
        description="""Send Telegram summary:
🚨 *Incident*
Issue: [what broke]
Cause: [root cause]
Fix: [action taken]
Status: [resolved/escalated]

Keep under 300 chars.""",
        agent=communicator_agent,
        expected_output="Telegram sent",
        context=[detection_task, analysis_task, healing_task]
    )

    # Create and run the crew
    crew = Crew(
        agents=[monitor_agent, analyst_agent, healer_agent, communicator_agent],
        tasks=[detection_task, analysis_task, healing_task, communication_task],
        process=Process.sequential,
        verbose=False  # Reduced verbosity to minimize token usage
    )

    result = crew.kickoff()

    # Store incident in memory for future learning
    if incident_memory:
        try:
            resolution_time = int(time.time() - start_time)

            # Extract information from crew result
            result_str = str(result).lower()

            # Determine resolution status
            if "resolved" in result_str or "success" in result_str or "fixed" in result_str:
                resolution_status = "resolved"
            elif "escalat" in result_str or "manual" in result_str or "fail" in result_str:
                resolution_status = "escalated"
            else:
                resolution_status = "attempted"

            # Extract affected systems (parse from detection task result)
            affected_systems = [alert_name]  # Default to alert name

            # Store the incident
            incident_id = incident_memory.store_incident(
                alert_name=alert_name,
                description=alert_desc,
                severity=severity,
                affected_systems=affected_systems,
                root_cause=f"Analysis performed by AI agents: {result_str[:200]}",
                remediation_taken=f"Autonomous remediation executed: {result_str[200:400]}",
                resolution_status=resolution_status,
                resolution_time_seconds=resolution_time,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "crew_result": result_str[:500]
                }
            )
            print(f"✓ Incident stored in memory: {incident_id}")

            # Log statistics
            stats = incident_memory.get_incident_stats()
            print(f"📊 Memory Stats: {stats['total_incidents']} incidents, "
                  f"{stats['success_rate']:.1f}% success rate, "
                  f"avg resolution: {stats['avg_resolution_time']}s")
        except Exception as e:
            print(f"⚠ Warning: Could not store incident in memory: {e}")

    return result


def scheduled_health_check():
    """
    Periodic health check (runs every 5 minutes).
    Proactively looks for issues before alerts fire.
    """
    proactive_task = Task(
        description="""Quick health check:
1. Check Prometheus 'up' metrics
2. Check Docker/LXC containers
3. Check VPN connectivity
4. Report issues only

Return: status (OK or issues found)""",
        agent=monitor_agent,
        expected_output="Health status"
    )

    crew = Crew(
        agents=[monitor_agent],
        tasks=[proactive_task],
        process=Process.sequential,
        verbose=False  # Less verbose for scheduled checks
    )

    result = crew.kickoff()

    # Extract text from CrewOutput object
    result_text = str(result.raw) if hasattr(result, 'raw') else str(result)

    # If issues found, trigger full incident response
    if "issue" in result_text.lower() or "problem" in result_text.lower() or "down" in result_text.lower():
        print(f"Proactive check found issues: {result_text}")
        # Trigger full alert handling
        handle_alert({
            'alerts': [{
                'labels': {'alertname': 'ProactiveHealthCheckFailed'},
                'annotations': {'description': f'Scheduled health check detected: {result_text}'}
            }]
        })

    return result_text
