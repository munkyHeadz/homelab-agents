# Homepage Dashboard - Better Alternative

## 🎯 Why Homepage is Better

You're right - instead of building a custom portal, we should use **Homepage** (https://gethomepage.dev/)!

### Custom Portal (what I built)
- ❌ Basic static HTML
- ❌ No service integrations
- ❌ No status checking
- ❌ No widgets
- ❌ Manual updates needed

### Homepage Dashboard
- ✅ **Beautiful, modern UI**
- ✅ **Service integrations** (Proxmox, Plex, UniFi, etc.)
- ✅ **Real-time status** checks
- ✅ **Widgets** (weather, calendar, stats)
- ✅ **Resource monitoring** (CPU, RAM, disk)
- ✅ **Docker integration**
- ✅ **API support** for many services
- ✅ **Customizable** with YAML
- ✅ **Active development** and community

---

## 🚀 Homepage Features

### Service Integrations
Homepage can show real data from:
- **Proxmox VE** - VM/LXC status, resource usage
- **Plex** - Currently watching, library stats
- **AdGuard** - Blocked queries, stats
- **UniFi** - Network stats, clients
- **Prometheus** - Custom metrics
- **Grafana** - Embed dashboards
- **Docker** - Container status
- **And 100+ more services**

### Widgets
- System resources (CPU, RAM, disk)
- Weather
- Calendar
- Search (Google, DuckDuckGo)
- Bookmarks
- Custom iframes

### Status Monitoring
- HTTP/HTTPS health checks
- Response time tracking
- Automatic status indicators
- Ping monitoring

---

## 🏗️ Deployment Plan

### Replace Custom Portal with Homepage

**Option 1: Deploy in Existing Portal Container (LXC 108)**
```bash
# Stop current portal
sudo pct exec 108 -- systemctl stop portal

# Install Docker
sudo pct exec 108 -- apt install -y docker.io

# Deploy Homepage
sudo pct exec 108 -- docker run -d \
  --name=homepage \
  -p 3000:3000 \
  -v /opt/homepage/config:/app/config \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --restart unless-stopped \
  ghcr.io/gethomepage/homepage:latest
```

**Option 2: New Docker Compose Stack**
```yaml
# /opt/homepage/docker-compose.yml
version: "3.3"
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    container_name: homepage
    ports:
      - 3000:3000
    volumes:
      - /opt/homepage/config:/app/config
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
```

---

## 📝 Configuration Examples

### services.yaml
```yaml
---
# Monitoring
- Monitoring:
    - Grafana:
        icon: grafana.png
        href: https://grafana.tahr-bass.ts.net
        description: Dashboards & Visualization
        widget:
          type: grafana
          url: http://grafana:3000
          username: admin
          password: {{HOMEPAGE_VAR_GRAFANA_PASSWORD}}

    - Prometheus:
        icon: prometheus.png
        href: https://prometheus.tahr-bass.ts.net
        description: Metrics Collection
        ping: prometheus:9090

# Infrastructure
- Infrastructure:
    - Proxmox:
        icon: proxmox.png
        href: https://fjeld.tahr-bass.ts.net:8006
        description: Hypervisor
        widget:
          type: proxmox
          url: https://192.168.1.99:8006
          username: {{HOMEPAGE_VAR_PROXMOX_USER}}
          password: {{HOMEPAGE_VAR_PROXMOX_PASS}}

    - PostgreSQL:
        icon: postgres.png
        href: postgresql://postgres:5432
        description: Database
        widget:
          type: postgres
          url: postgres://postgres:5432

# Media
- Media:
    - Plex:
        icon: plex.png
        href: https://plex.tahr-bass.ts.net
        description: Media Server
        widget:
          type: plex
          url: http://plex:32400
          key: {{HOMEPAGE_VAR_PLEX_TOKEN}}

# Network
- Network:
    - AdGuard:
        icon: adguard.png
        href: https://adguard.tahr-bass.ts.net
        description: DNS & Ad Blocking
        widget:
          type: adguard
          url: http://adguard
          username: {{HOMEPAGE_VAR_ADGUARD_USER}}
          password: {{HOMEPAGE_VAR_ADGUARD_PASS}}

    - UniFi:
        icon: unifi.png
        href: https://unifios.tahr-bass.ts.net
        description: Network Controller
        widget:
          type: unifi
          url: https://unifios
          username: {{HOMEPAGE_VAR_UNIFI_USER}}
          password: {{HOMEPAGE_VAR_UNIFI_PASS}}
```

### widgets.yaml
```yaml
---
# System Resources
- resources:
    cpu: true
    memory: true
    disk: /

# Search
- search:
    provider: google
    target: _blank

# Date/Time
- datetime:
    text_size: xl
    format:
      dateStyle: long
      timeStyle: short
```

### docker.yaml (if using Docker)
```yaml
---
# Show Docker containers
my-docker:
  socket: /var/run/docker.sock
```

---

## 🎨 Theme & Customization

### settings.yaml
```yaml
---
title: Fjeld Homelab
background: https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe
backgroundOpacity: 0.3
theme: dark
color: slate
layout:
  Monitoring:
    style: row
    columns: 2
  Infrastructure:
    style: row
    columns: 2
```

---

## 🔗 Integration Examples

### Proxmox Integration
Shows:
- CPU usage
- Memory usage
- Number of VMs/LXCs
- Running/stopped status

### Plex Integration
Shows:
- Currently watching
- Total library size
- Recent additions

### AdGuard Integration
Shows:
- Queries blocked today
- Percentage blocked
- Active filters

---

## 🚀 Quick Deployment

Want me to:

1. **Replace the custom portal with Homepage?**
   - Redeploy LXC 108 with Homepage
   - Configure all your services
   - Set up integrations

2. **Keep both?**
   - Custom portal as backup
   - Homepage as primary dashboard
   - Different ports (3000 vs 3001)

3. **Start fresh in new container?**
   - Create LXC 109 for Homepage
   - Leave custom portal running
   - Compare both

---

## 💡 My Recommendation

**Deploy Homepage - it's vastly superior!**

**Pros:**
- Professional, polished interface
- Real-time service monitoring
- Rich integrations
- Active community
- Regular updates
- YAML configuration (easy to manage)

**Steps:**
1. Deploy Homepage in portal container
2. Configure services with integrations
3. Enable widgets for system resources
4. Set up Tailscale HTTPS
5. Access at https://portal.tahr-bass.ts.net

**Result:**
```
Before: Basic static HTML list
After: Professional dashboard with live stats!
```

---

## 🎯 What Homepage Will Show

**Grafana widget:**
- Current alerts
- Dashboard list
- Real-time stats

**Proxmox widget:**
- VM/LXC status (running/stopped)
- CPU/RAM usage per node
- Storage usage

**Plex widget:**
- What's currently streaming
- Library counts (movies, shows)
- Recent additions

**System Resources widget:**
- CPU usage graph
- Memory usage
- Disk space

**AdGuard widget:**
- Queries today
- Blocked percentage
- Top blocked domains

---

**Want me to deploy Homepage right now?** 🚀

It'll be way better than the simple portal I built!
