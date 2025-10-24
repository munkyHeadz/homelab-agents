# Homelab Autonomous Agent System

An autonomous agent system for managing homelab infrastructure using Claude AI and Model Context Protocol (MCP).

## Overview

This system provides intelligent, autonomous management of homelab infrastructure through:
- **Telegram Bot Interface** - Control your homelab from your phone
- **Autonomous Health Agent** - Self-monitoring, self-healing, and self-improving system (v2.5)
- **Scheduled Reporting** - Daily/weekly/monthly health reports (v2.6)
- **Backup Verification** - Automated backup integrity checking (v2.7)
- **Service Monitoring** - Multi-service health checks (v2.7)
- **Predictive Analysis** - Forecasting and capacity planning (v2.7)
- **Web Dashboard** - Real-time monitoring interface (v2.7)
- **Infrastructure Agent** - Manage Proxmox VMs, LXC containers, and Docker
- **Monitoring Agent** - Network monitoring, alerts, and incident response
- **MCP Integration** - Modular tool access via Model Context Protocol

## Features

### 🤖 Telegram Bot v2.7
- Complete system status monitoring
- VM and container management (start/stop/restart)
- Docker container control (restart/stop)
- Resource monitoring with 35+ commands
- Natural language interface
- Interactive button menus
- Automatic updates (`/update` command)
- Backup verification and integrity checks
- Service health monitoring (Plex, Sonarr, Radarr, etc.)
- Predictive analysis and trend forecasting
- Health monitoring and automated reports

### 🏥 Autonomous Self-Healing (v2.5)
- Continuous health monitoring (every 60 seconds)
- Automatic diagnosis using Claude AI
- Risk-based auto-healing (LOW risk actions executed automatically)
- Telegram approval workflow for risky actions
- Real-time notifications and reporting
- Learning from successful fixes
- See [AUTONOMOUS_FEATURES.md](docs/AUTONOMOUS_FEATURES.md) for details

### 📊 Scheduled Reporting (v2.6)
- Daily health summaries (8 AM)
- Weekly trend analysis (Mondays)
- Monthly summary reports (1st of month)
- Prometheus alert integration
- Customizable report schedules

### 💾 Backup Verification (v2.7 - NEW)
- Automated backup integrity checks
- Three verification levels (Basic, Checksum, Restore Test)
- Critical VM monitoring
- Success rate tracking
- Automatic alerts for failed/missing backups
- See [PHASE3_FEATURES.md](docs/PHASE3_FEATURES.md) for details

### 🔧 Service Health Monitoring (v2.7 - NEW)
- Multi-service support (Plex, Sonarr, Radarr, Jellyfin, Pi-hole, etc.)
- HTTP endpoint health checks
- API availability testing
- Service-specific metrics (streams, downloads, queries)
- Real-time alerts on service degradation

### 🔮 Predictive Analysis (v2.7 - NEW)
- Resource usage forecasting
- Disk full predictions
- Memory exhaustion warnings
- Service failure predictions
- Trend analysis and anomaly detection
- Historical data tracking (7-day default)

### 🌐 Web Dashboard (v2.7 - NEW)
- Real-time monitoring interface
- Visual status indicators
- Service health dashboard
- Predictive analysis charts
- Mobile-responsive design
- Auto-refresh (30 seconds)
- Access at `http://YOUR_LXC_IP:5000`

### 🤖 Advanced Automation (v2.7 - NEW)
- SSL certificate monitoring & auto-renewal
- Scheduled system updates
- Automated log cleanup
- Database maintenance (VACUUM/ANALYZE)
- Docker image update checks

### 🏗️ Infrastructure Management
- Proxmox VE integration (VMs and LXC)
- Docker container orchestration
- Resource monitoring and optimization
- Automated scaling decisions

### 📊 Monitoring & Alerts
- Prometheus metrics collection
- Grafana dashboards
- Network health monitoring (Unifi, Tailscale, Cloudflare)
- DNS management (Pi-hole, Cloudflare)
- Automated incident response

### 🔧 MCP Servers
- **Proxmox MCP** - VM/LXC management
- **Docker MCP** - Container management
- **Unifi MCP** - Network device management
- **Tailscale MCP** - VPN network status
- **Cloudflare MCP** - DNS/CDN/WAF management
- **Pi-hole MCP** - DNS ad-blocking
- **Mem0 MCP** - Agent memory and learning

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Telegram Bot (LXC 104)                │
│              telegram_bot.py - User Interface            │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼─────────┐
│ Infrastructure   │    │  Monitoring      │
│     Agent        │    │     Agent        │
│  (Proxmox/Docker)│    │  (Network/Alerts)│
└────────┬─────────┘    └────────┬─────────┘
         │                       │
    ┌────┴───────────────────────┴────┐
    │         MCP Servers              │
    ├──────────────────────────────────┤
    │ Proxmox | Docker | Unifi         │
    │ Tailscale | Cloudflare | Pi-hole │
    │ Mem0 (Memory & Learning)         │
    └──────────────────────────────────┘
         │
    ┌────┴────────────────────┐
    │  Infrastructure         │
    ├─────────────────────────┤
    │ Proxmox VE (192.168.1.99)│
    │ Docker (192.168.1.101)   │
    │ Monitoring (192.168.1.107)│
    │ PostgreSQL (192.168.1.200)│
    └──────────────────────────┘
```

## Installation

### Prerequisites
- Proxmox VE server
- Python 3.10+
- Anthropic API key
- Telegram Bot token
- PostgreSQL database

### Quick Start

1. **Clone repository**
   ```bash
   git clone https://github.com/munkyHeadz/homelab-agents.git
   cd homelab-agents
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Deploy to LXC**
   ```bash
   ./scripts/deploy_to_lxc.sh
   ```

5. **Start Telegram bot**
   ```bash
   systemctl start homelab-telegram-bot
   ```

## Configuration

### Environment Variables

Create `.env` file with:

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Proxmox
PROXMOX_HOST=192.168.1.99
PROXMOX_TOKEN_ID=root@pam!homelab
PROXMOX_TOKEN_SECRET=your-secret

# Docker
DOCKER_HOST=tcp://192.168.1.101:2375

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ADMIN_IDS=500505500

# PostgreSQL
POSTGRES_HOST=192.168.1.200
POSTGRES_USER=homelab
POSTGRES_PASSWORD=your-password
POSTGRES_DB=homelab_agents
```

### Claude Code Web Settings

The repository includes `.claude/settings.json` for Claude Code on the web:
- Automatic venv setup on session start
- Environment variable templates
- Default shell configuration

## Usage

### Telegram Commands

```bash
# System Status
/status     - Complete system overview
/uptime     - System and bot uptime
/monitor    - Resource monitoring
/menu       - Interactive control menu

# Proxmox Management
/node       - Node status
/vms        - List VMs and containers
/start_vm   - Start VM/Container
/stop_vm    - Stop VM/Container
/restart_vm - Restart VM/Container

# Docker Management
/docker     - Docker system info
/containers - List all containers
/restart_container - Restart Docker container
/stop_container    - Stop Docker container

# Health & Auto-Healing
/health              - System health report
/enable_autohealing  - Enable autonomous monitoring
/disable_autohealing - Disable autonomous monitoring

# Backup Status
/backup     - Show backup status
/backup <id> - Status for specific VM

# Bot Management
/update     - Auto-update and restart
/help       - Command reference
```

### Natural Language

Just send messages like:
- "Show status of LXC 101"
- "List running Docker containers"
- "Check system resources"

## Monitoring

### Prometheus Metrics
- **Endpoint**: http://192.168.1.104:8000/metrics
- **Agent health**: `agent_health_status`
- **Task metrics**: `agent_tasks_total`, `agent_task_duration_seconds`
- **MCP metrics**: `mcp_connections_active`, `mcp_requests_total`

### Grafana Dashboards
- **URL**: http://192.168.1.107:3000
- **Dashboard**: Homelab Infrastructure Overview

### Alert Rules
17 alert rules across 5 groups:
- Infrastructure alerts (CPU, memory, disk)
- Agent health monitoring
- MCP connection status
- Container health
- Network connectivity

## Testing

### Run Integration Tests
```bash
python tests/integration_test.py
```

### Test Telegram Bot
```bash
python tests/telegram_bot_test.py
```

### Test Individual Agents
```bash
python tests/quick_agent_test.py
```

## Development

### Project Structure
```
homelab-agents/
├── agents/                    # Autonomous agents
│   ├── infrastructure_agent.py
│   └── monitoring_agent.py
├── interfaces/                # User interfaces
│   └── telegram_bot.py
├── mcp_servers/              # MCP server implementations
│   ├── proxmox_mcp/
│   ├── docker_mcp/
│   ├── unifi_mcp/
│   └── ...
├── shared/                   # Shared utilities
│   ├── config.py
│   ├── logging.py
│   ├── llm_router.py
│   └── metrics.py
├── scripts/                  # Deployment scripts
├── tests/                    # Test suite
└── monitoring/              # Monitoring configs
    ├── alert_rules.yml
    └── homelab-dashboard.json
```

### Adding New MCP Servers

1. Create server directory in `mcp_servers/`
2. Implement server using MCP SDK
3. Register tools and resources
4. Update agent to connect to new server
5. Add tests

## Deployment

### LXC Container Layout
- **LXC 100** - Arr stack (Sonarr, Radarr, etc.)
- **LXC 101** - Docker host
- **LXC 104** - Homelab agents + Telegram bot
- **LXC 107** - Monitoring (Prometheus, Grafana)
- **LXC 200** - PostgreSQL database

### Services
```bash
# Telegram bot
systemctl status homelab-telegram-bot

# Monitoring stack
systemctl status prometheus
systemctl status grafana-server
systemctl status node_exporter
```

## Metrics

### Test Results
- **Integration Tests**: 96.9% pass rate (31/32)
- **Telegram Bot Tests**: 94.6% pass rate (35/37)
- **Bot Response Time**: 2-8 seconds
- **Memory Usage**: ~89 MB

## Documentation

### Getting Started
- **[README](README.md)** - This file - Project overview and features
- **[Complete Feature Summary](docs/COMPLETE_FEATURE_SUMMARY.md)** - v2.5 & v2.6 features (40+ pages)
- **[Phase 3 Features](docs/PHASE3_FEATURES.md)** - ⭐ **NEW v2.7** - Advanced monitoring & automation
- [Deployment Instructions](docs/DEPLOYMENT_INSTRUCTIONS.md) - Step-by-step deployment

### Feature Guides (By Version)
- **v2.7 (Phase 3):**
  - [Phase 3 Features](docs/PHASE3_FEATURES.md) - Backup verification, service monitoring, predictions, web dashboard
- **v2.6:**
  - [Prometheus Integration](docs/PROMETHEUS_INTEGRATION.md) - Alert forwarding and webhook setup
  - [Scheduled Reporting](docs/COMPLETE_FEATURE_SUMMARY.md#scheduled-reporting) - Daily/weekly/monthly reports
- **v2.5:**
  - [Autonomous Features](docs/AUTONOMOUS_FEATURES.md) - Self-healing system guide (750+ lines)
- **Core:**
  - [Bot Improvements](docs/BOT_IMPROVEMENTS.md) - Telegram bot features
  - [Telegram Testing](docs/TELEGRAM_BOT_TESTING.md) - Manual testing procedures

### Technical References
- [Test Report](docs/TEST_REPORT.md) - Integration test results
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md) - Feature tracking
- [MCP Servers](docs/MCP_SERVERS_STATUS.md) - MCP server documentation
- [Git Troubleshooting](docs/FIX_GIT_OWNERSHIP.md) - Fix git ownership issues

## Troubleshooting

### Bot Not Responding
```bash
# Check service
sudo pct exec 104 -- systemctl status homelab-telegram-bot

# View logs
sudo pct exec 104 -- journalctl -u homelab-telegram-bot -f

# Restart
sudo pct exec 104 -- systemctl restart homelab-telegram-bot
```

### Agent Errors
```bash
# Check agent health
curl http://192.168.1.104:8000/metrics | grep agent_health

# Test agents directly
python tests/quick_agent_test.py
```

### MCP Connection Issues
```bash
# Verify MCP servers accessible
curl https://192.168.1.99:8006  # Proxmox
curl http://192.168.1.101:2375  # Docker
```

## Contributing

This is a personal homelab project, but suggestions and improvements are welcome!

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/claude)
- Uses [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Inspired by the autonomous agent pattern

---

**Status**: ✅ Production
**Version**: 2.6 (Scheduled Reports & Prometheus Integration)
**Last Updated**: 2025-10-24

**New in v2.6:**
- 📊 Scheduled health reports (daily/weekly/monthly)
- 🔔 Prometheus alert integration with auto-remediation
- 📈 Trend analysis and reporting

**v2.5 Features:**
- 🏥 Autonomous health monitoring and self-healing
- 🎮 Interactive Telegram button menus
- 🔧 VM/Container control commands
- 💾 Backup status checking
- ⚠️ Smart approval workflow for risky actions
