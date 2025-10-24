# Prometheus Alert Integration

## Overview

The homelab agent system can receive alerts directly from Prometheus Alertmanager and:
- Forward them to Telegram for notification
- Automatically attempt remediation via the Autonomous Health Agent
- Track alert history and patterns

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Prometheus  │────▶│  Alertmanager    │────▶│  Homelab Agent │
│   (Metrics)  │     │   (Grouping)     │     │  Alert Receiver│
└──────────────┘     └──────────────────┘     └────────┬───────┘
                                                         │
                                         ┌──────────────┴───────────┐
                                         ▼                          ▼
                                  ┌─────────────┐          ┌──────────────┐
                                  │  Telegram   │          │   Health     │
                                  │ Notification│          │    Agent     │
                                  └─────────────┘          └──────────────┘
                                                                  │
                                                           Auto-Remediation
```

## Setup

### Step 1: Configure Alertmanager

Edit your Alertmanager configuration (`/etc/alertmanager/alertmanager.yml`):

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'homelab-telegram'

receivers:
  - name: 'homelab-telegram'
    webhook_configs:
      - url: 'http://192.168.1.104:9095/prometheus/webhook'
        send_resolved: true
```

**Replace `192.168.1.104` with your actual homelab agent LXC IP.**

### Step 2: Configure Environment Variables

In your `.env` file:

```bash
# Prometheus Integration
PROMETHEUS_WEBHOOK_PORT=9095
PROMETHEUS_WEBHOOK_PATH=/prometheus/webhook
```

### Step 3: Start the Alert Receiver

The alert receiver can be started:

**Option A: As part of Telegram bot (automatic)**

The bot will start it automatically when you enable auto-healing:

```
/enable_autohealing
```

**Option B: Standalone service**

Create systemd service (`/etc/systemd/system/prometheus-alert-receiver.service`):

```ini
[Unit]
Description=Prometheus Alert Receiver
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/homelab-agents
Environment="PYTHONPATH=/root/homelab-agents"
ExecStart=/root/homelab-agents/venv/bin/python agents/prometheus_alert_receiver.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
systemctl daemon-reload
systemctl enable prometheus-alert-receiver
systemctl start prometheus-alert-receiver
```

### Step 4: Update Firewall (if needed)

Allow incoming connections on port 9095:

```bash
# On homelab agent LXC
iptables -A INPUT -p tcp --dport 9095 -j ACCEPT

# Or in Proxmox firewall rules
```

### Step 5: Test the Integration

Send a test alert from Prometheus:

```bash
# Test webhook endpoint
curl -X POST http://192.168.1.104:9095/prometheus/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "receiver": "homelab-telegram",
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "TestAlert",
        "severity": "warning",
        "instance": "test-instance"
      },
      "annotations": {
        "summary": "This is a test alert",
        "description": "Testing Prometheus integration"
      }
    }]
  }'
```

You should receive a message in Telegram!

## Alert Format

### Firing Alert

When an alert fires, you'll receive:

```
🟡 Prometheus Alert

HighCPU
Severity: WARNING
Instance: 192.168.1.101

Summary: CPU usage is high

Description: CPU usage has been above 90% for 5 minutes

Time: 2025-10-24 10:30:00
```

### Resolved Alert

When an alert resolves:

```
✅ Alert Resolved

HighCPU
Instance: 192.168.1.101

CPU usage returned to normal

Time: 2025-10-24 10:35:00
```

## Auto-Remediation

The system automatically attempts to fix certain alerts:

### Alerts with Auto-Fix (LOW Risk)

- **ContainerDown** → Restart container
- **HighDiskUsage** → Clean up old data
- **UnhealthyContainer** → Restart container

### Alerts Requiring Approval (MEDIUM/HIGH Risk)

- **HighCPU** → Kill high-CPU processes
- **HighMemory** → Clear caches/stop services
- **ServiceDown** → Restart service
- **HostDown** → Investigate connectivity

You'll receive an approval request in Telegram:

```
⚠️ Action Approval Required

Component: 192.168.1.101
Issue: High CPU usage detected
Severity: 🟡 WARNING
Risk Level: MEDIUM

Suggested Fix: Identify and optimize high-CPU processes

Should I proceed with this action?

[✅ Approve] [❌ Reject]
```

## Example Prometheus Alert Rules

Add these to your Prometheus rules (`/etc/prometheus/rules.yml`):

```yaml
groups:
  - name: homelab
    interval: 30s
    rules:
      # High CPU Alert
      - alert: HighCPU
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanize }}%"

      # High Memory Alert
      - alert: HighMemory
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanize }}%"

      # High Disk Usage Alert
      - alert: HighDiskUsage
        expr: (node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage on {{ $labels.instance }}"
          description: "Disk usage is {{ $value | humanize }}%"

      # Container Down Alert
      - alert: ContainerDown
        expr: absent(container_last_seen{name!=""})
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.name }} is down"
          description: "Container has not been seen for 5 minutes"

      # Service Down Alert
      - alert: ServiceDown
        expr: up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.instance }} has been down for 5 minutes"
```

## Configuration Options

### Environment Variables

```bash
# Webhook Configuration
PROMETHEUS_WEBHOOK_PORT=9095              # Port for webhook receiver
PROMETHEUS_WEBHOOK_PATH=/prometheus/webhook  # Webhook endpoint path

# Alert Deduplication
ALERT_DEDUP_WINDOW=300                    # Seconds to deduplicate alerts (default: 5 min)
```

### Alert Routing

You can route different severity levels to different handlers:

**In `prometheus_alert_receiver.py`**, modify the `forward_to_health_agent` method to add custom logic based on alert labels.

## Monitoring the Integration

### Check Alert Receiver Status

```bash
# Check if service is running
systemctl status prometheus-alert-receiver

# Check logs
journalctl -u prometheus-alert-receiver -f

# Test health endpoint
curl http://localhost:9095/health
```

### In Telegram

Check the health of the integration:

```
/health
```

Should show connection to Prometheus alert receiver.

## Troubleshooting

### Alerts Not Arriving

1. **Check Alertmanager configuration**:
   ```bash
   # Verify config
   amtool check-config /etc/alertmanager/alertmanager.yml

   # Check Alertmanager logs
   journalctl -u alertmanager -f
   ```

2. **Check network connectivity**:
   ```bash
   # Test from Alertmanager host
   curl http://192.168.1.104:9095/health
   ```

3. **Check webhook receiver logs**:
   ```bash
   journalctl -u prometheus-alert-receiver -f
   ```

### Duplicate Alerts

The receiver has built-in deduplication (5-minute window). If you're still seeing duplicates:

1. Increase `ALERT_DEDUP_WINDOW` in `.env`
2. Adjust Alertmanager `repeat_interval`

### Auto-Remediation Not Working

1. Ensure auto-healing is enabled: `/enable_autohealing`
2. Check health agent logs
3. Verify the alert severity is `critical` or `warning`

## Advanced Configuration

### Custom Alert Handlers

Add custom handlers in `prometheus_alert_receiver.py`:

```python
def _suggest_fix_for_alert(self, alertname: str, alert: Dict[str, Any]) -> str:
    """Add your custom alert handlers here"""
    suggestions = {
        "HighCPU": "Identify and optimize high-CPU processes",
        "MyCustomAlert": "Custom remediation for my alert",
        # Add more...
    }
    return suggestions.get(alertname, f"Investigate {alertname} alert")
```

### Alert Filtering

Filter alerts before processing:

```python
async def process_alert(self, alert: Dict[str, Any], group_status: str):
    labels = alert.get("labels", {})

    # Skip certain alerts
    if labels.get("alertname") in ["NoiseAlert", "TestAlert"]:
        return

    # Only process critical alerts
    if labels.get("severity") != "critical":
        return

    # Continue processing...
```

## Integration with Other Tools

### Grafana Annotations

Alerts can also create Grafana annotations:

```python
# In prometheus_alert_receiver.py, add:
async def create_grafana_annotation(self, alert: Dict[str, Any]):
    """Create Grafana annotation for alert"""
    # Implementation here
```

### PagerDuty Integration

Forward critical alerts to PagerDuty:

```python
async def handle_firing_alert(self, ...):
    if severity == "critical":
        await self.forward_to_pagerduty(alert)
```

## Security Considerations

### Authentication

Add authentication to the webhook endpoint:

```python
async def handle_webhook(self, request: web.Request) -> web.Response:
    # Check API key
    api_key = request.headers.get("X-API-Key")
    if api_key != config.get("PROMETHEUS_API_KEY"):
        return web.Response(status=401)
    # Continue...
```

Then in Alertmanager:

```yaml
webhook_configs:
  - url: 'http://192.168.1.104:9095/prometheus/webhook'
    http_config:
      headers:
        X-API-Key: your-secret-key
```

### HTTPS/TLS

For production, use HTTPS:

1. Set up reverse proxy (nginx)
2. Use Let's Encrypt certificates
3. Update Alertmanager URL to `https://...`

## Summary

The Prometheus integration provides:

✅ **Real-time Alerts** - Instant notification in Telegram
✅ **Auto-Remediation** - Automatic fixes for common issues
✅ **Smart Routing** - Critical alerts get immediate attention
✅ **Deduplication** - Avoid alert fatigue
✅ **Integration** - Works seamlessly with autonomous health agent

**Quick Start:**
1. Configure Alertmanager webhook
2. Enable auto-healing: `/enable_autohealing`
3. Test with a sample alert
4. Watch the magic happen! 🎉
