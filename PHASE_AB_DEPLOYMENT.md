# Phase A & B Deployment Guide

## ✅ Status: CODE COMPLETE - READY FOR DEPLOYMENT

All code for Phase A (Alert Integration) and Phase B (VM Control) is **already integrated** into the telegram bot!

**What's already done:**
- ✅ Alert manager system implemented
- ✅ Webhook server implemented
- ✅ All command handlers added to bot
- ✅ Commands registered in application
- ✅ Webhook server starts automatically with bot
- ✅ Infrastructure agent integration complete

---

## 🚀 Quick Deployment Steps

### Step 1: Configure Alertmanager (15 min)

**Connect to monitoring LXC (107):**
```bash
ssh root@192.168.1.107
# or
pct enter 107
```

**Backup existing config:**
```bash
cp /etc/alertmanager/alertmanager.yml /etc/alertmanager/alertmanager.yml.backup
```

**Update configuration:**
```bash
cat > /etc/alertmanager/alertmanager.yml <<'EOF'
global:
  resolve_timeout: 5m

route:
  receiver: 'telegram-webhook'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'telegram-webhook'
    webhook_configs:
      - url: 'http://192.168.1.104:8001/webhook/alerts'
        send_resolved: true
        http_config:
          follow_redirects: true
        max_alerts: 0

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
EOF
```

**Restart Alertmanager:**
```bash
systemctl restart alertmanager
systemctl status alertmanager
```

**Verify configuration:**
```bash
# Check config is valid
amtool check-config /etc/alertmanager/alertmanager.yml

# View current alerts
curl http://localhost:9093/api/v2/alerts
```

---

### Step 2: Restart Telegram Bot (5 min)

The bot will automatically start the webhook server on port 8001.

**Option A: If bot is already running via systemd:**
```bash
sudo systemctl restart homelab-bot
sudo systemctl status homelab-bot
```

**Option B: If running manually:**
```bash
cd /home/munky/homelab-agents
source venv/bin/activate
pkill -f telegram_bot.py  # Stop old instance
python interfaces/telegram_bot.py  # Start new instance
```

**Verify webhook server is running:**
```bash
curl http://localhost:8001/health
# Should return JSON with alert stats
```

---

### Step 3: Test Alert Flow (15 min)

**Test 1: Trigger a test alert from Prometheus**
```bash
# On monitoring LXC (107)
cat > /tmp/test_alert.yml <<EOF
groups:
  - name: test
    interval: 10s
    rules:
      - alert: TestAlert
        expr: up{job="node"} == 1  # Will fire immediately
        for: 0s
        labels:
          severity: warning
        annotations:
          summary: "Test alert from Prometheus"
          description: "This is a test alert to verify webhook integration"
EOF

# Load the test rules
curl -X POST http://localhost:9090/api/v1/admin/tsdb/reload
```

**Expected behavior:**
1. Alert fires in Prometheus
2. Alertmanager receives alert
3. Webhook sent to bot at `http://192.168.1.104:8001/webhook/alerts`
4. 📱 Notification appears in Telegram
5. `/alerts` command shows the active alert

**Test 2: Test alert commands in Telegram**
```
You: /alerts
Bot: Shows active alerts with fingerprints

You: /ack a1b2c3d4
Bot: ✅ Alert acknowledged

You: /silence a1b2c3d4 30
Bot: 🔕 Alert silenced for 30 minutes
```

---

## 🎮 Available Commands

### Phase A: Alert Integration

| Command | Description | Example |
|---------|-------------|---------|
| `/alerts` | Show all active alerts | `/alerts` |
| `/ack <fingerprint>` | Acknowledge an alert | `/ack a1b2c3d4` |
| `/silence <fingerprint> [minutes]` | Silence alert notifications | `/silence a1b2c3d4 60` |

### Phase B: VM/Container Control

| Command | Description | Example |
|---------|-------------|---------|
| `/start_vm <vmid>` | Start a VM or container | `/start_vm 101` |
| `/stop_vm <vmid>` | Stop a VM (requires confirmation) | `/stop_vm 101` |
| `/restart_vm <vmid>` | Restart a VM or container | `/restart_vm 101` |
| `/confirm <id>` | Confirm destructive action | `/confirm stop_101` |

---

## 🔍 Troubleshooting

### Webhook Server Not Starting

**Check bot logs:**
```bash
journalctl -u homelab-bot -f
# or if running manually, check console output
```

**Verify port 8001 is not in use:**
```bash
netstat -tuln | grep 8001
# or
lsof -i :8001
```

### Alerts Not Appearing in Telegram

**Check webhook server health:**
```bash
curl http://192.168.1.104:8001/health
```

**Check Alertmanager logs:**
```bash
# On monitoring LXC (107)
journalctl -u alertmanager -f
```

**Verify webhook URL is reachable from monitoring LXC:**
```bash
# On monitoring LXC (107)
curl -X POST http://192.168.1.104:8001/webhook/alerts \
  -H "Content-Type: application/json" \
  -d '{"status":"firing","alerts":[{"labels":{"alertname":"test"}}]}'
```

### VM Control Not Working

**Verify infrastructure agent has access:**
```bash
# Test from Python
python -c "
from agents.infrastructure_agent import InfrastructureAgent
import asyncio

async def test():
    agent = InfrastructureAgent()
    result = await agent.execute('List all VMs')
    print(result)

asyncio.run(test())
"
```

**Check Proxmox API credentials:**
```bash
# Verify token in .env
grep PROXMOX_TOKEN .env
```

---

## 📊 Monitoring Integration Points

### Alert Flow
```
Prometheus Alert Rule Fires
    ↓
Alertmanager receives alert
    ↓
Webhook POST to http://192.168.1.104:8001/webhook/alerts
    ↓
WebhookServer.handle_alert_webhook()
    ↓
AlertManager.process_webhook()
    ↓
Alert stored in memory
    ↓
TelegramBot.on_alert_received()
    ↓
📱 Push notification to admin users
```

### VM Control Flow
```
User: /start_vm 101
    ↓
TelegramBot.start_vm_command()
    ↓
InfrastructureAgent.execute("Start VM 101")
    ↓
Proxmox API: Start VM
    ↓
✅ Status message sent to user
```

---

## 🎯 Success Criteria

After deployment, verify:

- [ ] Webhook server running on port 8001
- [ ] `/health` endpoint returns alert stats
- [ ] Alertmanager can send webhooks successfully
- [ ] Test alert appears in Telegram
- [ ] `/alerts` command shows active alerts
- [ ] `/ack` acknowledges alerts
- [ ] `/silence` silences alerts
- [ ] `/start_vm` can start VMs
- [ ] `/stop_vm` requires confirmation
- [ ] `/confirm` executes confirmed actions
- [ ] `/restart_vm` works correctly

---

## 📈 Next Steps After Deployment

Once Phase A & B are deployed and tested:

1. **Phase C: Backup Management** (2-3 hours)
   - PBS integration
   - Backup monitoring
   - Restore capabilities

2. **Phase D: Scheduled Reports** (2-3 hours)
   - Daily system summaries
   - Weekly trends
   - Monthly reports

3. **Phase H: Observability** (3-4 hours)
   - Prometheus metrics display
   - Grafana dashboard links
   - Performance monitoring

---

## 🆘 Support

- **Bot logs:** `journalctl -u homelab-bot -f`
- **Alertmanager logs:** `journalctl -u alertmanager -f`
- **Webhook server health:** `http://192.168.1.104:8001/health`
- **Prometheus UI:** `http://192.168.1.104:9090`
- **Alertmanager UI:** `http://192.168.1.107:9093`

---

**Deployment Time Estimate:** 30-45 minutes total
**Difficulty:** Easy (configuration only, no code changes needed)
**Status:** ✅ Ready to Deploy
