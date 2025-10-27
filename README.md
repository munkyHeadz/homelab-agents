# Homelab AI Agents - Autonomous Incident Response System

**An autonomous AI-powered incident response system with continuous learning for homelab infrastructure management.**

[![Status](https://img.shields.io/badge/status-production-success)](http://100.67.169.111:5000/health)
[![Success Rate](https://img.shields.io/badge/success%20rate-100%25-success)]()
[![Monthly Cost](https://img.shields.io/badge/monthly%20cost-$0.38-blue)]()
[![Tools](https://img.shields.io/badge/autonomous%20tools-87-blue)]()
[![Coverage](https://img.shields.io/badge/service%20coverage-51.6%25-success)]()

---

## 🎯 Overview

A **fully autonomous AI incident response system** that detects, diagnoses, and remediates infrastructure issues automatically using a 4-agent CrewAI architecture. The system learns from every incident to improve future responses.

### Key Features

- ✅ **Autonomous Incident Response** - End-to-end handling without human intervention
- ✅ **Continuous Learning** - Vector memory with semantic search for similar incidents
- ✅ **Multi-Layer Monitoring** - Infrastructure, network, and database visibility
- ✅ **Production Ready** - Deployed and tested with 100% success rate
- ✅ **Cost Effective** - $0.16/month for 100 incidents
- ✅ **Observable** - Complete monitoring stack with visual dashboards

### What It Does

1. **Detects** infrastructure incidents from Prometheus Alertmanager
2. **Diagnoses** root causes using AI analysis + historical context
3. **Remediates** issues autonomously with safe remediation strategies
4. **Notifies** humans via Telegram with incident summaries
5. **Learns** from every incident for continuous improvement

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| **Incidents Processed** | 8 total |
| **Success Rate** | 100% |
| **Average Resolution** | 137 seconds (~2.3 minutes) |
| **Tools Available** | 87 autonomous tools |
| **Integrations** | 15 services (48.4% of available) |
| **Network Devices** | 25+ Tailscale, 6+ UniFi APs/switches |
| **Databases Monitored** | 3+ PostgreSQL |
| **VMs/Containers** | Proxmox VMs + LXCs |
| **DNS Monitoring** | Cloudflare + AdGuard Home |
| **Monthly Cost** | $0.38 (GPT-4o-mini + embeddings) |

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Homelab Infrastructure                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Prometheus (9090) ──▶ Alertmanager (9093)                    │
│         │                      │                               │
│         │                      │ webhook                       │
│         │                      ▼                               │
│         │              AI Agents (5000)                        │
│         │              docker-gateway                          │
│         │                      │                               │
│         │              ┌───────┴────────┐                     │
│         │              │  4-Agent Crew   │                     │
│         │              ├─────────────────┤                     │
│         │              │ 1. Monitor      │────────┐           │
│         │              │ 2. Analyst  ◄───┼── Qdrant Memory    │
│         │              │ 3. Healer       │────────┘           │
│         │              │ 4. Communicator │                     │
│         │              └────────┬────────┘                     │
│         │                       │                               │
│         │         ┌─────────────┼───────────────┐             │
│         │         │             │               │             │
│         │         ▼             ▼               ▼             │
│         │   Tailscale (25)  PostgreSQL    Docker/Proxmox     │
│         │    Devices         (LXC 200)    (Remediation)       │
│         │                                                       │
│         ▼                                                       │
│  Grafana (3000) - Dashboard with 9 panels                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Available Tools

The AI agents have access to **87 autonomous tools** across 5 categories:

### Container & Virtualization (28 tools)
- **Docker (11 tools)**:
  - `check_container_status` - Check Docker container status
  - `restart_container` - Restart Docker containers
  - `check_container_logs` - Retrieve container logs
  - `list_docker_images` - Image inventory and dangling image detection
  - `prune_docker_images` - Automated cleanup of unused images
  - `inspect_docker_network` - Network troubleshooting and diagnostics
  - `check_docker_volumes` - Volume usage and orphaned volume detection
  - `get_container_resource_usage` - Real-time CPU/memory/network/IO stats
  - `check_docker_system_health` - Overall Docker daemon health
  - `update_docker_resources` - Dynamically update container resource limits (Phase 25)
- **LXC Containers (11 tools)**:
  - `check_lxc_status` - Query LXC container status
  - `restart_lxc` - Restart LXC containers
  - `list_lxc_containers` - List all LXC containers with status and resources
  - `check_lxc_logs` - Retrieve container logs for troubleshooting
  - `get_lxc_resource_usage` - Real-time CPU/memory/disk/network stats
  - `check_lxc_snapshots` - Snapshot management and backup verification
  - `check_lxc_network` - Network configuration and diagnostics
  - `get_lxc_config` - Configuration validation and security review
  - `update_lxc_resources` - Dynamically adjust CPU/memory/swap allocation (Phase 25)
  - `create_lxc_snapshot` - Create snapshots for rollback capability (Phase 25)
  - `restart_postgres_service` - Restart PostgreSQL service inside LXC (Phase 25)
- **Proxmox VMs (6 tools)**:
  - `check_proxmox_node_health` - Monitor Proxmox node resources (CPU, memory, storage)
  - `list_proxmox_vms` - List all VMs with status
  - `check_proxmox_vm_status` - Detailed VM diagnostics
  - `get_proxmox_storage_status` - Storage pool monitoring
  - `get_proxmox_cluster_status` - Cluster health and quorum
  - `get_proxmox_system_summary` - Complete platform overview
- **Monitoring (1 tool)**:
  - `query_prometheus` - Query Prometheus for metrics using PromQL
- **Communications (1 tool)**:
  - `send_telegram` - Send Telegram notifications

### Network Monitoring (16 tools)
- `list_tailscale_devices` - List all devices in Tailscale network
- `check_device_connectivity` - Check specific device details
- `monitor_vpn_health` - Monitor overall VPN health
- `get_critical_infrastructure_status` - Check critical services
- `list_unifi_devices` - UniFi network device inventory
- `check_ap_health` - WiFi Access Point health monitoring
- `monitor_network_clients` - Connected client tracking
- `check_wan_connectivity` - WAN uplink monitoring
- `monitor_switch_ports` - Switch port status and statistics
- `get_network_performance` - Network performance metrics
- `list_cloudflare_zones` - Cloudflare DNS zone inventory
- `check_zone_health` - DNS zone health and configuration
- `get_cloudflare_analytics` - Traffic analytics and insights
- `check_security_events` - Security event monitoring
- `monitor_dns_records` - DNS record monitoring
- `get_cloudflare_status` - Overall Cloudflare service status

### DNS & Security (5 tools)
- `check_adguard_status` - AdGuard Home service health
- `get_dns_query_stats` - DNS query statistics and analytics
- `check_blocklist_status` - Blocklist status and effectiveness
- `monitor_dns_clients` - DNS client activity tracking
- `get_adguard_protection_summary` - Protection summary dashboard

### Smart Home (6 tools)
- `check_homeassistant_status` - Home Assistant service health
- `list_homeassistant_entities` - Entity discovery and inventory
- `get_entity_state` - Detailed entity information
- `get_entity_history` - Historical state tracking
- `check_automation_status` - Automation monitoring
- `get_homeassistant_summary` - Dashboard overview

### Monitoring Stack (19 tools)
- **Prometheus (7 tools)**:
  - `check_prometheus_targets` - Scrape target monitoring
  - `check_prometheus_rules` - Rule evaluation monitoring
  - `get_prometheus_alerts` - Active alert tracking
  - `check_prometheus_tsdb` - Time Series Database health
  - `get_prometheus_runtime_info` - Runtime information
  - `get_prometheus_config_status` - Configuration management
  - `query_prometheus` - PromQL metrics queries
- **Alertmanager (6 tools)**:
  - `list_active_alerts` - View currently firing alerts
  - `list_alert_silences` - Manage maintenance silences
  - `create_alert_silence` - Automated silence creation
  - `delete_alert_silence` - Early silence removal
  - `check_alert_routing` - Verify routing configuration
  - `get_alertmanager_status` - Overall health status
- **Grafana (6 tools)**:
  - `add_annotation` - Mark incidents on graphs
  - `get_grafana_status` - Health and version monitoring
  - `list_dashboards` - Dashboard discovery
  - `get_dashboard` - Detailed dashboard information
  - `create_snapshot` - Capture dashboard state
  - `list_datasources` - Verify datasource connectivity

### Database Monitoring (13 tools)
- **PostgreSQL (13 tools)**:
  - `check_postgres_health` - PostgreSQL server health & connections
  - `query_database_performance` - Long-running queries & locks
  - `check_database_sizes` - Database & table size analysis
  - `monitor_database_connections` - Connection pool tracking
  - `check_specific_database` - Detailed database information
  - `check_replication_status` - Replication lag and replica health monitoring
  - `check_table_bloat` - Identify bloated tables needing VACUUM FULL
  - `analyze_slow_queries` - Query performance analysis (requires pg_stat_statements)
  - `check_index_health` - Detect unused indexes and optimization opportunities
  - `monitor_vacuum_status` - Track autovacuum operations
  - `check_database_locks` - Analyze blocking queries and deadlocks
  - `vacuum_postgres_table` - Reclaim space from dead tuples (Phase 25)
  - `clear_postgres_connections` - Terminate active database connections (Phase 25)

---

## 🚀 Quick Start

### Prerequisites

- Docker (for containerized deployment)
- Prometheus + Alertmanager (for alert routing)
- Qdrant vector database (for incident memory)
- OpenAI API key (for GPT-4o-mini)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/munkyHeadz/homelab-agents.git
   cd homelab-agents
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - OPENAI_API_KEY
   # - TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID
   # - PROXMOX_HOST, PROXMOX_TOKEN_SECRET
   # - POSTGRES_HOST, POSTGRES_USER_AGENT, POSTGRES_PASSWORD_AGENT
   # - TAILSCALE_API_KEY, TAILSCALE_TAILNET
   # - QDRANT_URL
   ```

3. **Build Docker image**
   ```bash
   docker build -t homelab-agents:latest .
   ```

4. **Run container**
   ```bash
   docker run -d \
     --name homelab-agents \
     --restart unless-stopped \
     --network monitoring \
     -p 5000:5000 \
     -v /var/run/docker.sock:/var/run/docker.sock \
     homelab-agents:latest
   ```

5. **Configure Alertmanager**
   ```yaml
   route:
     receiver: 'ai-agents'
     routes:
       - match:
           alertname: '.*'
         receiver: 'ai-agents'

   receivers:
     - name: 'ai-agents'
       webhook_configs:
         - url: 'http://100.67.169.111:5000/alert'
           send_resolved: true
   ```

6. **Verify deployment**
   ```bash
   curl http://localhost:5000/health
   # {"status":"healthy","service":"homelab-ai-agents","version":"1.1.0"}
   ```

---

## 📡 API Endpoints

### Health & Status
```bash
GET /health          # Service health check
GET /stats           # Incident statistics
GET /incidents       # List stored incidents
GET /metrics         # Prometheus metrics
```

### Webhook
```bash
POST /alert          # Receive Alertmanager webhooks
```

### Example Usage
```bash
# Check system health
curl http://100.67.169.111:5000/health

# Get incident statistics
curl http://100.67.169.111:5000/stats

# List recent incidents
curl http://100.67.169.111:5000/incidents?limit=10

# View Prometheus metrics
curl http://100.67.169.111:5000/metrics
```

---

## 🔄 Incident Response Workflow

```
1. Alert Fires → Prometheus detects issue
2. Alertmanager Routes → Sends webhook to AI agents
3. Monitor Validates → Verifies alert legitimacy (~15s)
4. Analyst Diagnoses → Root cause analysis with historical context (~15s)
5. Healer Remediates → Executes fix autonomously (~5s)
6. Communicator Notifies → Sends Telegram summary (<1s)
7. Memory Stores → Saves incident for learning (<1s)

Total: ~40-140 seconds end-to-end
```

---

## 🎯 Agent Descriptions

### 1. Monitor Agent
**Role:** Infrastructure Monitor
**Goal:** Detect anomalies and issues across all homelab systems
**Tools:** Prometheus, Docker, LXC, Tailscale VPN, PostgreSQL health

### 2. Analyst Agent
**Role:** Root Cause Analyst
**Goal:** Diagnose the exact cause through systematic investigation
**Tools:** Logs, metrics, performance queries, device connectivity

### 3. Healer Agent
**Role:** Self-Healing Engineer
**Goal:** Automatically remediate issues based on root cause
**Tools:** Container restart, LXC restart (least disruptive first)

### 4. Communicator Agent
**Role:** Communications Coordinator
**Goal:** Keep humans informed of incidents and resolutions
**Tools:** Telegram notifications with incident summaries

---

## 📊 Monitoring & Dashboards

### Grafana Dashboard

**URL:** http://100.120.140.105:3000/d/ai-agents-dashboard/

**9 Visualization Panels:**
- Total Incidents (stat with sparkline)
- Success Rate % (color thresholds)
- Average Resolution Time (seconds)
- Service Status (UP/DOWN)
- Resolution Time Trend (line graph)
- Incidents by Severity (pie chart)
- Total Incidents Over Time (cumulative)
- Success Rate Trend (gradient)
- Critical vs Warning Breakdown (multi-series)

**Auto-refresh:** Every 30 seconds

### Prometheus Metrics

```promql
# Service health
up{job="ai-agents"}

# Incident metrics
ai_agents_incidents_total
ai_agents_success_rate
ai_agents_avg_resolution_seconds
ai_agents_incidents_by_severity{severity="critical"}
ai_agents_incidents_by_severity{severity="warning"}
```

---

## 🧠 Continuous Learning

### Vector Memory System

- **Database:** Qdrant (http://192.168.1.99:6333)
- **Collection:** agent_memory
- **Embeddings:** OpenAI text-embedding-3-small
- **Dimensions:** 1536

### How It Works

1. Every incident is stored with full context
2. Embeddings created for semantic search
3. Analyst retrieves 3 similar past incidents
4. Historical context informs diagnosis
5. Pattern recognition improves over time

### Incident Data Stored

- Alert name and description
- Severity level
- Affected systems
- Root cause analysis
- Remediation actions taken
- Resolution status and time
- Full crew execution context

---

## 🔌 Integrated Services

### ✅ Fully Operational (13 services)

1. **Docker** - Container management (4 tools)
2. **Proxmox LXC** - LXC container management (2 tools)
3. **Proxmox VMs** - Virtual machine monitoring (6 tools)
4. **Proxmox Node** - Node health and storage (2 tools)
5. **Prometheus** - Metrics querying (1 tool)
6. **Grafana** - Visualization dashboard
7. **Qdrant** - Vector memory system
8. **Alertmanager** - Webhook receiver
9. **Telegram** - Incident notifications (1 tool)
10. **Tailscale** - VPN network monitoring (4 tools, 25+ devices)
11. **PostgreSQL** - Database monitoring (5 tools, 3+ databases)
12. **AdGuard Home** - DNS filtering (5 tools) ⭐
13. **GitHub** - Version control and collaboration

### ⚠️ Integrated But Need Credentials (2 services)

14. **UniFi Network** - WiFi/switching monitoring (6 tools) - API key needs renewal
15. **Cloudflare** - DNS/CDN/security monitoring (6 tools) - API token needs renewal

### 📋 Ready to Integrate (16 more)

See `docs/AVAILABLE_INTEGRATIONS.md` for:
- Home Assistant, Redis, N8N
- Backup systems (Kopia, Restic, B2)
- Monitoring expansions (Prometheus alerts, Grafana dashboards)
- And more...

**Progress:** 15/31 services integrated (48.4% complete)

---

## 💰 Cost Analysis

| Component | Monthly Cost | Annual Cost |
|-----------|--------------|-------------|
| GPT-4o-mini (100 incidents) | $0.36 | $4.32 |
| OpenAI Embeddings | $0.02 | $0.24 |
| Infrastructure (self-hosted) | $0.00 | $0.00 |
| **Total** | **$0.38** | **$4.56** |

**ROI:** Saves ~20 hours/month of manual incident response with expanded monitoring

---

## 📂 Project Structure

```
homelab-agents/
├── agent_server.py              # Flask webhook server (264 lines)
├── Dockerfile                   # Container image definition
├── requirements-docker.txt      # Python dependencies (17 packages)
├── .env                         # Environment configuration
│
├── crews/
│   ├── infrastructure_health/
│   │   ├── __init__.py
│   │   └── crew.py             # 4-agent crew (408 lines)
│   ├── memory/
│   │   ├── __init__.py
│   │   └── incident_memory.py  # Qdrant integration (248 lines)
│   └── tools/
│       ├── __init__.py         # Tool exports (85 lines)
│       ├── homelab_tools.py    # Core infrastructure tools (261 lines)
│       ├── tailscale_tools.py  # VPN monitoring (280 lines)
│       ├── postgres_tools.py   # Database monitoring (497 lines)
│       ├── unifi_tools.py      # WiFi/switching (564 lines) 🆕
│       ├── cloudflare_tools.py # DNS/CDN/security (684 lines) 🆕
│       ├── adguard_tools.py    # DNS filtering (519 lines) 🆕
│       └── proxmox_tools.py    # VM/node monitoring (602 lines) 🆕
│
├── tests/
│   ├── test_incident_memory.py
│   └── test_crew_memory_integration.py
│
├── docs/
│   ├── AI_INCIDENT_RESPONSE.md         # Production guide
│   ├── AVAILABLE_INTEGRATIONS.md       # 31 services analyzed
│   ├── PROJECT_COMPLETE.md             # Phases 1-6 summary
│   ├── PROJECT_SUMMARY.md              # Complete overview
│   ├── PHASE_7_COMPLETE.md             # Tailscale integration
│   ├── PHASE_8_COMPLETE.md             # PostgreSQL integration
│   ├── PHASE_14_COMPLETE.md            # UniFi network monitoring 🆕
│   ├── PHASE_15_COMPLETE.md            # Cloudflare DNS/security 🆕
│   ├── PHASE_16_COMPLETE.md            # AdGuard Home DNS 🆕
│   ├── PHASE_17_COMPLETE.md            # Expanded Proxmox 🆕
│   └── SESSION_SUMMARY_2025-10-26.md   # Session achievements 🆕
│
└── grafana-dashboard-ai-agents.json    # Dashboard definition (440 lines)
```

---

## 🧪 Testing

### Manual Testing

```bash
# Test service health
curl http://100.67.169.111:5000/health

# Check incident statistics
curl http://100.67.169.111:5000/stats

# View recent incidents
curl http://100.67.169.111:5000/incidents?limit=5

# Test Prometheus metrics
curl http://100.67.169.111:5000/metrics
```

### Simulating Incidents

```bash
# Trigger a test alert via Alertmanager
curl -X POST http://100.67.169.111:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestServiceDown",
      "severity": "critical"
    },
    "annotations": {
      "description": "Test service has been down for testing"
    }
  }]'
```

---

## 📈 Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| **1-2** | Core 4-agent system + tools | ✅ Complete |
| **3** | Continuous learning with Qdrant | ✅ Complete |
| **4** | Production deployment | ✅ Complete |
| **5** | Monitoring endpoints | ✅ Complete |
| **6** | Grafana dashboard | ✅ Complete |
| **7** | Tailscale network monitoring (4 tools) | ✅ Complete |
| **8** | PostgreSQL database monitoring (5 tools) | ✅ Complete |
| **9** | Project documentation | ✅ Complete |
| **10** | Git integration | ✅ Complete |
| **11-13** | Infrastructure improvements | ✅ Complete |
| **14** | UniFi network monitoring (6 tools) | ⚠️ Needs credentials |
| **15** | Cloudflare DNS/security (6 tools) | ⚠️ Needs credentials |
| **16** | AdGuard Home DNS filtering (5 tools) | ✅ Complete |
| **17** | Expanded Proxmox monitoring (6 tools) | ✅ Complete |
| **18** | Home Assistant smart home (6 tools) | ⚠️ Needs activation |
| **19** | Prometheus monitoring expansion (6 tools) | ✅ Complete |
| **20** | Docker management expansion (6 tools) | ✅ Complete |
| **21** | Alertmanager alert management (6 tools) | ✅ Complete |
| **22** | Grafana API integration (6 tools) | ✅ Complete |
| **23** | PostgreSQL monitoring expansion (6 tools) | ✅ Complete |
| **24** | LXC container management expansion (6 tools) | ✅ Complete |
| **25** | Healer Expansion Part 1 - Remediation (6 tools) | ✅ Complete |

**Total Development Time:** ~24 hours
**Lines of Code:** ~16,500+
**Documentation:** ~17,000+ lines
**Service Coverage:** 51.6% (16/31 services)

---

## 🔧 Operational Procedures

### Daily Operations

```bash
# Check Grafana dashboard
http://100.120.140.105:3000/d/ai-agents-dashboard/

# Verify service status
curl http://100.67.169.111:5000/health

# Review recent incidents
curl http://100.67.169.111:5000/incidents?limit=10
```

### Troubleshooting

```bash
# Check container status
ssh root@100.67.169.111 "docker ps | grep homelab-agents"

# View logs
ssh root@100.67.169.111 "docker logs homelab-agents -f"

# Restart if needed
ssh root@100.67.169.111 "docker restart homelab-agents"

# Check Qdrant connection
curl -s http://192.168.1.99:6333/collections/agent_memory
```

---

## 📚 Documentation

- **[AI Incident Response Guide](docs/AI_INCIDENT_RESPONSE.md)** - Complete production deployment guide
- **[Available Integrations](docs/AVAILABLE_INTEGRATIONS.md)** - Research on 31 services
- **[Project Summary](docs/PROJECT_SUMMARY.md)** - Comprehensive overview
- **[Phase 7: Tailscale](docs/PHASE_7_COMPLETE.md)** - Network monitoring integration
- **[Phase 8: PostgreSQL](docs/PHASE_8_COMPLETE.md)** - Database monitoring integration

---

## 🎯 Use Cases

### Scenario 1: Container Failure
```
Alert: Docker container stopped unexpectedly

Monitor: Detects container down, checks status
Analyst: Reviews logs, identifies OOM error
Healer: Restarts container
Communicator: Notifies via Telegram
Memory: Stores for future OOM prevention

Resolution: ~45 seconds
```

### Scenario 2: Network Connectivity
```
Alert: Service unreachable

Monitor: Checks Tailscale VPN health
Analyst: Identifies device offline, checks connectivity
Healer: Cannot fix VPN (escalates)
Communicator: Notifies with device details
Memory: Stores network pattern

Resolution: Escalated with diagnostic info
```

### Scenario 3: Database Performance
```
Alert: Application slow response

Monitor: Checks PostgreSQL connection pool (90% usage)
Analyst: Finds long-running queries, connection leak
Healer: Cannot fix app-level issue (escalates)
Communicator: Notifies with query details
Memory: Stores performance pattern

Resolution: Escalated with root cause identified
```

---

## 🤝 Contributing

This is a personal homelab project, but suggestions and improvements are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- Built with [Claude Code](https://claude.com/claude-code)
- Powered by [CrewAI](https://www.crewai.com/)
- Uses [Qdrant](https://qdrant.tech/) for vector memory
- LLM: OpenAI GPT-4o-mini

---

## 📞 Support

- **GitHub Issues:** [munkyHeadz/homelab-agents](https://github.com/munkyHeadz/homelab-agents/issues)
- **Documentation:** See `docs/` directory
- **Health Check:** http://100.67.169.111:5000/health

---

**Status:** ✅ Production Operational
**Version:** 1.8.0
**Last Updated:** 2025-10-27
**Success Rate:** 100% (8/8 incidents)
**Average Resolution:** 137 seconds
**Service Coverage:** 51.6% (16/31 services)
**Tools Available:** 87 autonomous tools (+6 remediation tools)
**Monthly Cost:** $0.38
