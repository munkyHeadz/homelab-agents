# AI Agent Deployment Status

## ✅ Phase 1: Foundation - COMPLETED

### Installation
- ✓ CrewAI 1.2.0 installed
- ✓ langchain-anthropic (Claude API integration)
- ✓ langchain-openai
- ✓ Qdrant client
- ✓ Prometheus API client
- ✓ Proxmoxer (Proxmox API)
- ✓ Docker SDK
- ✓ Flask + APScheduler

### Infrastructure
- ✓ Qdrant vector database deployed (localhost:6333)
  - Running as Docker container
  - Collection 'agent_memory' created for incident storage
- ✓ Claude API tested and working
  - Model: claude-3-5-sonnet-20241022
  - API key validated

### Crew Implementation
- ✓ **Infrastructure Health Crew** built with 4 agents:
  1. **Monitor Agent** - Detects anomalies using Prometheus metrics
  2. **Analyst Agent** - Diagnoses root causes
  3. **Healer Agent** - Executes autonomous remediation
  4. **Communicator Agent** - Sends Telegram notifications

- ✓ **Custom Tools** created:
  - `query_prometheus` - Query Prometheus metrics (PromQL)
  - `check_container_status` - Docker container monitoring
  - `restart_container` - Auto-restart containers
  - `check_container_logs` - Retrieve container logs
  - `check_lxc_status` - Proxmox LXC container status
  - `restart_lxc` - Restart LXC containers
  - `send_telegram` - Send notifications to @Bobbaerbot

### Application Server
- ✓ Flask webhook server created (`agent_server.py`)
  - `/health` - Health check endpoint
  - `/alert` - Receives Alertmanager webhooks
  - `/trigger-health-check` - Manual health check trigger
- ✓ APScheduler configured for proactive checks (every 5 minutes)

## 📋 Next Steps (Phase 2)

### 1. Create systemd service
```bash
sudo tee /etc/systemd/system/homelab-agents.service <<EOF
[Unit]
Description=Homelab AI Agent Server
After=network.target docker.service

[Service]
Type=simple
User=munky
WorkingDirectory=/home/munky/homelab-agents
Environment="PATH=/home/munky/homelab-agents/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/munky/homelab-agents/venv/bin/python3 /home/munky/homelab-agents/agent_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable homelab-agents
sudo systemctl start homelab-agents
```

### 2. Configure Alertmanager webhook
Update Alertmanager configuration on docker-gateway (100.67.169.111):

```yaml
route:
  receiver: 'ai-agents'
  routes:
    - match:
        severity: critical
      receiver: 'ai-agents'
    - match:
        severity: warning
      receiver: 'ai-agents'

receivers:
  - name: 'ai-agents'
    webhook_configs:
      - url: 'http://100.70.233.86:5000/alert'  # LXC 104 Tailscale IP
        send_resolved: false
```

### 3. Test end-to-end workflow
```bash
# Trigger a test alert
curl -X POST http://100.70.233.86:5000/alert -H "Content-Type: application/json" -d '{
  "alerts": [{
    "status": "firing",
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"description": "Test alert for AI agents"}
  }]
}'

# Check logs
tail -f /home/munky/homelab-agents/agent_server.log
```

## 🎯 Expected Behavior

When an alert fires:
1. Alertmanager sends webhook to agent server
2. **Monitor Agent** verifies alert using Prometheus + Docker
3. **Analyst Agent** examines logs and metrics for root cause
4. **Healer Agent** executes remediation (restart container/LXC)
5. **Communicator Agent** sends Telegram summary to @Bobbaerbot

**Estimated Resolution Time:** 30-60 seconds (vs. 20+ minutes manual)

## 📊 System Architecture

```
┌─────────────────┐
│   Prometheus    │ ──metrics──┐
│  100.67.169.111 │            │
└─────────────────┘            │
                               ▼
┌─────────────────┐      ┌──────────────────┐
│  Alertmanager   │─────▶│  Agent Server    │
│  100.67.169.111 │      │  (LXC 104)       │
└─────────────────┘      │  100.70.233.86   │
                         └──────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  ┌─────────┐           ┌───────────┐         ┌──────────┐
  │ Monitor │           │  Analyst  │         │  Healer  │
  │  Agent  │──────────▶│   Agent   │────────▶│  Agent   │
  └─────────┘           └───────────┘         └──────────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │ Communicator │
                                             │    Agent     │
                                             └──────────────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │   Telegram   │
                                             │  @Bobbaerbot │
                                             └──────────────┘
```

## 💰 Cost Analysis

- Claude API (Sonnet 3.5): ~$3 per 1M input tokens, $15 per 1M output tokens
- Estimated usage: 50-100 incidents/month
- Average tokens per incident: ~10K input, 2K output
- **Monthly cost: $5-15** (vs. 20+ hours of manual work saved)

## 🔗 Files Created

```
homelab-agents/
├── agent_server.py           # Flask webhook server + scheduler
├── test_crew.py              # Test script for crew validation
├── crews/
│   ├── infrastructure_health/
│   │   ├── __init__.py
│   │   └── crew.py          # 4-agent crew implementation
│   └── tools/
│       ├── __init__.py
│       └── homelab_tools.py # Custom Prometheus/Docker/Proxmox tools
└── venv/                     # Python virtual environment
```

## 🚀 Current Status

**Phase 1: COMPLETED ✅**

All core infrastructure is built and ready. The AI agents are configured and tested.

**Next Action:** Deploy as systemd service and configure Alertmanager webhook to begin autonomous operations.

---

*Generated: 2025-10-26*
*Location: LXC 104 (homelab-agents) - 192.168.1.104 / 100.70.233.86*
