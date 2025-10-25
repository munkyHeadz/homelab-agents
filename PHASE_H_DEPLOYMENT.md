# Phase H Deployment Guide: Observability & Metrics

## ✅ Status: CODE COMPLETE - READY FOR DEPLOYMENT

All code for Phase H (Observability) is **already integrated** into the telegram bot!

**What's already done:**
- ✅ Prometheus client for metrics queries implemented
- ✅ Observability manager with dashboard display implemented
- ✅ `/metrics`, `/prometheus`, `/grafana`, `/promql` commands added to bot
- ✅ Commands registered in application
- ✅ Observability manager initializes automatically with bot
- ✅ Integration with Prometheus and Grafana

---

## 🎯 What Phase H Does

Phase H adds comprehensive observability and monitoring capabilities:

### Features
1. **Real-time System Metrics**
   - CPU usage across all nodes
   - Memory usage with visual indicators
   - Disk usage tracking
   - Color-coded status (🟢 <70%, 🟡 70-85%, 🔴 >85%)

2. **Prometheus Integration**
   - Query Prometheus metrics
   - View active alerts (firing/pending)
   - Check scrape targets status
   - Execute custom PromQL queries

3. **Grafana Dashboards**
   - Quick links to common dashboards
   - Node Exporter metrics
   - Prometheus stats
   - Alertmanager overview

4. **Custom Queries**
   - Execute any PromQL query
   - Formatted results for Telegram
   - Support for instant and range queries

---

## 🚀 Quick Deployment Steps

### Step 1: Verify Prometheus & Grafana Config (5 min)

**Check .env file:**
```bash
cd /home/munky/homelab-agents
grep -A 10 "PROMETHEUS" .env
```

**Should show:**
```bash
PROMETHEUS_HOST=192.168.1.104
PROMETHEUS_PORT=9090
PROMETHEUS_URL=http://192.168.1.104:9090

GRAFANA_HOST=192.168.1.105
GRAFANA_PORT=3000
GRAFANA_URL=http://192.168.1.105:3000
```

**Verify Prometheus is accessible:**
```bash
curl http://192.168.1.104:9090/-/healthy
# Should return: Prometheus is Healthy.
```

**Verify Grafana is accessible:**
```bash
curl -I http://192.168.1.105:3000
# Should return: HTTP 200 or 302
```

---

### Step 2: Restart Telegram Bot (5 min)

The bot will automatically initialize the Prometheus client and observability manager.

**In LXC 104:**
```bash
sudo pct exec 104 -- systemctl restart homelab-telegram-bot
```

**Check status:**
```bash
sudo pct exec 104 -- systemctl status homelab-telegram-bot --no-pager
```

**Verify logs:**
```bash
sudo pct exec 104 -- journalctl -u homelab-telegram-bot -n 50 --no-pager | grep -i "observability"
# Should see: "Observability manager initialized"
```

---

### Step 3: Test Observability Commands (10 min)

**Test 1: View system metrics**
```
You: /metrics
Bot: 📊 **System Metrics Dashboard**
     [Shows CPU, Memory, Disk usage with color indicators]
```

**Test 2: Check Prometheus alerts**
```
You: /prometheus
Bot: 🚨 **Prometheus Alerts**
     [Shows firing and pending alerts]
```

**Test 3: Get Grafana links**
```
You: /grafana
Bot: 📊 **Grafana Dashboards**
     [Shows dashboard links]
```

**Test 4: Execute custom query**
```
You: /promql up
Bot: [Shows all scrape targets and their status]
```

---

## 🎮 Available Commands

### Phase H: Observability

| Command | Description | Example |
|---------|-------------|---------|
| `/metrics` | Show real-time system metrics | `/metrics` |
| `/prometheus` | View Prometheus alerts | `/prometheus` |
| `/grafana` | Get Grafana dashboard links | `/grafana` |
| `/promql <query>` | Execute Prometheus query | `/promql node_cpu_seconds_total` |

---

## 📊 What `/metrics` Shows

The metrics dashboard displays:

### CPU Usage
```
💻 CPU Usage:
🟢 192.168.1.99:9100: 15.2%
🟡 192.168.1.104:9100: 72.8%
🔴 192.168.1.107:9100: 92.3%
```

### Memory Usage
```
🧠 Memory Usage:
🟢 192.168.1.99:9100: 45.6%
🟡 192.168.1.104:9100: 81.2%
```

### Disk Usage
```
💾 Disk Usage:
🟢 192.168.1.99:9100: 58.3%
🟡 192.168.1.107:9100: 87.9%
```

### Prometheus Targets
```
🎯 Prometheus Targets:
  • Active: 12
  • Dropped: 0
```

### Alert Summary
```
🚨 Prometheus Alerts:
  • 🔴 Firing: 2
  • 🟡 Pending: 1
  • Total: 3
```

### Dashboard Links
```
🔗 Dashboards:
  • Prometheus
  • Grafana
```

---

## 🔍 Troubleshooting

### Prometheus Connection Fails

**Check Prometheus is running:**
```bash
curl http://192.168.1.104:9090/api/v1/targets
```

**Check from bot container:**
```bash
sudo pct exec 104 -- curl -s http://192.168.1.104:9090/-/healthy
```

**Verify .env configuration:**
```bash
sudo pct exec 104 -- grep PROMETHEUS /root/homelab-agents/.env
```

### Commands Show "Prometheus not configured"

**Check logs for initialization:**
```bash
sudo pct exec 104 -- journalctl -u homelab-telegram-bot -n 100 | grep -i prometheus
# Should see: "Prometheus client initialized successfully"
```

**Test Prometheus client directly:**
```bash
sudo pct exec 104 -- bash -c "cd /root/homelab-agents && python3 -c '
from integrations.prometheus_client import get_prometheus_client
import asyncio

async def test():
    client = get_prometheus_client()
    if client:
        health = await client.health_check()
        print(health)
    else:
        print(\"Client not available\")

asyncio.run(test())
'"
```

### Metrics Show No Data

**Verify node_exporter is running:**
```bash
# Check if node_exporter is running on each node
curl http://192.168.1.99:9100/metrics | head
curl http://192.168.1.104:9100/metrics | head
```

**Check Prometheus targets:**
```bash
curl http://192.168.1.104:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health}'
```

### Grafana Links Don't Work

**Update GRAFANA_URL in .env:**
```bash
# If Grafana is on a different host/port
GRAFANA_URL=http://your-grafana-host:3000
```

---

## 📈 Integration Points

### Metrics Query Flow
```
User: /metrics
    ↓
TelegramBot.metrics_command()
    ↓
ObservabilityManager.get_metrics_dashboard()
    ↓
  ├─ PrometheusClient.get_current_metrics()
  │    ├─ Query CPU: '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
  │    ├─ Query Memory: '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
  │    └─ Query Disk: '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100'
  ├─ PrometheusClient.get_targets()
  └─ PrometheusClient.get_alerts()
    ↓
Formatted markdown dashboard
    ↓
📱 Message sent to user
```

### Prometheus Client Architecture
```
ObservabilityManager
    ↓
PrometheusClient (uses aiohttp)
    ↓
Prometheus REST API (http://192.168.1.104:9090)
    ↓
  ├─ /api/v1/query (instant queries)
  ├─ /api/v1/query_range (range queries)
  ├─ /api/v1/targets (scrape targets)
  ├─ /api/v1/alerts (alert status)
  └─ /-/healthy (health check)
```

---

## 🎯 Success Criteria

After deployment, verify:

- [ ] Bot restarts without errors
- [ ] Bot logs show "Observability manager initialized"
- [ ] Bot logs show "Prometheus client initialized successfully"
- [ ] `/metrics` displays system metrics
- [ ] `/prometheus` shows alert status
- [ ] `/grafana` displays dashboard links
- [ ] `/promql up` executes and shows targets
- [ ] Color indicators work (🟢🟡🔴)
- [ ] Links to Prometheus/Grafana are clickable
- [ ] No errors in bot logs related to observability

---

## 🔧 Customization

### Changing Prometheus URL

Edit `/root/homelab-agents/.env` in container:
```bash
PROMETHEUS_URL=http://your-prometheus-host:9090
```

### Adding Custom Dashboards

Edit `/home/munky/homelab-agents/shared/observability_manager.py` line 236:

```python
dashboards = [
    {"name": "Home", "path": "/"},
    {"name": "Your Dashboard", "path": "/d/dashboard-id/dashboard-name"},
    # Add more dashboards here
]
```

### Adjusting Metric Thresholds

Edit color indicator thresholds in `observability_manager.py`:

```python
# CPU (line 96)
emoji = "🟢" if usage < 70 else "🟡" if usage < 85 else "🔴"

# Memory (line 107)
emoji = "🟢" if usage < 80 else "🟡" if usage < 90 else "🔴"

# Disk (line 118)
emoji = "🟢" if usage < 80 else "🟡" if usage < 90 else "🔴"
```

---

## 📂 Files Modified/Created

### New Files
- `integrations/prometheus_client.py` - Prometheus API client (390 lines)
- `shared/observability_manager.py` - High-level observability manager (330 lines)
- `PHASE_H_DEPLOYMENT.md` - This deployment guide

### Modified Files
- `interfaces/telegram_bot.py`
  - Added 4 observability commands (lines 1105-1179)
  - Registered commands (lines 1697-1701)
  - Updated `/start` and `/help` documentation
  - Added observability_manager initialization (line 89)

---

## 📅 Example PromQL Queries

Useful queries to try with `/promql`:

### System Metrics
```
# Show all scrape targets
/promql up

# CPU usage per instance
/promql 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage per instance
/promql (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage
/promql (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100
```

### Network Metrics
```
# Network receive rate (bytes/sec)
/promql rate(node_network_receive_bytes_total[5m])

# Network transmit rate
/promql rate(node_network_transmit_bytes_total[5m])
```

### Process Metrics
```
# Process count
/promql node_processes_running

# Load average
/promql node_load1
/promql node_load5
/promql node_load15
```

---

## 🆘 Support

- **Bot logs:** `sudo pct exec 104 -- journalctl -u homelab-telegram-bot -f`
- **Test Prometheus:** `curl http://192.168.1.104:9090/-/healthy`
- **Test commands:** `/metrics`, `/prometheus`, `/grafana`
- **Prometheus UI:** http://192.168.1.104:9090
- **Grafana UI:** http://192.168.1.105:3000

---

## 🏗️ Architecture

### Components

1. **PrometheusClient** (`integrations/prometheus_client.py`)
   - Async HTTP client using aiohttp
   - Query instant and range metrics
   - Get targets and alerts
   - Health checks
   - Singleton pattern for connection pooling

2. **ObservabilityManager** (`shared/observability_manager.py`)
   - High-level monitoring interface
   - Formatted dashboard generation
   - Alert summarization
   - Grafana link management
   - PromQL query execution

3. **Telegram Bot Integration** (`interfaces/telegram_bot.py`)
   - `/metrics` - Real-time metrics dashboard
   - `/prometheus` - Alert status
   - `/grafana` - Dashboard links
   - `/promql` - Custom query interface

### Data Flow

```
┌─────────────────────┐
│  Telegram User      │
│  /metrics command   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ObservabilityMgr    │
│ get_metrics_dashboard│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PrometheusClient   │
│  (aiohttp)          │
└──────────┬──────────┘
           │
     ┌─────┴──────────┐
     ▼                ▼
┌──────────┐    ┌──────────┐
│Prometheus│    │ Grafana  │
│   API    │    │   Links  │
└──────────┘    └──────────┘
     │                │
     └─────┬──────────┘
           ▼
┌─────────────────────┐
│  Format Dashboard   │
│  + Color Indicators │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  📱 Telegram        │
│  Markdown Display   │
└─────────────────────┘
```

### Prometheus Queries Used

**CPU Usage:**
```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

**Memory Usage:**
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

**Disk Usage:**
```promql
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
```

---

**Deployment Time Estimate:** 15-20 minutes total
**Difficulty:** Easy (Prometheus/Grafana already configured)
**Status:** ✅ Ready to Deploy
**Requirements:** Prometheus at 192.168.1.104:9090, Grafana at 192.168.1.105:3000

---

## 💡 Tips

1. **Bookmark Prometheus/Grafana** - Keep URLs handy for quick access
2. **Learn PromQL** - Powerful query language for custom metrics
3. **Set up alerts** - Configure Alertmanager for critical thresholds
4. **Create dashboards** - Build custom Grafana dashboards for your needs
5. **Monitor regularly** - Use `/metrics` daily to spot trends

---

## 🎓 Learning Resources

- **PromQL Documentation:** https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Grafana Documentation:** https://grafana.com/docs/
- **Node Exporter Metrics:** https://github.com/prometheus/node_exporter
- **Query Examples:** `/promql` command help

---

## ✨ What's Next?

All major phases are now complete! 🎉

**Completed Phases:**
- ✅ Phase A: Alert Integration
- ✅ Phase B: VM Control
- ✅ Phase C: Backup Management
- ✅ Phase D: Scheduled Reports
- ✅ Phase E & F: Network Monitoring
- ✅ Phase G: Automated Remediation
- ✅ Phase H: Observability

**Future Enhancements:**
- Custom alert rules
- Performance optimization
- Additional integrations
- Enhanced reporting
