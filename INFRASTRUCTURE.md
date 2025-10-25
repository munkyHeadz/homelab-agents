# Fjeld Homelab Infrastructure Topology

**Last Updated:** 2025-10-26
**Environment:** Production
**Network:** 192.168.1.0/24 + Tailscale VPN (100.x.x.x)

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                             │
└────────────┬────────────────────────────────────────────────────────┬────────┘
             │                                                        │
    ┌────────▼────────┐                                     ┌────────▼────────┐
    │  Cloudflare DNS │                                     │  Tailscale VPN  │
    │   (DNS-01 TLS)  │                                     │   100.x.x.x/16  │
    └────────┬────────┘                                     └────────┬────────┘
             │                                                        │
┌────────────▼─────────────────────────────────────────────────────────┬──────┐
│                    LOCAL NETWORK (192.168.1.0/24)                    │      │
│                                                                       │      │
│  ┌─────────────────────────────────────────────────────────────────┐│      │
│  │  PROXMOX HOST                                                    ││      │
│  │  ├─ vmbr0 (Bridge)                                               ││      │
│  │  └─ Tailscale: 100.64.220.69                                     ││      │
│  └─────────────────────────────────────────────────────────────────┘│      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  LXC 101: docker-gateway (192.168.1.101 / 100.67.169.111)    │  │      │
│  │  ┌──────────────────────────────────────────────────────────┐ │  │      │
│  │  │  Docker Network (traefik)                                 │ │  │      │
│  │  │  ├─ Traefik (Reverse Proxy + SSL)                         │ │  │      │
│  │  │  ├─ Homepage (Dashboard)                                  │ │  │      │
│  │  │  │                                                         │ │  │      │
│  │  │  Docker Network (monitoring)                              │ │  │      │
│  │  │  ├─ Prometheus (Metrics)                                  │ │  │      │
│  │  │  ├─ Alertmanager (Alerts)                                 │ │  │      │
│  │  │  ├─ Telegram-Forwarder (Notifications)                    │ │  │      │
│  │  │  └─ Node-Exporter (System Metrics)                        │ │  │      │
│  │  └──────────────────────────────────────────────────────────┘ │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  LXC 107: monitoring (192.168.1.107 / 100.120.140.105)       │  │      │
│  │  └─ Grafana (Visualization)                                   │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  LXC 200: postgres (192.168.1.50 / 100.108.125.86)           │  │      │
│  │  └─ PostgreSQL 15 + postgres_exporter                         │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  LXC 104: homelab-agents (192.168.1.102 / 100.69.150.29)     │  │      │
│  │  └─ Telegram Bot + Python Agents                              │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  LXC 108: portal (192.168.1.108 / 100.110.59.20)             │  │      │
│  │  └─ Homelab Control Portal (Python/Flask)                     │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  LXC 110: traefik-gateway (192.168.1.110)                    │  │      │
│  │  └─ (Reserved for future use)                                 │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
│  ┌───────────────────────────────────────────────────────────────┐  │      │
│  │  OTHER CONTAINERS                                              │  │      │
│  │  ├─ LXC 100: arr (192.168.1.151 / 100.122.192.4)             │  │      │
│  │  ├─ LXC 103: rustdeskserver (192.168.1.12 / 100.113.36.19)   │  │      │
│  │  ├─ LXC 105: portfolio (192.168.1.140 / 100.111.140.125)     │  │      │
│  │  ├─ LXC 106: adguard (192.168.1.104 / 100.94.4.16)           │  │      │
│  │  └─ LXC 112: plex (192.168.1.216 / 100.78.95.63)             │  │      │
│  └───────────────────────────────────────────────────────────────┘  │      │
│                                                                       │      │
└───────────────────────────────────────────────────────────────────────┴──────┘
```

---

## Container Inventory

### Core Infrastructure

| ID  | Hostname        | LAN IP        | Tailscale IP    | Role                | Resources      |
|-----|-----------------|---------------|-----------------|---------------------|----------------|
| 101 | docker-gateway  | 192.168.1.101 | 100.67.169.111  | Docker Host + Proxy | 4C/4GB/50GB    |
| 107 | monitoring      | 192.168.1.107 | 100.120.140.105 | Grafana Server      | 2C/4GB/30GB    |
| 200 | postgres        | 192.168.1.50  | 100.108.125.86  | PostgreSQL Database | 2C/2GB/20GB    |
| 104 | homelab-agents  | 192.168.1.102 | 100.69.150.29   | Automation Agents   | 2C/2GB/20GB    |
| 108 | portal          | 192.168.1.108 | 100.110.59.20   | Control Portal      | 2C/2GB/12GB    |
| 110 | traefik-gateway | 192.168.1.110 | -               | Reserved            | 2C/2GB/12GB    |

### Application Containers

| ID  | Hostname       | LAN IP        | Tailscale IP    | Purpose              | Resources     |
|-----|----------------|---------------|-----------------|----------------------|---------------|
| 100 | arr            | 192.168.1.151 | 100.122.192.4   | *arr Stack           | 2C/2GB/350GB  |
| 103 | rustdeskserver | 192.168.1.12  | 100.113.36.19   | Remote Desktop       | 1C/512MB/7GB  |
| 105 | portfolio      | 192.168.1.140 | 100.111.140.125 | Personal Website     | 1C/2GB/40GB   |
| 106 | adguard        | 192.168.1.104 | 100.94.4.16     | DNS Adblock          | 1C/512MB/7GB  |
| 112 | plex           | 192.168.1.216 | 100.78.95.63    | Media Server (GPU)   | 2C/4GB/48GB   |

---

## Service Map

### LXC 101: docker-gateway

**Docker Containers:**
```
traefik              → Reverse Proxy + SSL Termination
  ├─ Ports: 80, 443, 8080
  ├─ Cloudflare DNS-01 for Let's Encrypt
  └─ Routes all *.fjeld.tech traffic

homepage             → Homepage Dashboard
  ├─ Port: 3000
  └─ URL: https://home.fjeld.tech

prometheus           → Metrics Collection
  ├─ Port: 9090
  ├─ URL: https://prometheus.fjeld.tech
  └─ Scrapes: 13 targets across all containers

alertmanager         → Alert Routing
  ├─ Port: 9093
  ├─ URL: https://alerts.fjeld.tech
  └─ Routes to: telegram-forwarder

telegram-forwarder   → Notification Bridge
  ├─ Port: 9087 (internal)
  ├─ Bot: @Bobbaerbot
  └─ Forwards alerts to Telegram

node-exporter        → System Metrics
  ├─ Port: 9100
  └─ Includes: textfile collector for backup metrics
```

**Backup System:**
```
Restic Backup
  ├─ Repository: /mnt/disks/restic-repo
  ├─ Schedule: Daily @ 2:00 AM (cron)
  ├─ Script: /opt/backup-scripts/backup-with-monitoring.sh
  ├─ Retention: 7 daily, 4 weekly, 6 monthly
  └─ Metrics: Exported to Prometheus
```

### LXC 107: monitoring

**Services:**
```
Grafana              → Dashboard & Visualization
  ├─ Port: 3000
  ├─ URL: https://grafana.fjeld.tech
  ├─ Data Source: Prometheus (docker-gateway:9090)
  └─ Admin: admin / <configured>
```

### LXC 200: postgres

**Services:**
```
PostgreSQL 15        → Relational Database
  ├─ Port: 5432
  ├─ Version: 15/main
  └─ Users: postgres, postgres_exporter

postgres_exporter    → Database Metrics
  ├─ Port: 9187
  └─ Scraped by: Prometheus
```

### LXC 104: homelab-agents

**Services:**
```
Telegram Bot (@Bobbaerbot)
  ├─ Token: 8163435865:AAG...
  ├─ Chat ID: 500505500
  └─ Commands: Container control, status, monitoring

Python Automation
  ├─ Framework: Python + venv
  ├─ Repository: https://github.com/<user>/homelab-agents
  └─ Scripts: Various automation tasks
```

### LXC 108: portal

**Services:**
```
Homelab Portal       → Web Control Interface
  ├─ Framework: Python/Flask
  ├─ Port: 5000 (internal)
  ├─ Process: /opt/homelab-portal/venv/bin/python
  └─ Features: Container management, monitoring
```

---

## DNS & Domain Configuration

### Public Domain: fjeld.tech

**Cloudflare DNS Records:**
```
Type    Name        Target              Purpose
────────────────────────────────────────────────────────────
A       @           <public-ip>         Root domain
CNAME   *.          @                   Wildcard for subdomains
TXT     _acme-*     <challenge>         Let's Encrypt DNS-01
```

**Traefik Routes (SSL via Let's Encrypt):**
```
https://home.fjeld.tech       → Homepage Dashboard
https://grafana.fjeld.tech    → Grafana
https://prometheus.fjeld.tech → Prometheus
https://alerts.fjeld.tech     → Alertmanager
```

### Tailscale Private DNS

**MagicDNS Enabled:**
```
<hostname>.tahr-bass.ts.net   → All containers have Tailscale DNS names
Search Domains: tahr-bass.ts.net, fjeld.tech, tech
```

---

## Monitoring Architecture

### Prometheus Scrape Targets (13 active)

**System Metrics (node_exporter):**
```
lxc-docker-gateway    → 100.67.169.111:9100 ✓
lxc-traefik-gateway   → 192.168.1.110:9100  ✓
lxc-portal            → 192.168.1.108:9100  ✓
lxc-postgres          → 192.168.1.50:9100   ✓
```

**Application Metrics:**
```
prometheus            → localhost:9090      ✓
alertmanager          → alertmanager:9093   ✓
postgres              → 192.168.1.50:9187   ✓ (postgres_exporter)
grafana               → 100.120.140.105:3000 ✓
traefik               → traefik:8080        ✓
docker-gateway        → 100.67.169.111:9323 ✓ (docker metrics)
proxmox               → 100.64.220.69:9100  ✗ (not configured)
```

### Alert Rules (7 active)

**Service Health (homelab_alerts):**
1. `ServiceDown` - Any monitored service offline >2 minutes → **critical**
2. `HighMemoryUsage` - Memory usage >90% for 5 minutes → **warning**
3. `HighDiskUsage` - Disk usage >90% for 5 minutes → **warning**
4. `ContainerDown` - Critical container stopped >1 minute → **critical**

**Backup Monitoring (backup_alerts):**
5. `BackupNotRunning` - No backup run in 25+ hours → **critical**
6. `BackupFailed` - Last backup attempt failed → **critical**
7. `BackupSlowDuration` - Backup took >30 minutes → **warning**

### Alert Routing

```
Prometheus
  └─→ Alertmanager (http://172.19.0.3:9093)
       ├─→ critical alerts → telegram-forwarder → @Bobbaerbot
       └─→ warning alerts  → telegram-forwarder → @Bobbaerbot
```

---

## Network Flow

### External Access (HTTPS)

```
Internet User
  └─→ Cloudflare DNS (*.fjeld.tech)
       └─→ Public IP (NAT)
            └─→ Router (Port 443 → 192.168.1.101:443)
                 └─→ Traefik (docker-gateway)
                      ├─→ home.fjeld.tech      → homepage:3000
                      ├─→ grafana.fjeld.tech   → 100.120.140.105:3000
                      ├─→ prometheus.fjeld.tech→ prometheus:9090
                      └─→ alerts.fjeld.tech    → alertmanager:9093
```

### Internal Access (Tailscale VPN)

```
Tailscale Client
  └─→ MagicDNS (*.tahr-bass.ts.net)
       └─→ Direct encrypted connection
            └─→ Any container via 100.x.x.x IP
                 └─→ Full network access to all services
```

### Monitoring Data Flow

```
All Containers
  ├─→ node_exporter:9100 (system metrics)
  └─→ Prometheus (100.67.169.111:9090)
       ├─→ Stores time-series data
       ├─→ Evaluates alert rules
       └─→ Pushes alerts to Alertmanager
            └─→ Routes to telegram-forwarder
                 └─→ Telegram API
                      └─→ @Bobbaerbot sends to Chat ID 500505500
```

---

## Security Model

### Network Segmentation

- **Public Internet**: Only Traefik (ports 80/443) exposed
- **LAN (192.168.1.x)**: All containers communicate
- **Tailscale (100.x.x.x)**: Encrypted private access
- **Docker Networks**: Internal service isolation

### SSL/TLS

- **Provider**: Let's Encrypt (via Traefik)
- **Challenge**: DNS-01 (Cloudflare)
- **Renewal**: Automatic via Traefik
- **Coverage**: All *.fjeld.tech domains

### Container Security

- **Privilege**: All containers unprivileged (except Plex for GPU)
- **Namespaces**: Separate user namespaces
- **Nesting**: Docker/containerd enabled where needed
- **Firewall**: Host-level + container-level rules

---

## Backup Strategy

### What's Backed Up

```
/opt directory on docker-gateway (LXC 101)
  ├─ /opt/traefik         → Traefik config, SSL certs
  ├─ /opt/monitoring      → Prometheus config, alert rules
  ├─ /opt/homepage        → Homepage dashboard config
  └─ /opt/backup-scripts  → Backup scripts & configs

Excluded from backup:
  ├─ *.log, **/logs/*     → Log files
  ├─ **/cache/*           → Cache directories
  └─ **/prometheus/data/* → Prometheus time-series (regenerated)
```

### Backup Schedule

```
Daily: 2:00 AM UTC
  ├─ Stop: Docker containers (for consistency)
  ├─ Backup: Restic snapshot with tags
  ├─ Restart: Docker containers
  ├─ Prune: Keep 7 daily, 4 weekly, 6 monthly
  └─ Report: Export metrics to Prometheus
```

### Monitoring

Backup metrics available in Prometheus:
- `backup_last_run_timestamp` - Unix timestamp of last run
- `backup_last_run_success` - 1 if success, 0 if failed
- `backup_duration_seconds` - How long backup took

---

## Quick Reference

### Container Access

```bash
# SSH to Proxmox host
ssh root@<proxmox-ip>

# Enter container console
pct enter <container-id>

# Execute command in container
pct exec <container-id> -- <command>
```

### Service Management

```bash
# Docker services (LXC 101)
pct exec 101 -- docker ps
pct exec 101 -- docker compose -f /opt/monitoring/docker-compose.yml ps

# System services
pct exec <id> -- systemctl status <service>
```

### Monitoring Access

```bash
# Check Prometheus targets
curl -s http://100.67.169.111:9090/api/v1/targets | jq

# Check active alerts
curl -s http://100.67.169.111:9093/api/v2/alerts | jq

# View backup metrics
curl -s http://100.67.169.111:9100/metrics | grep backup_
```

### Log Files

```
Backups:        /var/log/restic-backup.log (LXC 101)
Docker:         docker logs <container>
System:         /var/log/syslog
```

---

## Maintenance Windows

- **Backups**: Daily 2:00-2:30 AM UTC (Traefik/Homepage offline)
- **Updates**: Manual, typically Sundays
- **Monitoring**: 24/7, alerts to Telegram

---

**Infrastructure Status**: ✅ Fully Operational
**Last Verified**: 2025-10-26
**Maintainer**: Fjeld Homelab Team
