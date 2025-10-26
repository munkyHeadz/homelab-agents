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
)
from crews.memory.incident_memory import IncidentMemory

# Load environment variables
load_dotenv()

# Initialize LLM - Using GPT-4o-mini (fast, cheap, works with CrewAI)
# Cost: $0.38/month for ~100 incidents vs Claude issues with CrewAI routing
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1
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
    goal="Continuously detect anomalies and issues across all homelab systems",
    backstory="""You are an expert SRE with 15 years of experience monitoring complex
    distributed systems. You have a keen eye for spotting anomalies before they become
    critical issues. You specialize in Prometheus metrics analysis and container orchestration.

    Your responsibility is to scan all metrics, identify problems, and immediately escalate
    issues to the Analyst for root cause analysis.""",
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
    ],
    llm=llm,
    verbose=True,
    allow_delegation=True,
)

# Agent 2: Root Cause Analyst
analyst_agent = Agent(
    role="Root Cause Analyst",
    goal="Diagnose the exact cause of infrastructure issues through systematic investigation",
    backstory="""You are a seasoned infrastructure detective with deep knowledge of
    Linux systems, networking, container orchestration, and distributed systems. You excel
    at correlating symptoms to find root causes.

    When the Monitor identifies an issue, you dive deep into logs, metrics, and system
    state to pinpoint exactly what went wrong and why. You provide detailed diagnostic
    reports to the Healer.""",
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
    ],
    llm=llm,
    verbose=True,
    allow_delegation=True,
)

# Agent 3: Self-Healing Engineer
healer_agent = Agent(
    role="Self-Healing Engineer",
    goal="Automatically remediate infrastructure issues based on root cause analysis",
    backstory="""You are an expert automation engineer who specializes in self-healing
    infrastructure. You have extensive experience with incident response and know the
    safest remediation strategies for common issues.

    Based on the Analyst's diagnosis, you execute precise fixes - restarting containers,
    clearing caches, adjusting resource limits, etc. You always verify the fix worked
    before reporting success.""",
    tools=[restart_container, restart_lxc, check_container_status, check_lxc_status],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

# Agent 4: Communications Coordinator
communicator_agent = Agent(
    role="Communications Coordinator",
    goal="Keep humans informed of all incidents, investigations, and resolutions",
    backstory="""You are a technical communications expert who translates complex
    infrastructure events into clear, actionable summaries for humans. You know when
    to alert immediately vs. when to send a summary report.

    You track the entire incident lifecycle - from detection through resolution - and
    provide concise Telegram notifications with just enough detail.""",
    tools=[send_telegram],
    llm=llm,
    verbose=True,
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
                limit=3,
                severity_filter=severity if severity != 'unknown' else None
            )
            if similar_incidents:
                historical_context = incident_memory.format_historical_context(similar_incidents)
                print(f"✓ Found {len(similar_incidents)} similar past incidents for context")
        except Exception as e:
            print(f"⚠ Warning: Could not retrieve historical context: {e}")

    # Task 1: Detection and Initial Assessment
    detection_task = Task(
        description=f"""
        An alert has been triggered: {alert_name}
        Description: {alert_desc}

        Your task:
        1. Verify the alert is legitimate using Prometheus metrics
        2. Assess the severity and scope of the issue
        3. Identify which services/containers are affected
        4. Provide a clear summary for the Analyst to investigate

        Return a structured report with:
        - Alert validity (true/false positive)
        - Affected systems
        - Severity level (critical/warning/info)
        - Initial observations
        """,
        agent=monitor_agent,
        expected_output="Structured detection report with affected systems and severity"
    )

    # Task 2: Root Cause Analysis
    analysis_task = Task(
        description=f"""
        Based on the Monitor's detection report, perform deep root cause analysis:

        1. Examine container/service logs for errors
        2. Check Prometheus metrics for anomalies (CPU, memory, disk, network)
        3. Correlate timeline of events
        4. Identify the specific failure point

        {historical_context}

        Return a diagnostic report with:
        - Root cause explanation
        - Timeline of events
        - Recommended remediation steps
        - Confidence level in diagnosis
        """,
        agent=analyst_agent,
        expected_output="Root cause analysis with remediation recommendations",
        context=[detection_task]
    )

    # Task 3: Auto-Remediation
    healing_task = Task(
        description="""
        Based on the Analyst's diagnosis, execute the safest remediation:

        1. Choose the least disruptive fix (restart container < restart LXC < manual intervention)
        2. Execute the remediation action
        3. Wait 30 seconds and verify the fix worked
        4. If still broken, try next level of remediation
        5. If all auto-fixes fail, escalate to humans

        Return a remediation report with:
        - Action taken
        - Success/failure status
        - Post-fix verification results
        - Any follow-up recommendations
        """,
        agent=healer_agent,
        expected_output="Remediation report with success status and verification",
        context=[analysis_task]
    )

    # Task 4: Human Communication
    communication_task = Task(
        description="""
        Summarize the entire incident for the human operator via Telegram:

        Create a concise message with:
        - What broke
        - What caused it
        - What we did to fix it
        - Current status
        - Any required human action

        Use Markdown formatting for clarity.
        Keep it under 500 characters if possible.

        Use this format:
        🚨 *Incident Report*
        *Issue*: [what broke]
        *Cause*: [root cause]
        *Action*: [what agents did]
        *Status*: [resolved/escalated]
        [Next steps if needed]
        """,
        agent=communicator_agent,
        expected_output="Telegram notification sent with incident summary",
        context=[detection_task, analysis_task, healing_task]
    )

    # Create and run the crew
    crew = Crew(
        agents=[monitor_agent, analyst_agent, healer_agent, communicator_agent],
        tasks=[detection_task, analysis_task, healing_task, communication_task],
        process=Process.sequential,
        verbose=True
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
        description="""
        Perform a proactive health check of the entire homelab:

        1. Query Prometheus for all 'up' metrics
        2. Check all Docker containers are running
        3. Check all LXC containers are running
        4. Monitor Tailscale VPN health and critical infrastructure connectivity
        5. Look for any concerning metrics (high CPU, memory, disk usage)
        6. If everything looks good, no action needed
        7. If issues found, escalate to full incident response

        Return a health status report.
        """,
        agent=monitor_agent,
        expected_output="Health check report with status of all systems"
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
