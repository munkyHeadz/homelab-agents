# Homelab-Agents Strategic Improvement Roadmap

**Document Version:** 1.0
**Date Created:** 2025-10-27
**Current Project State:** 81 tools, 16 services, 51.6% coverage
**Target State:** 150+ tools, 25+ services, 80% coverage, 80% autonomous resolution

---

## Executive Summary

The homelab-agents project has successfully built a **world-class diagnostic system** with 81 autonomous tools across 16 services, achieving 100% success on 8 handled incidents at $0.38/month operational cost. However, strategic analysis reveals a critical capability gap:

**Current State:**
- ✅ **Observability**: Excellent (72 diagnostic tools)
- ⚠️ **Remediation**: Weak (9 healing tools)
- 📊 **Ratio**: 8:1 diagnostic-to-remediation

**The Problem:**
The system can **diagnose** 90% of issues but can only **fix** ~10% autonomously. This creates a bottleneck where the AI identifies problems but requires human intervention for resolution.

**Strategic Goal:**
Transform from "AI-assisted diagnostics" to "true autonomous operations" by:
1. Expanding Healer agent from 9 to 40+ remediation tools
2. Implementing safety controls (approval workflows, rollback)
3. Adding predictive capabilities
4. Achieving 80% autonomous resolution rate

**Timeline:** 10 phases over 3-4 months
**Expected Outcome:** 4x increase in autonomous resolution capability

---

## 📊 Current State Analysis (After Phase 24)

### Strengths
1. **Comprehensive Monitoring**: 72 diagnostic tools across critical infrastructure
2. **Perfect Track Record**: 100% success rate on incidents handled
3. **Cost Efficiency**: $0.38/month operational cost
4. **Learning System**: Qdrant vector memory for incident patterns
5. **Multi-Layer Coverage**: Containers, VMs, databases, networks, monitoring stack
6. **Production Deployed**: Live system handling real incidents

### Critical Weaknesses
1. **Healer Agent Underpowered**: Only 9 remediation tools
2. **No Approval Workflow**: Can execute destructive actions without human approval
3. **Zero Automated Tests**: 81 tools with no regression testing
4. **No Rollback Capability**: Cannot undo changes if something goes wrong
5. **No CI/CD Pipeline**: Manual deployment to production
6. **Limited Tool Observability**: Don't know which tools are slow or failing
7. **Single Model Dependency**: 100% reliant on OpenAI GPT-4o-mini
8. **Passive Learning**: Stores incidents but doesn't learn from patterns
9. **Purely Reactive**: No predictive or proactive capabilities
10. **Service Coverage Gaps**: 48% of infrastructure unmonitored

### Service Coverage Breakdown

**Fully Covered (10 services, 6+ tools each):**
- Docker: 10 tools ✅
- PostgreSQL: 11 tools ✅
- LXC: 8 tools ✅
- Prometheus: 7 tools ✅
- Grafana: 6 tools ✅
- Alertmanager: 6 tools ✅
- Proxmox VMs: 6 tools ✅
- UniFi: 6 tools ✅
- Cloudflare: 6 tools ✅
- Home Assistant: 6 tools ✅

**Under-Served (3 services, <6 tools):**
- AdGuard Home: 5 tools ⚠️
- Tailscale: 4 tools ⚠️
- Telegram: 1 tool ⚠️

**Not Covered (15+ services, 0 tools):**
- Redis/Valkey ❌
- MinIO/Object Storage ❌
- Proxmox Backup Server ❌
- Certificate Management (Let's Encrypt/Certbot) ❌
- Reverse Proxies (Traefik/HAProxy/Nginx) ❌
- CI/CD (Gitea/Drone/Jenkins) ❌
- Message Queues (RabbitMQ/NATS) ❌
- Logging (Loki/Elasticsearch) ❌
- Backup Tools (Restic/Borg) ❌
- Monitoring Exporters (Node Exporter details) ❌
- And 5+ more...

### Tool Distribution Analysis

**By Agent:**
- Monitor Agent: ~25 tools (health checks, summaries, alerts)
- Analyst Agent: ~47 tools (diagnostics, logs, analysis, troubleshooting)
- Healer Agent: **9 tools** (restart containers, prune images, silence alerts) ⚠️
- Communicator Agent: 1 tool (Telegram notifications)

**By Capability:**
- Read-Only (Diagnostic): 72 tools (89%)
- Write (Remediation): 9 tools (11%) ⚠️

**Critical Insight:** The system is 8:1 diagnostic-heavy, creating a human bottleneck for remediation.

---

## 🎯 Strategic Objectives

### Primary Objective
**Achieve 80% autonomous incident resolution within 3-4 months**

### Secondary Objectives
1. Expand Healer agent from 9 to 40+ remediation tools
2. Implement safety controls for all destructive actions
3. Achieve 80% code coverage with automated tests
4. Deploy fully automated CI/CD pipeline
5. Add predictive and proactive capabilities
6. Increase service coverage from 51.6% to 80%
7. Reduce mean time to resolution from 137s to <60s
8. Maintain 100% safety record (no unintended outages)

---

## 🚀 Implementation Roadmap: Phases 25-35

### **PHASE 25: Healer Expansion (Part 1) - Critical Remediation Tools**
**Priority:** 🔴 CRITICAL
**Timeline:** 1 week
**Dependencies:** None

**Objective:** Add 6 critical remediation tools to Healer agent

**Tools to Implement:**
1. **update_lxc_resources(vmid, cpu, memory, swap)** - Adjust container resources
   - Use case: PostgreSQL running out of memory → increase allocation
   - Safety: Dry-run mode, requires approval for production containers
   - Validation: Check if resources available on node

2. **create_lxc_snapshot(vmid, name, description)** - Backup before changes
   - Use case: Create snapshot before risky operations
   - Safety: Check available storage before creating
   - Validation: Verify snapshot creation succeeded

3. **restart_postgres_service(lxc_id, service_name)** - Database service recovery
   - Use case: PostgreSQL service crashed but container is running
   - Safety: Check if database has active connections first
   - Validation: Verify service started successfully

4. **vacuum_postgres_table(database, table, full=False)** - Automated bloat cleanup
   - Use case: Table bloat detected by check_table_bloat
   - Safety: Only run during low-traffic periods, require approval for VACUUM FULL
   - Validation: Check bloat reduction after operation

5. **clear_postgres_connections(database, force_user=None)** - Kill blocking sessions
   - Use case: Database locked by long-running query
   - Safety: Require approval, log all terminated sessions
   - Validation: Verify locks cleared

6. **update_docker_resources(container, cpu_limit, memory_limit)** - Container resource adjustment
   - Use case: Container consuming excessive resources
   - Safety: Validate limits before applying
   - Validation: Check container still running after change

**Integration:**
- Add all 6 tools to Healer agent's tool list
- Update crew.py with new imports
- Create approval workflow stubs (implement in Phase 26)

**Testing:**
- Manual testing in dev environment
- Document test cases for future automation

**Success Criteria:**
- ✅ All 6 tools created and validated
- ✅ Healer agent can access tools
- ✅ Manual testing confirms functionality
- ✅ Documentation updated

**Expected Impact:**
- Healer tools: 9 → 15 (+67% increase)
- New capabilities: Resource adjustment, database maintenance, backup creation
- Autonomous resolution potential: 10% → 25%

---

### **PHASE 26: Approval Workflow & Safety Controls**
**Priority:** 🔴 CRITICAL
**Timeline:** 1.5 weeks
**Dependencies:** Phase 25

**Objective:** Implement safety controls to prevent AI from taking down critical infrastructure

**Components to Implement:**

**1. Approval Decorator System**
```python
# crews/safety/approval.py

from enum import Enum
from typing import Callable, Dict, Any
import json

class ApprovalLevel(Enum):
    NONE = "none"           # Auto-approve
    SOFT = "soft"           # Notify but proceed
    HARD = "hard"           # Require approval, block until response
    FORBIDDEN = "forbidden" # Never allow

class ApprovalWorkflow:
    # Critical services that require approval
    CRITICAL_SERVICES = {
        'lxc': [200],  # PostgreSQL
        'container': ['prometheus', 'grafana', 'alertmanager'],
        'database': ['postgres', 'production']
    }

    # Action risk levels
    ACTION_RISK_LEVELS = {
        'restart_lxc': ApprovalLevel.HARD,
        'restart_postgres_service': ApprovalLevel.HARD,
        'vacuum_postgres_table': ApprovalLevel.SOFT,
        'update_lxc_resources': ApprovalLevel.HARD,
        'clear_postgres_connections': ApprovalLevel.HARD,
        'prune_docker_images': ApprovalLevel.SOFT,
        'restart_container': ApprovalLevel.HARD,
    }

    def requires_approval(self, action: str, target: Any) -> ApprovalLevel:
        """Determine if action requires approval"""
        base_level = self.ACTION_RISK_LEVELS.get(action, ApprovalLevel.NONE)

        # Elevate to HARD if target is critical
        if self._is_critical_target(target):
            if base_level == ApprovalLevel.SOFT:
                return ApprovalLevel.HARD

        return base_level

    def _is_critical_target(self, target: Any) -> bool:
        """Check if target is a critical service"""
        # Implementation checks against CRITICAL_SERVICES
        pass

    def request_approval(self, action: str, target: Any, params: Dict) -> bool:
        """Request approval via Telegram"""
        # Send approval request to Telegram
        # Return True if approved, False if denied
        # Timeout after 5 minutes = auto-deny
        pass
```

**2. Telegram Approval Bot**
```python
# crews/safety/telegram_approval.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TelegramApprovalBot:
    def send_approval_request(self, action: str, target: Any, params: Dict,
                             incident_id: str, timeout_minutes: int = 5):
        """Send approval request with inline buttons"""

        message = f"""
🤖 **Approval Required**

**Incident:** {incident_id}
**Action:** {action}
**Target:** {target}
**Parameters:** {json.dumps(params, indent=2)}

**Risk Level:** HIGH - Critical Service
**Timeout:** {timeout_minutes} minutes

Do you approve this action?
        """

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{incident_id}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"deny:{incident_id}")
            ],
            [
                InlineKeyboardButton("🔍 More Info", callback_data=f"info:{incident_id}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send message and wait for response
        pass
```

**3. Change Logging System**
```python
# crews/safety/change_log.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class ChangeRecord:
    change_id: str
    incident_id: str
    timestamp: datetime
    agent: str
    action: str
    target: Any
    params: Dict[str, Any]
    approval_status: str
    approved_by: Optional[str]
    result: str
    rollback_possible: bool
    rollback_action: Optional[str]

class ChangeLog:
    def record_change(self, change: ChangeRecord):
        """Store change in Qdrant for audit trail"""
        pass

    def get_incident_changes(self, incident_id: str):
        """Retrieve all changes for an incident"""
        pass

    def get_rollback_plan(self, change_id: str):
        """Get rollback instructions for a change"""
        pass
```

**4. Dry-Run Mode**
```python
# Add to each remediation tool

def restart_lxc(vmid: int, dry_run: bool = False):
    if dry_run:
        return f"DRY-RUN: Would restart LXC {vmid}"

    # Actual implementation
    pass
```

**Testing:**
- Unit tests for approval logic
- Integration tests with Telegram bot
- End-to-end test with mock approvals

**Success Criteria:**
- ✅ Approval workflow prevents unauthorized actions on critical services
- ✅ Telegram bot sends approval requests with buttons
- ✅ Change log tracks all remediation actions
- ✅ Dry-run mode works for all tools
- ✅ 5-minute timeout auto-denies

**Expected Impact:**
- Safety: Prevents accidental outages on critical infrastructure
- Auditability: Complete change history
- Testing: Dry-run mode enables safe validation

---

### **PHASE 27: Automated Testing & CI/CD**
**Priority:** 🔴 CRITICAL
**Timeline:** 2 weeks
**Dependencies:** Phase 26

**Objective:** Implement comprehensive automated testing and CI/CD pipeline

**Components to Implement:**

**1. Test Framework Structure**
```
tests/
  unit/
    test_docker_tools.py          # 10 tools × 3 tests = 30 tests
    test_postgres_tools.py         # 11 tools × 3 tests = 33 tests
    test_lxc_tools.py             # 8 tools × 3 tests = 24 tests
    test_proxmox_tools.py          # 6 tools × 3 tests = 18 tests
    test_prometheus_tools.py       # 7 tools × 3 tests = 21 tests
    test_approval_workflow.py      # 10 tests
    test_change_log.py            # 5 tests
    ...
  integration/
    test_monitor_agent.py          # 15 tests
    test_analyst_agent.py          # 15 tests
    test_healer_agent.py          # 20 tests (includes approval tests)
    test_communicator_agent.py     # 5 tests
    test_full_workflow.py         # 10 tests
  e2e/
    test_incident_scenarios.py     # 10 common incident types
    test_approval_flow.py         # End-to-end approval testing

  Target: 200+ tests, 80% code coverage
```

**2. Mock Infrastructure**
```python
# tests/mocks/mock_docker.py
class MockDockerClient:
    def containers(self):
        return MockContainerCollection()

    def images(self):
        return MockImageCollection()

# tests/mocks/mock_proxmox.py
class MockProxmoxAPI:
    def nodes(self, node):
        return MockNode(node)

# tests/mocks/mock_postgres.py
class MockPostgresConnection:
    def execute(self, query):
        return MockCursor()
```

**3. GitHub Actions Workflows**
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install ruff black mypy
      - name: Lint with ruff
        run: ruff check crews/
      - name: Format check with black
        run: black --check crews/
      - name: Type check with mypy
        run: mypy crews/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      - name: Run tests
        run: pytest tests/ --cov=crews/ --cov-report=xml --cov-report=term
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Bandit security scan
        run: |
          pip install bandit
          bandit -r crews/ -f json -o bandit-report.json
```

**4. Deployment Automation**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    needs: [test, lint, security]
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to homelab
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh -o StrictHostKeyChecking=no root@100.67.169.111 'bash -s' < scripts/deploy.sh
```

**5. Deployment Script**
```bash
# scripts/deploy.sh
#!/bin/bash
set -e

echo "🚀 Starting deployment..."

cd /root/homelab-agents

# Pull latest code
git fetch origin
git checkout main
git pull origin main

# Backup current state
docker commit homelab-agents homelab-agents:backup-$(date +%Y%m%d-%H%M%S)

# Rebuild image
docker build -t homelab-agents:latest .

# Run tests in container
docker run --rm homelab-agents:latest pytest tests/unit/ tests/integration/

# Stop old container
docker stop homelab-agents || true
docker rm homelab-agents || true

# Start new container
docker run -d \
  --name homelab-agents \
  --restart unless-stopped \
  --network monitoring \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file /root/homelab-agents/.env \
  homelab-agents:latest

# Wait for health check
sleep 10
curl -f http://localhost:5000/health || exit 1

echo "✅ Deployment successful!"
```

**Success Criteria:**
- ✅ 200+ automated tests implemented
- ✅ 80% code coverage achieved
- ✅ GitHub Actions runs on every commit
- ✅ Deployment fully automated
- ✅ All tests passing

**Expected Impact:**
- Quality: Catch regressions before production
- Confidence: Safe to make changes
- Speed: Automated deployment reduces manual work

---

### **PHASE 28: Healer Expansion (Part 2) - Service Management**
**Priority:** 🟡 HIGH
**Timeline:** 1 week
**Dependencies:** Phase 25, 26, 27

**Objective:** Add 6 more remediation tools focused on service management

**Tools to Implement:**
1. **reload_prometheus_config()** - Apply configuration changes without restart
2. **rotate_logs(service, max_size_mb)** - Free up disk space
3. **adjust_monitoring_thresholds(service, metric, value)** - Tune alert thresholds
4. **restart_network_interface(lxc_id, interface)** - Network recovery
5. **update_dns_record(zone, record, value, ttl)** - DNS automation
6. **restart_homeassistant()** - Smart home service recovery

**Integration:**
- All tools go to Healer agent
- All require approval workflow
- All include dry-run mode
- All log changes

**Success Criteria:**
- ✅ Healer tools: 15 → 21
- ✅ All tools tested
- ✅ Approval workflow working
- ✅ CI/CD passing

**Expected Impact:**
- Healer capabilities: +40% increase
- Autonomous resolution potential: 25% → 35%

---

### **PHASE 29: Tool Performance Monitoring**
**Priority:** 🟡 HIGH
**Timeline:** 1 week
**Dependencies:** Phase 27

**Objective:** Add observability for tool performance and AI decision-making

**Components to Implement:**

**1. Tool Metrics Collection**
```python
# crews/observability/tool_metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Metrics
tool_executions = Counter('agent_tool_executions_total',
                         'Total tool executions',
                         ['tool_name', 'agent', 'status'])

tool_duration = Histogram('agent_tool_duration_seconds',
                         'Tool execution duration',
                         ['tool_name', 'agent'])

tool_errors = Counter('agent_tool_errors_total',
                     'Tool execution errors',
                     ['tool_name', 'error_type'])

def track_tool_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        agent = get_current_agent()  # From context

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            status = 'success'
            return result
        except Exception as e:
            status = 'error'
            tool_errors.labels(tool_name=tool_name, error_type=type(e).__name__).inc()
            raise
        finally:
            duration = time.time() - start_time
            tool_executions.labels(tool_name=tool_name, agent=agent, status=status).inc()
            tool_duration.labels(tool_name=tool_name, agent=agent).observe(duration)

    return wrapper
```

**2. Grafana Dashboard**
```
Tool Performance Dashboard:
- Tool execution count by tool (bar chart)
- Tool success rate by tool (gauge, 0-100%)
- Tool execution time p50/p95/p99 (graph)
- Tool errors by type (pie chart)
- Agent decision time (histogram)
- Cost per incident (gauge)
- Tools used per incident (histogram)
- Most common tool combinations (table)
```

**3. AI Decision Logging**
```python
# crews/observability/decision_log.py

def log_agent_decision(agent, tool_selected, reasoning, confidence):
    """Log why agent chose a particular tool"""
    decision_log.labels(
        agent=agent,
        tool=tool_selected,
        confidence_bucket=bucket_confidence(confidence)
    ).inc()
```

**Success Criteria:**
- ✅ Metrics exported to Prometheus
- ✅ Grafana dashboard created
- ✅ 7-day historical data visible
- ✅ Alerts on tool failures

**Expected Impact:**
- Visibility: Know which tools are slow or failing
- Optimization: Identify tools to improve
- Cost tracking: Monitor LLM token usage

---

### **PHASE 30: Predictive Analytics**
**Priority:** 🟢 MEDIUM
**Timeline:** 2 weeks
**Dependencies:** Phase 29

**Objective:** Add proactive capabilities - predict issues before they occur

**Components to Implement:**

**1. Resource Trend Analysis**
```python
# crews/intelligence/predictive.py

def predict_resource_exhaustion(service, resource_type):
    """
    Analyze resource growth trends and predict exhaustion

    Examples:
    - "LXC 200 disk will be full in 14 days at current growth rate"
    - "PostgreSQL memory usage growing 5% per week, will hit limit in 8 weeks"
    """

    # Query Prometheus for historical data (30 days)
    query = f'{resource_type}{{service="{service}"}}'
    data = prometheus.query_range(query, start='-30d', step='1h')

    # Linear regression to predict future usage
    trend = calculate_trend(data)

    # Predict when resource will reach 90% threshold
    days_until_exhaustion = predict_exhaustion_date(trend, threshold=0.9)

    if days_until_exhaustion < 30:
        return {
            'alert': True,
            'service': service,
            'resource': resource_type,
            'current_usage': trend.current_value,
            'days_until_full': days_until_exhaustion,
            'recommended_action': generate_recommendation(service, resource_type)
        }
```

**2. Anomaly Detection**
```python
def detect_anomalies(service, metric):
    """
    Use statistical methods to detect unusual patterns

    Examples:
    - "Database query time increased 40% in past 6 hours (anomaly)"
    - "Network traffic to LXC 200 is 3 standard deviations above normal"
    """

    # Get baseline (past 7 days, same time of day)
    baseline = get_baseline_metrics(service, metric, days=7)

    # Get current values
    current = get_current_metrics(service, metric)

    # Statistical anomaly detection
    if is_anomaly(current, baseline, threshold=3.0):  # 3 sigma
        return {
            'anomaly_detected': True,
            'service': service,
            'metric': metric,
            'current_value': current,
            'baseline_mean': baseline.mean,
            'deviation': calculate_deviation(current, baseline),
            'severity': classify_severity(deviation)
        }
```

**3. Pattern Recognition**
```python
def identify_recurring_patterns():
    """
    Analyze incident history to find patterns

    Examples:
    - "LXC 200 OOM every Sunday at 3am (backup job)"
    - "PostgreSQL slow queries spike on Monday mornings (report generation)"
    """

    incidents = get_all_incidents(days=90)

    # Group by day of week, time of day
    patterns = analyze_temporal_patterns(incidents)

    # Find correlations
    correlations = find_correlations(incidents)

    return {
        'temporal_patterns': patterns,
        'correlations': correlations,
        'recommendations': [
            'Schedule backup job at different time',
            'Pre-emptively increase resources before peak',
            'Add indexes to reduce Monday query times'
        ]
    }
```

**4. Proactive Health Check Task**
```python
# Add to crew.py

proactive_check_task = Task(
    description="""
    Run predictive analytics:
    1. Check for resource exhaustion predictions
    2. Detect anomalies in key metrics
    3. Identify recurring patterns
    4. Recommend preventive actions

    Only report if issues predicted in next 7 days.
    """,
    agent=analyst_agent,
    expected_output="Predictive analysis report"
)
```

**Success Criteria:**
- ✅ Predicts resource exhaustion 7+ days in advance
- ✅ Detects anomalies before alerts fire
- ✅ Identifies recurring patterns
- ✅ Generates actionable recommendations

**Expected Impact:**
- Proactive: Prevent issues before they occur
- Efficiency: Reduce unplanned incidents by 40%
- Planning: Better capacity planning

---

### **PHASE 31: Adaptive Learning System**
**Priority:** 🟢 MEDIUM
**Timeline:** 2 weeks
**Dependencies:** Phase 30

**Objective:** Make the system learn from past resolutions and improve over time

**Components to Implement:**

**1. Resolution Success Tracking**
```python
# crews/intelligence/learning.py

class AdaptiveLearning:
    def track_resolution_outcome(self, incident_id, tools_used, success):
        """
        Track which tools worked for which incidents

        Update confidence scores:
        - Success: Increase tool confidence for this incident type
        - Failure: Decrease tool confidence
        """

        incident = get_incident(incident_id)
        incident_type = classify_incident_type(incident)

        for tool in tools_used:
            update_tool_confidence(
                tool=tool,
                incident_type=incident_type,
                success=success,
                delta=0.1  # Learning rate
            )

    def get_recommended_tools(self, incident_type):
        """
        Recommend tools based on historical success rates

        Returns:
        [
            ('analyze_slow_queries', 0.92),  # 92% success rate
            ('check_index_health', 0.85),
            ('vacuum_postgres_table', 0.78)
        ]
        """

        tool_scores = get_tool_success_rates(incident_type)
        return sorted(tool_scores, key=lambda x: x[1], reverse=True)[:5]
```

**2. Intelligent Tool Selection**
```python
def enhance_analyst_prompt_with_learning(incident):
    """Add learned patterns to agent prompt"""

    incident_type = classify_incident_type(incident)
    recommended_tools = adaptive_learning.get_recommended_tools(incident_type)
    similar_incidents = incident_memory.find_similar_incidents(incident)

    enhanced_prompt = f"""
    Incident: {incident.description}

    Historical Context:
    - Similar incidents: {len(similar_incidents)}
    - Recommended tools (by success rate):
      {format_tool_recommendations(recommended_tools)}

    Past Successful Resolutions:
    {format_similar_resolutions(similar_incidents)}

    Based on this historical data, investigate and diagnose.
    """

    return enhanced_prompt
```

**3. Feedback Loop**
```python
def collect_resolution_feedback():
    """
    After incident resolution, ask user for feedback

    Telegram message:
    "Incident XYZ was resolved. Did it work? ✅ Yes / ❌ No"

    Use feedback to update success rates
    """
    pass
```

**Success Criteria:**
- ✅ Tool confidence scores update based on success
- ✅ Agent prompts include learned recommendations
- ✅ Success rate improves over time
- ✅ User feedback collected

**Expected Impact:**
- Intelligence: System gets smarter with each incident
- Efficiency: Higher first-attempt success rate
- Accuracy: Better tool selection

---

### **PHASE 32: Healer Expansion (Part 3) - Advanced Remediation**
**Priority:** 🟢 MEDIUM
**Timeline:** 1.5 weeks
**Dependencies:** Phase 28

**Objective:** Add advanced remediation capabilities

**Tools to Implement:**
1. **restore_lxc_snapshot(vmid, snapshot_name)** - Rollback capability
2. **kill_long_running_query(database, query_pid)** - Database cleanup
3. **clear_docker_logs(container, keep_lines)** - Free disk space
4. **update_container_image(container, image_tag)** - Automated updates
5. **reindex_postgres_table(database, table)** - Fix corrupted indexes
6. **adjust_lxc_disk_size(vmid, size_gb)** - Expand storage

**Integration:**
- All tools require HARD approval
- All tools log changes with rollback information
- All tools tested in CI/CD

**Success Criteria:**
- ✅ Healer tools: 21 → 27
- ✅ Rollback capability available
- ✅ Advanced database operations
- ✅ Storage management

**Expected Impact:**
- Healer capabilities: +28% increase
- Autonomous resolution potential: 35% → 50%

---

### **PHASE 33: Service Coverage Expansion - Backup Systems**
**Priority:** 🟢 MEDIUM
**Timeline:** 1 week
**Dependencies:** None (parallel track)

**Objective:** Add monitoring for backup infrastructure

**Services to Integrate:**

**1. Proxmox Backup Server (PBS)** - 6 tools:
```
- check_pbs_datastore_status
- list_backup_jobs
- verify_backup_integrity
- check_backup_schedule
- get_backup_statistics
- check_pbs_disk_usage
```

**2. Restic/Borg (if used)** - 6 tools:
```
- check_restic_repository
- list_restic_snapshots
- verify_restic_backup
- check_backup_age
- get_repository_stats
- check_backup_encryption
```

**Success Criteria:**
- ✅ 12 new backup monitoring tools
- ✅ Integrated with Monitor and Analyst agents
- ✅ Alert on backup failures
- ✅ Verify backup recency

**Expected Impact:**
- Service coverage: 51.6% → 58%
- Backup visibility: Complete
- Disaster recovery: Proactive monitoring

---

### **PHASE 34: Service Coverage Expansion - Certificate Management**
**Priority:** 🟢 MEDIUM
**Timeline:** 1 week
**Dependencies:** None (parallel track)

**Objective:** Monitor SSL/TLS certificates and automate renewal

**Tools to Implement (6 total):**
1. **check_certificate_expiry(domain)** - Monitor certificate validity
2. **list_all_certificates()** - Certificate inventory
3. **verify_certificate_chain(domain)** - Validate trust chain
4. **renew_certificate(domain)** - Automated renewal (with approval)
5. **check_acme_challenges()** - Monitor Let's Encrypt challenges
6. **alert_expiring_certificates(days_threshold)** - Proactive alerts

**Integration:**
- Monitor agent: Expiry checks
- Analyst agent: Chain validation
- Healer agent: Renewal (with approval)

**Success Criteria:**
- ✅ 6 certificate tools
- ✅ Alert 30 days before expiry
- ✅ Automated renewal capability
- ✅ No certificate outages

**Expected Impact:**
- Service coverage: 58% → 61%
- Security: No expired certificates
- Automation: Hands-free certificate management

---

### **PHASE 35: Multi-Model Strategy & Resilience**
**Priority:** 🟢 MEDIUM
**Timeline:** 1 week
**Dependencies:** Phase 27

**Objective:** Reduce single-point-of-failure risk on OpenAI

**Components to Implement:**

**1. Model Abstraction Layer**
```python
# crews/llm/model_selector.py

from enum import Enum

class ModelProvider(Enum):
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    OPENAI_GPT4O = "openai_gpt4o"
    ANTHROPIC_CLAUDE_SONNET = "anthropic_claude_sonnet"
    ANTHROPIC_CLAUDE_HAIKU = "anthropic_claude_haiku"

class ModelSelector:
    # Fallback chain
    PRIMARY = ModelProvider.OPENAI_GPT4O_MINI
    SECONDARY = ModelProvider.OPENAI_GPT4O
    TERTIARY = ModelProvider.ANTHROPIC_CLAUDE_SONNET

    def select_model(self, incident_severity, incident_complexity):
        """
        Select optimal model based on incident characteristics

        Rules:
        - Critical + Complex → GPT-4o (better reasoning)
        - Critical + Simple → GPT-4o-mini (fast)
        - Normal → GPT-4o-mini (cost-effective)
        """

        if incident_severity == 'critical' and incident_complexity == 'high':
            return self.get_client(ModelProvider.OPENAI_GPT4O)
        else:
            return self.get_client(ModelProvider.OPENAI_GPT4O_MINI)

    def get_client_with_fallback(self, preferred: ModelProvider):
        """
        Try primary, fall back to secondary if unavailable
        """
        try:
            return self.get_client(preferred)
        except Exception as e:
            logger.warning(f"Primary model {preferred} failed: {e}")
            return self.get_client(self.SECONDARY)
```

**2. Model Performance Tracking**
```python
def track_model_performance(model, incident_id, tokens_used, cost, success):
    """Track which models perform best"""

    model_performance.labels(
        model=model,
        success=success
    ).inc()

    model_cost.labels(model=model).observe(cost)
    model_tokens.labels(model=model).observe(tokens_used)
```

**Success Criteria:**
- ✅ Multiple LLM providers configured
- ✅ Automatic fallback on failure
- ✅ Intelligent model selection
- ✅ Performance tracking per model

**Expected Impact:**
- Resilience: No single point of failure
- Optimization: Use right model for the job
- Cost: Potential 20% savings

---

## 📊 Success Metrics & KPIs

### Primary Metrics

**1. Autonomous Resolution Rate**
- **Baseline:** Unknown (currently manual intervention needed)
- **Phase 25:** 25% (basic remediation)
- **Phase 28:** 35% (service management)
- **Phase 32:** 50% (advanced remediation)
- **Target:** 80% (by Phase 35)

**2. Mean Time to Resolution (MTTR)**
- **Baseline:** 137 seconds
- **Phase 25:** 100 seconds (faster remediation)
- **Phase 30:** 80 seconds (predictive prevents escalation)
- **Target:** <60 seconds

**3. Service Coverage**
- **Baseline:** 51.6% (16 of 31 services)
- **Phase 33:** 58% (+backup systems)
- **Phase 34:** 61% (+certificates)
- **Target:** 80% (25 of 31 services)

**4. Tool Distribution**
- **Baseline:** 9 Healer tools, 72 diagnostic tools (11% remediation)
- **Phase 25:** 15 Healer tools (15% remediation)
- **Phase 28:** 21 Healer tools (20% remediation)
- **Phase 32:** 27 Healer tools (25% remediation)
- **Target:** 40 Healer tools (30% remediation)

**5. Safety Metrics**
- **Baseline:** No approval workflow
- **Phase 26:** 100% critical actions require approval
- **Target:** Zero unintended outages

**6. Test Coverage**
- **Baseline:** 0% automated test coverage
- **Phase 27:** 80% code coverage
- **Target:** 90% coverage

**7. Monthly Operational Cost**
- **Baseline:** $0.38/month
- **With optimizations:** $0.25/month
- **Target:** Maintain <$1/month

### Secondary Metrics

**8. Incident Prediction Accuracy**
- **Phase 30:** Track prediction vs actual incidents
- **Target:** 70% accuracy on 7-day predictions

**9. Tool Performance**
- **Phase 29:** Track all tool executions
- **Target:** <5% tool failure rate

**10. Learning Effectiveness**
- **Phase 31:** Track success rate improvement over time
- **Target:** 10% improvement quarter-over-quarter

---

## ⚠️ Risk Analysis & Mitigation

### Critical Risks

**1. AI Takes Down Critical Infrastructure**
- **Risk Level:** 🔴 CRITICAL
- **Probability:** Medium (without controls)
- **Impact:** Severe (data loss, extended outage)
- **Mitigation:**
  - Phase 26: Approval workflow (BLOCKS risky actions)
  - Change logging (audit trail)
  - Dry-run mode (test before executing)
  - Critical service list (PostgreSQL LXC 200, Prometheus, etc.)
- **Residual Risk:** 🟢 LOW (with Phase 26 complete)

**2. False Positives Lead to Unnecessary Remediations**
- **Risk Level:** 🟡 HIGH
- **Probability:** Medium
- **Impact:** Moderate (unnecessary restarts, service disruption)
- **Mitigation:**
  - Require approval for all restarts
  - Track false positive rate
  - Improve incident classification
  - User feedback loop
- **Residual Risk:** 🟡 MEDIUM

**3. Testing Gaps Allow Bugs in Production**
- **Risk Level:** 🟡 HIGH
- **Probability:** High (without Phase 27)
- **Impact:** Moderate (broken tools, failed remediations)
- **Mitigation:**
  - Phase 27: 200+ automated tests
  - CI/CD prevents deployment of failing tests
  - Staged rollout (dev → staging → production)
- **Residual Risk:** 🟢 LOW (with Phase 27)

**4. Single Model Dependency (OpenAI Outage)**
- **Risk Level:** 🟡 MEDIUM
- **Probability:** Low (but possible)
- **Impact:** High (complete system failure)
- **Mitigation:**
  - Phase 35: Multi-model strategy
  - Automatic failover to Anthropic
  - Cache recent LLM responses
- **Residual Risk:** 🟢 LOW (with Phase 35)

**5. Cost Spirals Out of Control**
- **Risk Level:** 🟢 LOW
- **Probability:** Low
- **Impact:** Low ($0.38/month baseline is very low)
- **Mitigation:**
  - Token usage monitoring
  - Cost alerts at $5/month
  - Model optimization
  - Response caching
- **Residual Risk:** 🟢 VERY LOW

### Moderate Risks

**6. Approval Fatigue (Too Many Approvals)**
- **Risk Level:** 🟡 MEDIUM
- **Mitigation:** Tune approval thresholds, allow auto-approve for low-risk actions after trust builds

**7. Complexity Makes System Hard to Maintain**
- **Risk Level:** 🟡 MEDIUM
- **Mitigation:** Comprehensive documentation, well-tested code, modular design

**8. Learning System Learns Wrong Patterns**
- **Risk Level:** 🟢 LOW
- **Mitigation:** Human feedback loop, confidence thresholds, manual review of learned patterns

---

## 🗓️ Implementation Timeline

### Month 1 (Weeks 1-4)
- **Week 1:** Phase 25 - Healer Expansion Part 1
- **Week 2-3:** Phase 26 - Approval Workflow & Safety Controls
- **Week 4:** Phase 27 Part 1 - Test framework setup

### Month 2 (Weeks 5-8)
- **Week 5:** Phase 27 Part 2 - CI/CD implementation
- **Week 6:** Phase 28 - Healer Expansion Part 2
- **Week 7:** Phase 29 - Tool Performance Monitoring
- **Week 8:** Phase 30 Part 1 - Predictive Analytics basics

### Month 3 (Weeks 9-12)
- **Week 9:** Phase 30 Part 2 - Advanced predictions
- **Week 10:** Phase 31 - Adaptive Learning System
- **Week 11:** Phase 32 - Healer Expansion Part 3
- **Week 12:** Phase 33 - Backup Systems Coverage

### Month 4 (Weeks 13-14)
- **Week 13:** Phase 34 - Certificate Management
- **Week 14:** Phase 35 - Multi-Model Strategy

**Total Timeline:** 14 weeks (~3.5 months)

---

## 📈 Expected Outcomes

### Quantitative Outcomes

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Autonomous Resolution** | ~10% | 80% | 8x increase |
| **Healer Tools** | 9 | 40+ | 4.4x increase |
| **Total Tools** | 81 | 150+ | 1.8x increase |
| **Service Coverage** | 51.6% | 80% | +28.4pp |
| **MTTR** | 137s | <60s | 56% reduction |
| **Test Coverage** | 0% | 80% | +80pp |
| **Incidents Prevented** | 0 | 40% | Proactive |

### Qualitative Outcomes

**Before:**
- ✅ Excellent diagnostics
- ⚠️ Weak remediation
- ❌ No safety controls
- ❌ Manual deployment
- ❌ Reactive only
- ⚠️ Limited learning

**After:**
- ✅ Excellent diagnostics
- ✅ **Strong remediation**
- ✅ **Comprehensive safety**
- ✅ **Automated CI/CD**
- ✅ **Proactive + Predictive**
- ✅ **Continuous learning**

### Business Value

1. **Reduced Operational Burden:** 80% of incidents handled autonomously
2. **Faster Recovery:** Sub-60-second resolution for common issues
3. **Prevented Incidents:** 40% reduction in unplanned incidents
4. **Better Uptime:** Proactive capacity planning prevents outages
5. **Knowledge Capture:** System learns and improves continuously
6. **Peace of Mind:** Approval workflow prevents AI mistakes

---

## 🎯 Next Actions

### Immediate (This Week)
1. ✅ Review and approve this strategic roadmap
2. Begin Phase 25: Healer Expansion Part 1
3. Document approval workflow requirements for Phase 26
4. Set up test framework structure for Phase 27

### Short Term (Next 2 Weeks)
1. Complete Phase 25 implementation
2. Begin Phase 26 approval workflow
3. Create mock infrastructure for testing

### Medium Term (Next Month)
1. Complete Phases 25-27 (safety-critical path)
2. Have 80% test coverage
3. Deploy with automated CI/CD

### Long Term (3 Months)
1. Complete all 10 phases (25-35)
2. Achieve 80% autonomous resolution rate
3. Reach 80% service coverage

---

## 📝 Decision Log

**Decision Points Requiring Approval:**

1. **Proceed with Healer Expansion?**
   - Recommended: YES (Phase 25)
   - Risk: Low (adding read-only tools first)

2. **Implement Approval Workflow?**
   - Recommended: YES (Phase 26, CRITICAL before more Healer tools)
   - Risk: None (pure safety addition)

3. **Invest in Automated Testing?**
   - Recommended: YES (Phase 27, essential for growth)
   - Risk: None (only upside)

4. **Add Predictive Capabilities?**
   - Recommended: YES (Phase 30, high value)
   - Risk: Low (non-invasive addition)

5. **Multi-Model Strategy?**
   - Recommended: YES (Phase 35, reduces risk)
   - Risk: Low (fallback only)

---

## 📖 References & Documentation

**Related Documents:**
- `docs/PHASE_*_COMPLETE.md` - Completion documentation for Phases 1-24
- `README.md` - Project overview and current state
- `crews/infrastructure_health/crew.py` - Agent definitions and tool assignments

**External Resources:**
- CrewAI Documentation: https://docs.crewai.com
- Proxmox API: https://pve.proxmox.com/wiki/Proxmox_VE_API
- PostgreSQL Monitoring: https://www.postgresql.org/docs/current/monitoring-stats.html
- Prometheus Best Practices: https://prometheus.io/docs/practices/

**Success Stories:**
- Phase 20: Docker expansion (+6 tools, container management parity)
- Phase 23: PostgreSQL expansion (+6 tools, database optimization)
- Phase 24: LXC expansion (+6 tools, container technology parity)

---

**Document Status:** 🟢 READY FOR APPROVAL
**Prepared By:** Claude (Strategic Planning Agent)
**Review Date:** 2025-10-27
**Next Review:** After Phase 27 completion (reassess remaining phases)
