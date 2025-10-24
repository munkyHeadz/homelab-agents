# Phase 3 Features - v2.7: Advanced Monitoring & Automation

**Release Date:** 2025-10-24
**Version:** 2.7.0

This document describes the Phase 3 features added to the Homelab Agent System, focusing on advanced monitoring, predictive analysis, and intelligent automation.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Backup Verification System](#backup-verification-system)
3. [Service Health Monitoring](#service-health-monitoring)
4. [Predictive Analysis](#predictive-analysis)
5. [Web Dashboard](#web-dashboard)
6. [Advanced Automation](#advanced-automation)
7. [Telegram Commands](#telegram-commands)
8. [Configuration](#configuration)
9. [Deployment](#deployment)
10. [API Reference](#api-reference)

---

## Overview

Phase 3 introduces enterprise-grade monitoring and automation features:

### Key Features

✅ **Backup Verification**
- Automated backup integrity checks
- Restore testing (dry-run)
- Critical VM backup monitoring
- Success rate tracking

✅ **Service Health Monitoring**
- Multi-service support (Plex, Sonarr, Radarr, Jellyfin, etc.)
- HTTP endpoint health checks
- API availability testing
- Service-specific metrics

✅ **Predictive Analysis**
- Resource usage forecasting
- Failure prediction
- Capacity planning
- Trend analysis
- Anomaly detection

✅ **Web Dashboard**
- Real-time monitoring interface
- Visual status indicators
- Historical metrics charting
- Mobile-responsive design

✅ **Advanced Automation**
- SSL certificate monitoring & renewal
- Scheduled system updates
- Automated log cleanup
- Database maintenance
- Docker image update checks

---

## Backup Verification System

### Features

The Backup Verification Agent automatically verifies backup integrity and ensures your data is recoverable.

#### Verification Levels

1. **BASIC** - Checks backup exists with recent timestamp
2. **CHECKSUM** - Verifies file integrity via checksums
3. **RESTORE_TEST** - Performs actual restore test (dry-run)

#### Automatic Monitoring

```python
# Runs verification every 24 hours (configurable)
BACKUP_VERIFICATION_INTERVAL=86400  # seconds

# Maximum backup age before alert (hours)
MAX_BACKUP_AGE_HOURS=48

# Enable restore testing
ENABLE_RESTORE_TESTS=false  # Set to true for full testing
```

#### Critical VMs

Designate critical VMs that MUST have backups:

```bash
# .env configuration
CRITICAL_VMS=100,101,104,105
```

If any critical VM is missing a backup, you'll receive immediate alerts.

#### Telegram Commands

```bash
/verify_backups       # Verify all backups now
/backup_report        # Detailed backup verification report
```

#### Example Output

```
💾 Backup Verification Complete

Total VMs: 8
✅ Verified: 7
❌ Failed: 0
⚠️ Missing: 1

Recent Backups:
✅ VM 104 (homelab-agents): 2.3h ago, 12.5 GB
✅ VM 101 (nginx-proxy): 5.1h ago, 1.2 GB
⚠️ VM 105 (test-server): 50.2h ago (TOO OLD!)
```

---

## Service Health Monitoring

### Supported Services

The Service Health Agent monitors the following services:

- **Plex Media Server** - Stream status, transcoding
- **Sonarr** - Download queue, indexer health
- **Radarr** - Movie downloads, quality profiles
- **Lidarr** - Music downloads
- **Jellyfin** - Media streaming
- **Home Assistant** - Smart home status
- **Nextcloud** - Cloud storage
- **Pi-hole** - DNS filtering, ad blocking
- **Portainer** - Docker management

### Configuration

Add service URLs to your `.env` file:

```bash
# Media Services
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_plex_token

SONARR_URL=http://192.168.1.100:8989
SONARR_API_KEY=your_api_key

RADARR_URL=http://192.168.1.100:7878
RADARR_API_KEY=your_api_key

JELLYFIN_URL=http://192.168.1.100:8096

# Home Automation
HOME_ASSISTANT_URL=http://192.168.1.100:8123
HOME_ASSISTANT_TOKEN=your_token

# Network Services
PIHOLE_URL=http://192.168.1.100
NEXTCLOUD_URL=https://cloud.example.com

# Container Management
PORTAINER_URL=http://192.168.1.100:9000
```

### Health Checks

For each service, the agent performs:

1. **HTTP Availability** - Can we reach the service?
2. **Response Time** - How fast is it responding?
3. **API Health** - Are API endpoints working?
4. **Service Metrics** - Service-specific stats

#### Service-Specific Metrics

**Plex:**
- Active streams
- Transcoding sessions
- Server load

**Sonarr/Radarr:**
- Download queue size
- Active downloads
- Indexer status

**Pi-hole:**
- Queries today
- Blocked queries
- Percent blocked

### Telegram Commands

```bash
/services          # List all monitored services
/service_health    # Detailed service health report
```

#### Example Output

```
🔧 Monitored Services

✅ Plex Media Server (0.12s)
   2 streams, 1 transcoding
✅ Sonarr (0.08s)
   3 queued, 1 downloading
🟡 Radarr (2.45s)
   ⚠️ Slow response time
✅ Pi-hole (0.05s)
   1,245 queries, 234 blocked (18.8%)
🔴 Jellyfin
   ⚠️ Connection error: timeout
```

---

## Predictive Analysis

### Overview

The Predictive Analysis Agent uses historical data and statistical analysis to forecast potential issues before they occur.

### Prediction Types

1. **DISK_FULL** - Predicts when disk space will run out
2. **MEMORY_EXHAUSTION** - Forecasts memory exhaustion
3. **CPU_OVERLOAD** - Detects CPU saturation trends
4. **SERVICE_FAILURE** - Predicts service failures based on patterns
5. **BACKUP_FAILURE** - Forecasts backup job failures
6. **CONTAINER_CRASH** - Predicts container stability issues

### How It Works

#### 1. Data Collection

The agent collects metrics every hour:
- CPU usage
- Memory usage
- Disk usage
- Service response times
- Error rates

#### 2. Trend Analysis

Uses linear regression to calculate:
- **Slope** - Rate of change
- **Direction** - Increasing, decreasing, stable
- **Volatility** - Standard deviation

#### 3. Forecasting

Predicts future values using historical trends:

```python
# Example: Disk full prediction
current_usage = 75%
rate_of_increase = 0.5% per hour
threshold = 95%

hours_until_full = (95 - 75) / 0.5 = 40 hours
predicted_time = now + 40 hours
```

#### 4. Confidence Levels

- **HIGH** (>80%) - Low volatility, consistent trend
- **MEDIUM** (50-80%) - Moderate volatility
- **LOW** (<50%) - High volatility, uncertain

### Configuration

```bash
# Analysis interval (seconds)
PREDICTION_INTERVAL=3600  # 1 hour

# Historical data window (days)
PREDICTION_HISTORY_DAYS=7

# Minimum data points for predictions
# (default: 24 = 1 day of hourly data)
```

### Telegram Commands

```bash
/predictions         # Show predictive analysis
/prediction_report   # Detailed prediction report
/trends              # View resource usage trends
```

### Example Output

```
🔮 Predictive Analysis

Generated 3 predictions:

🟡 proxmox_node
   Disk Full
   In ~5 days
   Disk usage at 78.2%, trending up at 0.8%/hour

🔵 docker_daemon
   Memory Exhaustion
   In ~14 days
   Memory usage at 65.1%, trending up at 0.2%/hour

🟡 vm_104
   Service Failure
   In ~3 days
   Based on 4 recent failures, average interval: 72.5h
```

---

## Web Dashboard

### Overview

A real-time web interface for monitoring your homelab from any device.

### Features

- **Live Status Monitoring** - Real-time system health
- **Service Status** - Visual service health indicators
- **Active Issues** - Current problems and resolutions
- **Predictions** - Predictive analysis visualization
- **Backup Status** - Backup verification results
- **Auto-Refresh** - Updates every 30 seconds

### Access

The dashboard runs on port 5000 (configurable):

```bash
http://192.168.1.104:5000
```

Or access via Tailscale/VPN:

```bash
http://homelab-agents:5000
```

### Screenshots

#### Main Dashboard
![Dashboard Overview](./screenshots/dashboard-main.png)

- Overall system status badge
- Active issues count
- Resolved issues today
- Services up/down

#### Service Monitoring
![Service Status](./screenshots/dashboard-services.png)

- Real-time service health
- Response times
- Service-specific metrics

#### Predictive Analysis
![Predictions](./screenshots/dashboard-predictions.png)

- Future issue forecasts
- Confidence levels
- Recommendations

### Starting the Dashboard

#### Option 1: Standalone

```bash
cd /root/homelab-agents
python3 web/dashboard.py
```

#### Option 2: With Agents (Recommended)

The dashboard starts automatically when you enable auto-healing:

```bash
/enable_autohealing
```

### API Endpoints

The dashboard exposes REST APIs:

```
GET /api/status              # Overall system status
GET /api/health              # Health agent data
GET /api/predictions         # Predictive analysis
GET /api/services            # Service health
GET /api/backups             # Backup verification
GET /api/infrastructure      # VM/Container stats
GET /api/metrics/history     # Historical metrics
GET /api/trends              # Trend analysis
```

### Example API Response

```json
{
  "status": "healthy",
  "timestamp": "2025-10-24T14:30:00Z",
  "active_issues": 0,
  "resolved_today": 3,
  "services_up": 8,
  "services_total": 9
}
```

---

## Advanced Automation

### Overview

The Advanced Automation Agent handles routine maintenance tasks automatically.

### Automated Tasks

#### 1. SSL Certificate Monitoring

**Schedule:** Daily
**Action:** Check certificate expiration

```bash
# Configure domains to check
DOMAINS_TO_CHECK=example.com,*.example.com,api.example.com

# Days before expiration to alert
CERT_RENEWAL_DAYS=30
```

**Features:**
- Checks SSL certificates via OpenSSL
- Alerts 30 days before expiration
- Can trigger automatic renewal (Let's Encrypt)

#### 2. System Updates

**Schedule:** Weekly
**Action:** Check for OS updates

```bash
# Enable automatic updates
AUTO_UPDATE_ENABLED=true
```

**Features:**
- Checks for apt updates
- Identifies security updates
- Can apply updates automatically
- Sends notification before/after

#### 3. Log Cleanup

**Schedule:** Daily
**Action:** Remove old log files

**Features:**
- Removes logs older than 30 days
- Frees up disk space
- Preserves recent logs

**Directories cleaned:**
- `/var/log`
- `/root/homelab-agents/logs`
- `/tmp`

#### 4. Database Maintenance

**Schedule:** Weekly
**Action:** VACUUM and ANALYZE

**Features:**
- PostgreSQL optimization
- Reclaims disk space
- Updates query planner statistics

#### 5. Docker Image Updates

**Schedule:** Daily
**Action:** Check for new images

**Features:**
- Pulls latest images
- Compares with running containers
- Alerts on available updates
- Does NOT auto-update (safety)

### Manual Triggers

You can trigger automation tasks manually:

```bash
# In Python code
from agents.automation_agent import AdvancedAutomationAgent

agent = AdvancedAutomationAgent()

# Check certificates
await agent.check_ssl_certificates()

# Check updates
await agent.check_system_updates()

# Clean logs
await agent.cleanup_old_logs()
```

---

## Telegram Commands

### Phase 3 Command Reference

#### Backup Verification

```bash
/verify_backups      # Verify all backups now
/backup_report       # Detailed backup report
```

#### Service Health

```bash
/services            # List all monitored services
/service_health      # Detailed service health report
```

#### Predictive Analysis

```bash
/predictions         # Show predictive forecasts
/prediction_report   # Detailed prediction report
/trends              # View resource usage trends
```

### Complete Command List (All Phases)

```bash
# System Status
/status              # Overall system status
/uptime              # System and bot uptime
/monitor             # Real-time resource monitoring
/menu                # Interactive control menu

# VM Management
/node                # Proxmox node status
/vms                 # List all VMs
/start_vm <id>       # Start VM
/stop_vm <id>        # Stop VM
/restart_vm <id>     # Restart VM

# Docker Management
/docker              # Docker system info
/containers          # List containers
/restart_container   # Restart container
/stop_container      # Stop container

# Health & Auto-Healing
/health              # System health report
/enable_autohealing  # Start autonomous monitoring
/disable_autohealing # Stop autonomous monitoring

# Reporting
/enable_reports      # Enable daily/weekly/monthly reports
/disable_reports     # Disable reports
/report_now          # Generate immediate report

# Backups (Phase 1 & 3)
/backup              # Show backup status
/verify_backups      # Verify backup integrity
/backup_report       # Detailed backup report

# Services (Phase 3)
/services            # Monitor services
/service_health      # Service health report

# Predictions (Phase 3)
/predictions         # Predictive analysis
/prediction_report   # Detailed predictions
/trends              # Resource trends

# Bot Management
/update              # Pull latest code and restart
/help                # Show command reference
```

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# ============================================================================
# PHASE 3: ADVANCED MONITORING & AUTOMATION
# ============================================================================

# Backup Verification
BACKUP_VERIFICATION_INTERVAL=86400  # 24 hours
MAX_BACKUP_AGE_HOURS=48
ENABLE_RESTORE_TESTS=false
CRITICAL_VMS=100,101,104,105

# Service Health Monitoring
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_token
SONARR_URL=http://192.168.1.100:8989
SONARR_API_KEY=your_key
RADARR_URL=http://192.168.1.100:7878
RADARR_API_KEY=your_key
JELLYFIN_URL=http://192.168.1.100:8096
HOME_ASSISTANT_URL=http://192.168.1.100:8123
HOME_ASSISTANT_TOKEN=your_token
PIHOLE_URL=http://192.168.1.100
NEXTCLOUD_URL=https://cloud.example.com
PORTAINER_URL=http://192.168.1.100:9000

# Predictive Analysis
PREDICTION_INTERVAL=3600  # 1 hour
PREDICTION_HISTORY_DAYS=7

# Web Dashboard
DASHBOARD_PORT=5000
DASHBOARD_HOST=0.0.0.0

# Advanced Automation
DOMAINS_TO_CHECK=example.com,*.example.com
CERT_RENEWAL_DAYS=30
AUTO_UPDATE_ENABLED=false  # Set to true for auto-updates
SECURITY_SCAN_ENABLED=true
```

---

## Deployment

### Prerequisites

```bash
# Install new dependencies
pip install -r requirements.txt

# This includes:
# - flask==3.0.0 (web dashboard)
# - flask-cors==4.0.0 (CORS support)
# - numpy==1.26.4 (predictive analysis)
```

### Step 1: Update Configuration

Edit your `.env` file and add Phase 3 configuration (see Configuration section above).

### Step 2: Start the Bot

The new agents start automatically when you enable auto-healing:

```bash
# Via Telegram
/enable_autohealing
```

This starts:
- Health monitoring (60s intervals)
- Backup verification (daily)
- Service health monitoring (60s intervals)
- Predictive analysis (hourly)
- Advanced automation (hourly task checks)
- Web dashboard (port 5000)

### Step 3: Access the Dashboard

Open in your browser:

```bash
http://YOUR_LXC_IP:5000
```

For example:
```bash
http://192.168.1.104:5000
```

### Step 4: Configure Services

Add URLs for the services you want to monitor in `.env`, then restart:

```bash
/update  # or restart manually
```

### Step 5: Verify Operation

Check that everything is working:

```bash
/services          # Should show your configured services
/predictions       # May say "needs more data" initially
/verify_backups    # Should check your VMs
```

---

## API Reference

### REST API Endpoints

#### GET /api/status

Returns overall system status.

**Response:**
```json
{
  "timestamp": "2025-10-24T14:30:00Z",
  "status": "healthy",
  "uptime": 86400,
  "active_issues": 0,
  "resolved_today": 3,
  "services_up": 8,
  "services_total": 9
}
```

#### GET /api/health

Returns detailed health information.

**Response:**
```json
{
  "active_issues": [
    {
      "component": "vm_105",
      "type": "high_memory",
      "severity": "warning",
      "description": "Memory usage: 89.2%",
      "detected_at": "2025-10-24T14:25:00Z",
      "risk_level": "medium"
    }
  ],
  "resolved_issues": [...],
  "summary": "..."
}
```

#### GET /api/predictions

Returns predictive analysis data.

**Response:**
```json
{
  "predictions": [
    {
      "type": "disk_full",
      "component": "proxmox_node",
      "predicted_time": "2025-10-29T14:30:00Z",
      "confidence": "high",
      "severity": "warning",
      "description": "Disk usage at 78.2%, trending up at 0.8%/hour",
      "recommendation": "Free up disk space or expand storage",
      "created_at": "2025-10-24T14:30:00Z"
    }
  ]
}
```

#### GET /api/services

Returns service health data.

**Response:**
```json
{
  "services": [
    {
      "id": "plex",
      "name": "Plex Media Server",
      "type": "plex",
      "status": "healthy",
      "response_time": 0.12,
      "last_check": "2025-10-24T14:30:00Z",
      "error_message": null,
      "metrics": {
        "active_streams": 2,
        "transcoding": 1
      }
    }
  ]
}
```

#### GET /api/backups

Returns backup verification data.

**Response:**
```json
{
  "summary": {
    "total_vms": 8,
    "verified": 7,
    "failed": 0,
    "missing": 1
  },
  "backups": [
    {
      "vm_id": 104,
      "vm_name": "homelab-agents",
      "backup_time": "2025-10-24T12:15:00Z",
      "backup_size": 13421772800,
      "status": "success",
      "verification_level": "checksum",
      "restore_test_passed": false
    }
  ]
}
```

---

## Troubleshooting

### Dashboard Won't Start

**Problem:** Dashboard fails to start or shows errors.

**Solutions:**
1. Check Flask is installed: `pip install flask flask-cors`
2. Check port 5000 is not in use: `netstat -tulpn | grep 5000`
3. Check logs: `tail -f /root/homelab-agents/logs/dashboard.log`

### Services Show as "Down"

**Problem:** All services show as down or unreachable.

**Solutions:**
1. Verify URLs are correct in `.env`
2. Check firewall rules
3. Test connectivity: `curl http://SERVICE_URL`
4. Check API keys are valid

### No Predictions Available

**Problem:** Predictive analysis says "needs more data".

**Solution:** This is normal! The system needs at least 24 hours of data to make predictions. Check back after the system has been monitoring for a day.

### Backup Verification Fails

**Problem:** `/verify_backups` shows all backups as failed.

**Solutions:**
1. Check Proxmox credentials are correct
2. Verify backup storage is accessible
3. Check MCP Proxmox tool is working: Test with `/vms` command

---

## Performance Considerations

### Resource Usage

Phase 3 agents are lightweight:

- **Backup Verification:** Runs once per day, ~5-10 seconds per VM
- **Service Health:** 60-second intervals, <1 second per service
- **Predictive Analysis:** Hourly analysis, <5 seconds
- **Web Dashboard:** ~10MB RAM, minimal CPU
- **Automation Agent:** Hourly task checks, minimal impact

### Memory Footprint

Total additional memory usage: ~50-100 MB

### Network Usage

- Service health checks: ~1KB per check
- Dashboard: ~50KB per page load
- Total: Negligible for local network

---

## What's Next?

### Phase 4 Roadmap (Future)

- Machine learning-based anomaly detection
- Custom alerting rules engine
- Integration with external monitoring (Grafana, Datadog)
- Mobile app
- Voice control (Alexa/Google Home)
- Cost tracking and optimization
- Multi-site support

---

## Support

### Getting Help

- **Documentation:** `/root/homelab-agents/docs/`
- **GitHub Issues:** [Create an issue](https://github.com/yourusername/homelab-agents/issues)
- **Telegram:** Use `/help` command

### Contributing

Phase 3 is open source! Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Version:** 2.7.0
**Last Updated:** 2025-10-24
**Author:** Homelab Agents Team
