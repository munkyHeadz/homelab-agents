# Alert Rules Deployment Guide

## 📋 Overview

This guide explains how to deploy the Tailscale and PostgreSQL alert rules to your Prometheus/Alertmanager setup.

**Alert Rules File:** `/home/munky/homelab-agents/prometheus-alerts/tailscale-postgresql-alerts.yml`
**Rules Created:** 18 rules across 3 categories
**Status:** Ready for deployment

---

## 🎯 Alert Rules Summary

### Tailscale Network Alerts (5 rules)
- `TailscaleCriticalDeviceOffline` - Critical infrastructure offline >5m
- `TailscaleDeviceOfflineExtended` - Any device offline >24h
- `TailscaleHighOfflineRate` - >40% devices offline
- `TailscaleUpdatesAvailable` - Client updates pending >7d
- `TailscaleKeyExpirySoon` - Auth key expiring <7d

### PostgreSQL Database Alerts (10 rules)
- `PostgreSQLDown` - Database not responding
- `PostgreSQLConnectionPoolHigh` - Pool usage >75%
- `PostgreSQLConnectionPoolCritical` - Pool usage >90%
- `PostgreSQLTooManyIdleConnections` - >50 idle connections
- `PostgreSQLLongRunningQuery` - Query running >5 minutes
- `PostgreSQLBlockingQuery` - Queries blocked by locks
- `PostgreSQLLowCacheHitRatio` - Cache hit ratio <90%
- `PostgreSQLDatabaseSizeGrowth` - Growth >1GB/hour
- `PostgreSQLDeadTuplesHigh` - Dead tuples >20%
- `PostgreSQLReplicationLag` - Replication lag >60s

### AI Agents System Alerts (3 rules)
- `AIAgentsServiceDown` - Webhook service unavailable
- `AIAgentsMemoryStorageError` - Qdrant connection failed
- `AIAgentsSlowResolution` - Incident resolution >5 minutes

---

## 📍 Prometheus/Alertmanager Configuration

Based on `.env` file:
```
Prometheus: 192.168.1.104:9090
Alertmanager: 192.168.1.106:9093
AI Agents Webhook: 100.67.169.111:5000/alert
```

---

## 🚀 Deployment Steps

### Step 1: Verify Prometheus is Running

```bash
# Check Prometheus is accessible
curl http://192.168.1.104:9090/api/v1/status/config

# Check current rules
curl http://192.168.1.104:9090/api/v1/rules
```

### Step 2: Deploy Alert Rules

**Option A: Copy to Prometheus Server**

If Prometheus server is accessible via SSH:

```bash
# Copy rules file to Prometheus server
scp /home/munky/homelab-agents/prometheus-alerts/tailscale-postgresql-alerts.yml \
    root@192.168.1.104:/etc/prometheus/rules/

# Verify file copied
ssh root@192.168.1.104 "ls -lh /etc/prometheus/rules/"
```

**Option B: Manual Copy**

If SSH not available, manually copy the file:
1. Open `/home/munky/homelab-agents/prometheus-alerts/tailscale-postgresql-alerts.yml`
2. Copy contents
3. On Prometheus server, create file at `/etc/prometheus/rules/tailscale-postgresql-alerts.yml`
4. Paste contents

### Step 3: Update Prometheus Configuration

Edit Prometheus config (usually `/etc/prometheus/prometheus.yml` or `/etc/prometheus/prometheus.yml`):

```yaml
# Add to prometheus.yml
rule_files:
  - "/etc/prometheus/rules/*.yml"
  # Or specifically:
  - "/etc/prometheus/rules/tailscale-postgresql-alerts.yml"
```

### Step 4: Validate Configuration

```bash
# Validate Prometheus configuration
promtool check config /etc/prometheus/prometheus.yml

# Validate alert rules
promtool check rules /etc/prometheus/rules/tailscale-postgresql-alerts.yml
```

### Step 5: Reload Prometheus

**Option A: API Reload (Preferred)**

```bash
# Reload via API (requires --web.enable-lifecycle flag)
curl -X POST http://192.168.1.104:9090/-/reload
```

**Option B: Service Restart**

```bash
# Restart Prometheus service
sudo systemctl restart prometheus

# OR if running in Docker:
docker restart prometheus
```

### Step 6: Verify Rules Loaded

```bash
# Check rules are loaded
curl -s http://192.168.1.104:9090/api/v1/rules | jq '.data.groups[].name'

# Expected output should include:
# - "tailscale_network"
# - "postgresql_database"
# - "ai_agents_integration_health"

# Check specific rule group
curl -s http://192.168.1.104:9090/api/v1/rules | \
    jq '.data.groups[] | select(.name == "tailscale_network")'
```

---

## 🔧 Alertmanager Configuration

### Configure Routing

Edit Alertmanager config (usually `/etc/alertmanager/alertmanager.yml`):

```yaml
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

  routes:
    # Route all Tailscale alerts to AI agents
    - match:
        integration: tailscale
      receiver: homelab-ai-agents
      continue: true

    # Route all PostgreSQL alerts to AI agents
    - match:
        integration: postgresql
      receiver: homelab-ai-agents
      continue: true

    # Route critical alerts to AI agents
    - match:
        severity: critical
      receiver: homelab-ai-agents
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 4h

    # Route AI agents system alerts
    - match:
        integration: ai-agents
      receiver: homelab-ai-agents

receivers:
  - name: 'default'
    # Your default receiver config

  - name: 'homelab-ai-agents'
    webhook_configs:
      - url: 'http://100.67.169.111:5000/alert'
        send_resolved: true
        http_config:
          follow_redirects: true
        max_alerts: 0  # No limit
```

### Reload Alertmanager

```bash
# Validate configuration
amtool check-config /etc/alertmanager/alertmanager.yml

# Reload via API
curl -X POST http://192.168.1.106:9093/-/reload

# OR restart service
sudo systemctl restart alertmanager
# OR
docker restart alertmanager
```

---

## ✅ Verification & Testing

### 1. Check Rules Status

```bash
# View all loaded rules
curl -s http://192.168.1.104:9090/api/v1/rules | jq '.data.groups[]' | head -50

# Check specific rule is active
curl -s http://192.168.1.104:9090/api/v1/rules | \
    jq '.data.groups[].rules[] | select(.name == "TailscaleCriticalDeviceOffline")'
```

### 2. Check Alert States

```bash
# View currently firing alerts
curl -s http://192.168.1.104:9090/api/v1/alerts | jq '.data.alerts[]'

# Check Alertmanager alerts
curl -s http://192.168.1.106:9093/api/v2/alerts | jq '.'
```

### 3. Test Alert Firing

Create a test alert to verify the webhook works:

```bash
# Send test alert to AI agents
curl -X POST http://100.67.169.111:5000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "receiver": "homelab-ai-agents",
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "TestAlert",
        "severity": "warning"
      },
      "annotations": {
        "summary": "Test alert for verification"
      }
    }]
  }'
```

### 4. Monitor AI Agents Processing

```bash
# Watch AI agents logs
ssh root@100.67.169.111 "docker logs -f homelab-agents"

# Check incidents processed
curl -s http://100.67.169.111:5000/incidents?limit=5 | jq '.'

# Check stats
curl -s http://100.67.169.111:5000/stats | jq '.'
```

---

## 🐛 Troubleshooting

### Rules Not Loading

**Problem:** Rules don't appear in Prometheus

**Solution:**
```bash
# Check Prometheus logs
sudo journalctl -u prometheus -n 50

# OR for Docker
docker logs prometheus --tail 50

# Validate rules syntax
promtool check rules /etc/prometheus/rules/tailscale-postgresql-alerts.yml
```

### Alerts Not Firing

**Problem:** Metrics exist but alerts don't fire

**Checks:**
1. Verify metrics exist:
   ```bash
   # Check Tailscale metrics
   curl -s 'http://192.168.1.104:9090/api/v1/query?query=tailscale_device_online'

   # Check PostgreSQL metrics
   curl -s 'http://192.168.1.104:9090/api/v1/query?query=pg_up'
   ```

2. Check rule evaluation:
   ```bash
   # See rule evaluation state
   curl -s http://192.168.1.104:9090/api/v1/rules | \
       jq '.data.groups[].rules[] | select(.name == "TailscaleCriticalDeviceOffline")'
   ```

3. Verify `for:` duration hasn't prevented firing yet

### Webhook Not Receiving Alerts

**Problem:** Alertmanager not sending to AI agents

**Checks:**
1. Verify Alertmanager routing:
   ```bash
   # Check Alertmanager config
   curl http://192.168.1.106:9093/api/v1/status
   ```

2. Check network connectivity:
   ```bash
   # From Alertmanager server
   curl http://100.67.169.111:5000/health
   ```

3. Check AI agents logs:
   ```bash
   ssh root@100.67.169.111 "docker logs homelab-agents --tail 100"
   ```

### Missing Metrics

**Problem:** Alert queries fail because metrics don't exist

**Solution:** Install/configure exporters:

**Tailscale Metrics:**
- Requires custom exporter or scripts
- See `/home/munky/homelab-agents/crews/tools/tailscale_tools.py` for API usage
- May need to create Prometheus exporter script

**PostgreSQL Metrics:**
- Install `postgres_exporter`:
  ```bash
  # Example with Docker
  docker run -d \
    --name postgres-exporter \
    -p 9187:9187 \
    -e DATA_SOURCE_NAME="postgresql://postgres_exporter:password@192.168.1.50:5432/postgres?sslmode=disable" \
    wrouesnel/postgres_exporter
  ```

- Add to Prometheus scrape config:
  ```yaml
  scrape_configs:
    - job_name: 'postgresql'
      static_configs:
        - targets: ['192.168.1.50:9187']
  ```

---

## 📊 Expected Behavior After Deployment

### Normal Operation

When deployed correctly:
1. **Rules Loaded:** 18 rules visible in Prometheus UI
2. **Evaluation:** Rules evaluated every 30-60s
3. **Alert States:**
   - **Pending:** Alert condition met, waiting for `for:` duration
   - **Firing:** Alert fired and sent to Alertmanager
   - **Resolved:** Alert condition no longer true
4. **AI Processing:** Firing alerts trigger AI agent crew execution
5. **Resolution:** Agents diagnose and remediate (2-5 minutes typically)
6. **Notification:** Telegram message sent on completion

### Metrics to Monitor

Check these metrics post-deployment:
```bash
# AI agents processing metrics
curl -s http://100.67.169.111:5000/metrics

# Expected metrics:
# - ai_agents_incidents_total
# - ai_agents_success_rate
# - ai_agents_avg_resolution_seconds
# - ai_agents_incidents_by_severity
```

---

## 📚 Additional Resources

- **Prometheus Documentation:** https://prometheus.io/docs/
- **Alertmanager Documentation:** https://prometheus.io/docs/alerting/latest/alertmanager/
- **PromQL Cheat Sheet:** https://promlabs.com/promql-cheat-sheet/
- **Alert Rules Best Practices:** https://prometheus.io/docs/practices/alerting/

---

## 🎯 Quick Reference Commands

```bash
# === Deployment ===
scp tailscale-postgresql-alerts.yml root@192.168.1.104:/etc/prometheus/rules/
curl -X POST http://192.168.1.104:9090/-/reload

# === Verification ===
curl -s http://192.168.1.104:9090/api/v1/rules | jq '.data.groups[].name'
curl -s http://192.168.1.104:9090/api/v1/alerts

# === Testing ===
curl -s http://100.67.169.111:5000/health | jq '.'
curl -X POST http://100.67.169.111:5000/alert -H "Content-Type: application/json" -d '@test-alert.json'

# === Monitoring ===
ssh root@100.67.169.111 "docker logs -f homelab-agents"
curl -s http://100.67.169.111:5000/stats | jq '.'
```

---

## ✅ Deployment Checklist

- [ ] Prometheus server accessible (192.168.1.104:9090)
- [ ] Alertmanager accessible (192.168.1.106:9093)
- [ ] Alert rules file copied to Prometheus server
- [ ] Prometheus configuration updated with rule_files
- [ ] Configuration validated with promtool
- [ ] Prometheus reloaded/restarted
- [ ] Rules visible in Prometheus UI
- [ ] Alertmanager routing configured
- [ ] Alertmanager reloaded/restarted
- [ ] Test alert sent successfully
- [ ] AI agents received and processed test alert
- [ ] Telegram notification received
- [ ] Metrics endpoint working
- [ ] Documentation reviewed

---

**Created:** 2025-10-26
**Phase:** 12 - Fix Critical Issues & Deploy Alert Rules
**Status:** Ready for Deployment
**Next:** Deploy to Prometheus server and verify
