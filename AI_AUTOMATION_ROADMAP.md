# Fjeld Homelab: CrewAI Autonomous Infrastructure

**Vision:** Deploy AI agent crews that autonomously manage, heal, and optimize your homelab 24/7 using Claude AI and OpenAI.

**Date:** 2025-10-26
**Status:** 🚀 Ready for Implementation
**Core Framework:** CrewAI + Claude Sonnet 4.5 + OpenAI

---

## 🎯 Why This Approach

**What We're Building:**
- Multi-agent crews that work as teams (not single agents)
- Powered by Claude Sonnet 4.5 (best reasoning) + OpenAI (embeddings)
- Zero local GPU needed - all AI in the cloud
- Agents run 24/7 on existing infrastructure (LXC 104)
- Full integration with Prometheus, Telegram, Proxmox, Docker

**What Makes This Different:**
```
Traditional Monitoring:              CrewAI Approach:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alert fires                         Alert fires
  └─→ Wakes you up                    └─→ Monitor Agent detects
      └─→ You investigate                  └─→ Analyst Agent diagnoses
          └─→ You fix                          └─→ Healer Agent fixes
              └─→ Manual work                      └─→ Notifies you it's done
                                                       └─→ Learns from incident
```

---

## 🧠 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude AI (Brain)                            │
│     Sonnet 4.5: Reasoning, Planning, Decision Making           │
└────────┬────────────────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────┐
    │         CrewAI Orchestration Layer                │
    │   (Running on LXC 104 - homelab-agents)          │
    │                                                   │
    │  Crews:                                           │
    │  ├─ Infrastructure Health Crew (4 agents)        │
    │  ├─ Security Response Crew (3 agents)            │
    │  ├─ Optimization Crew (2 agents)                 │
    │  └─ Documentation Crew (2 agents)                │
    └────┬──────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────────────┐
    │              Vector Memory (Qdrant)                │
    │        Stores: Past incidents, solutions,         │
    │        runbooks, learned patterns                 │
    └────┬──────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────────────┐
    │          Infrastructure Tools & APIs               │
    │  ├─ Prometheus (metrics)                          │
    │  ├─ Alertmanager (alerts)                         │
    │  ├─ Proxmox API (containers)                      │
    │  ├─ Docker API (services)                         │
    │  ├─ SSH (system commands)                         │
    │  ├─ PostgreSQL (databases)                        │
    │  ├─ GitHub API (GitOps)                           │
    │  └─ Telegram (notifications)                      │
    └───────────────────────────────────────────────────┘
```

---

## 📅 Implementation Phases

### Phase 1: Foundation (Week 1)

**Deploy CrewAI Infrastructure**

```bash
# Already on LXC 104 (homelab-agents)
cd /home/munky/homelab-agents

# Install CrewAI and dependencies
pip install crewai crewai-tools langchain-anthropic langchain-openai
pip install qdrant-client python-telegram-bot proxmoxer docker prometheus-api-client

# Verify API keys are loaded
python -c "import os; print('Claude:', bool(os.getenv('ANTHROPIC_API_KEY'))); print('OpenAI:', bool(os.getenv('OPENAI_API_KEY')))"
```

**Deploy Qdrant Vector Database (for agent memory)**

```bash
# On docker-gateway (LXC 101)
pct exec 101 -- bash -c 'mkdir -p /opt/qdrant/data'

# Add to docker-compose
pct exec 101 -- bash <<'EOF'
cat >> /opt/monitoring/docker-compose.yml <<'QDRANT'

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    networks:
      - monitoring
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - /opt/qdrant/data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
QDRANT
cd /opt/monitoring && docker compose up -d qdrant
EOF
```

---

### Phase 2: Infrastructure Health Crew (Week 1-2)

**The Team:**

1. **Monitor Agent** - Watches all systems
2. **Analyst Agent** - Investigates root causes
3. **Healer Agent** - Executes fixes
4. **Communicator Agent** - Reports to humans

**Implementation:**

```python
# /home/munky/homelab-agents/crews/infrastructure_health.py

from crewai import Agent, Task, Crew, Process
from crewai_tools import tool
from langchain_anthropic import ChatAnthropic
import os

# Initialize Claude Sonnet 4.5
llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.1  # Low temperature for reliability
)

# Custom Tools
@tool("Query Prometheus")
def query_prometheus(query: str) -> str:
    """Query Prometheus for metrics. Use PromQL syntax."""
    from prometheus_api_client import PrometheusConnect
    prom = PrometheusConnect(url="http://100.67.169.111:9090")
    result = prom.custom_query(query)
    return str(result)

@tool("Check Container Status")
def check_container_status(container_id: str) -> str:
    """Check LXC container status via Proxmox API."""
    from proxmoxer import ProxmoxAPI
    proxmox = ProxmoxAPI(
        os.getenv("PROXMOX_HOST"),
        user=os.getenv("PROXMOX_USER"),
        token_name="full-access",
        token_value=os.getenv("PROXMOX_TOKEN_SECRET"),
        verify_ssl=False
    )
    status = proxmox.nodes(os.getenv("PROXMOX_NODE")).lxc(container_id).status.current.get()
    return str(status)

@tool("Restart Docker Container")
def restart_docker_container(container_name: str) -> str:
    """Restart a Docker container on docker-gateway."""
    import docker
    client = docker.DockerClient(base_url='tcp://192.168.1.101:2375')
    container = client.containers.get(container_name)
    container.restart()
    return f"Container {container_name} restarted successfully"

@tool("Send Telegram Message")
def send_telegram(message: str) -> str:
    """Send message to Telegram chat."""
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
    return "Message sent"

# Define Agents
monitor_agent = Agent(
    role="Infrastructure Monitor",
    goal="Continuously detect anomalies and issues across all homelab systems",
    backstory="""You are an expert SRE with 15 years experience monitoring
    large-scale infrastructure. You have a sixth sense for detecting issues
    before they become critical. You know what normal looks like.""",
    tools=[query_prometheus, check_container_status],
    llm=llm,
    verbose=True
)

analyst_agent = Agent(
    role="Root Cause Analyst",
    goal="Investigate issues and determine the true root cause",
    backstory="""You are a brilliant debugger who has solved thousands of
    production incidents. You think in systems, understand dependencies,
    and always find the real cause (not just symptoms).""",
    tools=[query_prometheus, check_container_status],
    llm=llm,
    verbose=True
)

healer_agent = Agent(
    role="Auto-Remediation Specialist",
    goal="Fix issues autonomously when safe to do so",
    backstory="""You are an automation expert who has codified decades of
    operational knowledge. You know when it's safe to fix automatically
    and when to escalate to humans. You never make things worse.""",
    tools=[restart_docker_container, check_container_status],
    llm=llm,
    verbose=True
)

communicator_agent = Agent(
    role="Communications Officer",
    goal="Keep humans informed with clear, actionable updates",
    backstory="""You translate complex technical issues into clear English.
    You know what information matters to humans and always provide context
    about impact and next steps.""",
    tools=[send_telegram],
    llm=llm,
    verbose=True
)

# Define Tasks
def create_incident_response_tasks(alert_data):
    """Create tasks for incident response workflow"""

    detect_task = Task(
        description=f"""Analyze this alert and determine severity:

        Alert Data: {alert_data}

        Check:
        1. Is this a real issue or false positive?
        2. What systems are affected?
        3. What is the current state vs expected state?
        4. Is this urgent?

        Provide a clear assessment.""",
        agent=monitor_agent,
        expected_output="Detailed assessment of the alert with severity level"
    )

    diagnose_task = Task(
        description="""Based on the monitor's assessment, investigate root cause:

        1. Query relevant Prometheus metrics
        2. Check system logs and container status
        3. Identify dependencies and correlations
        4. Determine the actual root cause (not symptoms)

        Provide root cause analysis with evidence.""",
        agent=analyst_agent,
        expected_output="Root cause analysis with supporting metrics",
        context=[detect_task]
    )

    heal_task = Task(
        description="""Based on the root cause analysis, determine fix:

        1. What is the safest fix for this issue?
        2. What is the risk level? (low/medium/high)
        3. If risk is LOW, execute the fix automatically
        4. If risk is MEDIUM or HIGH, propose fix for human approval

        Execute or propose the fix.""",
        agent=healer_agent,
        expected_output="Fix executed or proposed with risk assessment",
        context=[diagnose_task]
    )

    communicate_task = Task(
        description="""Summarize the incident for humans:

        Create a Telegram message with:
        1. What happened (in plain English)
        2. What was the root cause
        3. What action was taken
        4. Current status
        5. Any follow-up needed

        Send the message.""",
        agent=communicator_agent,
        expected_output="Telegram notification sent with incident summary",
        context=[detect_task, diagnose_task, heal_task]
    )

    return [detect_task, diagnose_task, heal_task, communicate_task]

# Create Crew
infrastructure_crew = Crew(
    agents=[monitor_agent, analyst_agent, healer_agent, communicator_agent],
    tasks=[],  # Tasks created dynamically per incident
    process=Process.sequential,  # Execute in order
    verbose=2
)

# Main execution function
def handle_alert(alert_json):
    """Main entry point for alert handling"""
    tasks = create_incident_response_tasks(alert_json)
    infrastructure_crew.tasks = tasks
    result = infrastructure_crew.kickoff()
    return result
```

**Integration with Alertmanager:**

```bash
# Update Alertmanager to call CrewAI
pct exec 101 -- bash <<'EOF'
cat > /opt/monitoring/alertmanager/config/alertmanager.yml <<'YAML'
global:
  resolve_timeout: 5m

route:
  group_by: ["alertname", "cluster", "service"]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: "crewai-handler"

receivers:
  - name: "crewai-handler"
    webhook_configs:
      - url: "http://192.168.1.102:5000/alert"
        send_resolved: true
YAML
docker restart alertmanager
EOF
```

**Flask Webhook Server:**

```python
# /home/munky/homelab-agents/alert_webhook.py

from flask import Flask, request, jsonify
from crews.infrastructure_health import handle_alert
import threading

app = Flask(__name__)

@app.route('/alert', methods=['POST'])
def receive_alert():
    """Receive alert from Alertmanager and dispatch to CrewAI"""
    alert_data = request.json

    # Handle in background thread (don't block webhook)
    thread = threading.Thread(
        target=handle_alert,
        args=(alert_data,)
    )
    thread.start()

    return jsonify({"status": "accepted"}), 202

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

### Phase 3: Security Response Crew (Week 2-3)

**The Team:**

1. **Threat Hunter** - Scans for vulnerabilities and intrusions
2. **Incident Commander** - Coordinates response
3. **Forensics Agent** - Analyzes security events

```python
# /home/munky/homelab-agents/crews/security_response.py

from crewai import Agent, Crew
from crewai_tools import tool

@tool("Scan Container for CVEs")
def scan_for_cves(container_name: str) -> str:
    """Scan Docker container for known vulnerabilities using Trivy."""
    import subprocess
    result = subprocess.run(
        ["docker", "run", "--rm", "-v", "/var/run/docker.sock:/var/run/docker.sock",
         "aquasec/trivy:latest", "image", container_name],
        capture_output=True, text=True
    )
    return result.stdout

@tool("Check Failed Login Attempts")
def check_failed_logins() -> str:
    """Check auth logs for brute force attempts."""
    import subprocess
    result = subprocess.run(
        ["pct", "exec", "101", "--", "grep", "Failed password", "/var/log/auth.log"],
        capture_output=True, text=True
    )
    return result.stdout

threat_hunter = Agent(
    role="Security Threat Hunter",
    goal="Proactively find security vulnerabilities and suspicious activity",
    backstory="Former red team lead with deep knowledge of attack patterns",
    tools=[scan_for_cves, check_failed_logins],
    llm=llm
)

incident_commander = Agent(
    role="Security Incident Commander",
    goal="Coordinate response to security threats",
    backstory="CISSP with experience leading IR teams at major tech companies",
    tools=[],
    llm=llm
)

# Security crew runs on schedule (daily scans)
security_crew = Crew(
    agents=[threat_hunter, incident_commander],
    tasks=[],  # Created dynamically
    process=Process.sequential
)
```

---

### Phase 4: Optimization Crew (Week 3-4)

**The Team:**

1. **Performance Analyst** - Finds bottlenecks and inefficiencies
2. **Capacity Planner** - Predicts future resource needs

```python
# /home/munky/homelab-agents/crews/optimization.py

from crewai import Agent

performance_analyst = Agent(
    role="Performance Analyst",
    goal="Identify optimization opportunities across infrastructure",
    backstory="""Performance engineer who has optimized systems at massive scale.
    Obsessed with efficiency and resource utilization.""",
    tools=[query_prometheus],
    llm=llm
)

capacity_planner = Agent(
    role="Capacity Planner",
    goal="Predict future resource needs and prevent capacity issues",
    backstory="""SRE who prevented countless outages through accurate forecasting.
    Uses historical data to predict future trends.""",
    tools=[query_prometheus],
    llm=llm
)

# Weekly optimization analysis
optimization_crew = Crew(
    agents=[performance_analyst, capacity_planner],
    tasks=[],
    process=Process.sequential
)
```

---

### Phase 5: Documentation Crew (Week 4)

**The Team:**

1. **Documentation Writer** - Creates and updates docs
2. **Knowledge Manager** - Maintains vector database

```python
# /home/munky/homelab-agents/crews/documentation.py

from crewai import Agent
from crewai_tools import tool

@tool("Update Git Repository")
def update_git_docs(file_path: str, content: str) -> str:
    """Commit documentation updates to GitHub."""
    import subprocess
    with open(file_path, 'w') as f:
        f.write(content)

    subprocess.run(["git", "add", file_path])
    subprocess.run(["git", "commit", "-m", f"Auto-update: {file_path}"])
    subprocess.run(["git", "push"])
    return f"Updated {file_path}"

doc_writer = Agent(
    role="Technical Documentation Writer",
    goal="Maintain accurate, up-to-date infrastructure documentation",
    backstory="Technical writer who makes complex systems understandable",
    tools=[update_git_docs],
    llm=llm
)

knowledge_manager = Agent(
    role="Knowledge Manager",
    goal="Store and organize operational knowledge in vector database",
    backstory="Information architect who builds searchable knowledge systems",
    tools=[],
    llm=llm
)

# Daily documentation updates
documentation_crew = Crew(
    agents=[doc_writer, knowledge_manager],
    tasks=[],
    process=Process.sequential
)
```

---

## 🚀 Deployment Strategy

### Week 1: Core Setup

```bash
# Day 1-2: Install Dependencies
cd /home/munky/homelab-agents
source venv/bin/activate
pip install crewai crewai-tools langchain-anthropic langchain-openai \
    qdrant-client prometheus-api-client proxmoxer docker \
    python-telegram-bot flask

# Deploy Qdrant
# (See Phase 1 commands above)

# Day 3-4: Build Infrastructure Health Crew
mkdir -p crews
# Create crews/infrastructure_health.py (see Phase 2 code)
# Create alert_webhook.py (see Phase 2 code)

# Day 5: Test First Agent
python -c "from crews.infrastructure_health import infrastructure_crew; print(infrastructure_crew)"

# Day 6-7: Integration Testing
# Start webhook server
python alert_webhook.py &

# Trigger test alert
curl -X POST http://localhost:5000/alert -H "Content-Type: application/json" -d '{
  "alerts": [{
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"summary": "Test alert for CrewAI"}
  }]
}'
```

### Week 2: Production Deployment

```bash
# Create systemd service
sudo bash <<'EOF'
cat > /etc/systemd/system/crewai-webhook.service <<'SERVICE'
[Unit]
Description=CrewAI Alert Webhook Server
After=network.target

[Service]
Type=simple
User=munky
WorkingDirectory=/home/munky/homelab-agents
Environment="PATH=/home/munky/homelab-agents/venv/bin"
ExecStart=/home/munky/homelab-agents/venv/bin/python alert_webhook.py
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable crewai-webhook
systemctl start crewai-webhook
EOF
```

---

## 📊 Real-World Example: PostgreSQL Incident

**Scenario:** PostgreSQL memory usage spikes to 95%

**Traditional Response (You):**
1. Wake up to Telegram alert (2 AM) 😴
2. SSH into server
3. Check logs, run queries
4. Find long-running query
5. Kill query, restart connection pool
6. Go back to sleep
**Total time:** 30 minutes

**CrewAI Response (Autonomous):**
```
02:00:00 - Monitor Agent detects alert from Prometheus
02:00:05 - Analyst Agent queries PostgreSQL metrics
02:00:10 - Finds: Query on users table running for 45 minutes
02:00:15 - Cross-references: No index on email column (new query pattern)
02:00:20 - Healer Agent assesses: Low risk to kill query
02:00:25 - Executes: Kills query, restarts pgbouncer
02:00:30 - Verifies: Memory back to normal (45%)
02:00:35 - Communicator sends Telegram:

🤖 *Incident Resolved Automatically*

*What happened:* PostgreSQL memory spiked to 95%

*Root cause:* Unoptimized query on users table (missing index on email column)

*Action taken:*
- Killed long-running query (PID 12345)
- Restarted pgbouncer connection pool
- Memory now at 45% (normal)

*Recommendation:*
Consider adding index: `CREATE INDEX idx_users_email ON users(email);`

*Status:* ✅ Resolved (no action needed)
02:00:35 - Stores incident in vector DB for future learning
```

**Total time:** 35 seconds

You wake up to "issue already fixed" notification. ☕

---

## 🎯 Success Metrics

### Before CrewAI:
| Metric | Value |
|--------|-------|
| Mean Time to Detect (MTTD) | 15+ minutes |
| Mean Time to Resolve (MTTR) | 30+ minutes |
| Incidents requiring human intervention | 100% |
| Nighttime wake-ups per month | 2-3 |
| Documentation accuracy | ~60% (often stale) |

### After CrewAI (Target):
| Metric | Value | Improvement |
|--------|-------|-------------|
| MTTD | < 30 seconds | **97% faster** |
| MTTR | < 2 minutes | **93% faster** |
| Auto-resolved incidents | 70%+ | **70% reduction in manual work** |
| Nighttime wake-ups | < 1/quarter | **90% reduction** |
| Documentation accuracy | 95%+ | **Always current** |

---

## 💰 Cost Analysis

### API Costs (Estimated Monthly):

**Claude Sonnet 4.5:**
- Input: $3 per million tokens
- Output: $15 per million tokens
- Estimated usage: ~10M tokens/month
- **Cost: ~$30-50/month**

**OpenAI (Embeddings):**
- text-embedding-3-small: $0.02 per million tokens
- Estimated usage: ~5M tokens/month
- **Cost: ~$5/month**

**Total AI Costs: ~$35-55/month**

**Value:**
- Time saved: 20+ hours/month
- Sleep quality: Priceless
- Learning experience: Invaluable
- Coolness factor: Maximum

---

## 🔧 Advanced Features

### 1. Incident Learning

Every incident is stored in Qdrant vector DB:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

# Initialize
qdrant = QdrantClient(url="http://192.168.1.101:6333")
embeddings = OpenAIEmbeddings()

# Store incident
def store_incident(incident_data, resolution):
    # Create embedding
    text = f"{incident_data}\n\nResolution: {resolution}"
    vector = embeddings.embed_query(text)

    # Store in Qdrant
    qdrant.upsert(
        collection_name="incidents",
        points=[PointStruct(
            id=incident_id,
            vector=vector,
            payload={"data": incident_data, "resolution": resolution}
        )]
    )

# Retrieve similar incidents
def find_similar_incidents(current_issue):
    vector = embeddings.embed_query(current_issue)
    results = qdrant.search(
        collection_name="incidents",
        query_vector=vector,
        limit=5
    )
    return results
```

**Agents can now:**
- Query: "Have we seen this before?"
- Learn: "What worked last time?"
- Improve: "Apply historical solutions faster"

### 2. Natural Language Control

**Enhanced Telegram Bot:**

```python
# Add to existing Telegram bot

@bot.message_handler(func=lambda m: True)
def ai_assistant(message):
    """Send any message to Claude for interpretation"""
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")

    response = llm.invoke([{
        "role": "user",
        "content": f"""You are a homelab assistant. The user said: "{message.text}"

        Interpret their request and respond with:
        1. What they want
        2. Current status
        3. Any actions you recommend

        Available tools: Check metrics, restart containers, view logs, create containers."""
    }])

    bot.reply_to(message, response.content)
```

**Usage:**
```
You: "Is everything okay?"
AI: "All systems healthy. CPU at 25%, memory at 45%. No alerts."

You: "Why is grafana slow?"
AI: "Checking... Grafana container using 90% of allocated memory. Restarting now."

You: "Create a test WordPress site"
AI: "Creating LXC container with WordPress + MySQL. Will be ready in 2 minutes at https://test.fjeld.tech"
```

### 3. Scheduled Crew Runs

```python
# /home/munky/homelab-agents/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from crews.security_response import security_crew
from crews.optimization import optimization_crew
from crews.documentation import documentation_crew

scheduler = BackgroundScheduler()

# Security scan - Daily at 3 AM
scheduler.add_job(
    security_crew.kickoff,
    'cron',
    hour=3,
    id='security_scan'
)

# Optimization analysis - Weekly Sunday 2 AM
scheduler.add_job(
    optimization_crew.kickoff,
    'cron',
    day_of_week='sun',
    hour=2,
    id='optimization'
)

# Documentation update - Daily at 1 AM
scheduler.add_job(
    documentation_crew.kickoff,
    'cron',
    hour=1,
    id='docs_update'
)

scheduler.start()
```

---

## 🎓 Learning Resources

### CrewAI Documentation
- [Official Docs](https://docs.crewai.com/)
- [Agent Configuration](https://docs.crewai.com/core-concepts/Agents/)
- [Tools & Integrations](https://docs.crewai.com/core-concepts/Tools/)

### Claude AI
- [Anthropic Console](https://console.anthropic.com/)
- [Model Comparison](https://docs.anthropic.com/en/docs/about-claude/models)
- [Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)

### Example Repositories
- [CrewAI Examples](https://github.com/joaomdmoura/crewAI-examples)
- [Production Agent Systems](https://github.com/topics/crewai)

---

## 🚦 Quick Start Commands

```bash
# Week 1 - Get Started Now

# 1. Install dependencies
cd /home/munky/homelab-agents
source venv/bin/activate
pip install crewai crewai-tools langchain-anthropic qdrant-client flask

# 2. Test Claude API
python <<EOF
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")
response = llm.invoke("Say hello!")
print(response.content)
EOF

# 3. Deploy Qdrant (memory database)
pct exec 101 -- docker run -d --name qdrant -p 6333:6333 -v /opt/qdrant:/qdrant/storage qdrant/qdrant

# 4. Create first crew (use code from Phase 2)
mkdir -p crews
# Copy infrastructure_health.py code into crews/

# 5. Start webhook server
python alert_webhook.py
```

---

## 🎯 Next Steps

1. **Today:** Install dependencies, test Claude API
2. **This Week:** Build Infrastructure Health Crew
3. **Next Week:** Deploy to production, handle first real alert
4. **Week 3:** Add Security and Optimization Crews
5. **Week 4:** Fine-tune, add custom tools, measure impact

---

## 📞 Support & Troubleshooting

### Common Issues

**"CrewAI agent not responding"**
```bash
# Check logs
journalctl -u crewai-webhook -n 50

# Test Claude API directly
python -c "from langchain_anthropic import ChatAnthropic; ChatAnthropic().invoke('test')"
```

**"Qdrant connection failed"**
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Test connection
curl http://192.168.1.101:6333/collections
```

**"High API costs"**
- Use temperature=0.1 for more deterministic (cheaper) responses
- Cache common queries in Qdrant
- Implement rate limiting on webhook endpoint

---

## 🎬 Conclusion

**You're building agents that:**
- ✅ Never sleep
- ✅ Never forget
- ✅ Learn from every incident
- ✅ Fix issues in seconds
- ✅ Keep you informed
- ✅ Get smarter over time

**This isn't just automation.**

**This is having a 24/7 SRE team powered by Claude AI.**

**Start with Phase 1. Build incrementally. Ship value fast.**

---

*Last Updated: 2025-10-26*
*Framework: CrewAI + Claude Sonnet 4.5*
*Estimated Time to First Agent: 1-2 hours*
*Estimated Time to Full Autonomy: 4 weeks*
