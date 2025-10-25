# Fjeld.tech Homelab Infrastructure Map

## 🎯 Current State (October 2025)

### Tailscale Network

**MagicDNS:** ✅ Enabled (`tahr-bass.ts.net`)
**Custom Domain:** ❌ Not configured (target: `fjeld.internal`)

### Active Tailscale Devices

| Device Name | Tailscale IP | Local IP | MagicDNS | Status | Purpose |
|-------------|--------------|----------|----------|--------|---------|
| fjeld | 100.64.220.69 | 192.168.1.99 | fjeld.tahr-bass.ts.net | Active | Proxmox host |
| portfolio | 100.111.140.125 | 192.168.1.141 | portfolio.tahr-bass.ts.net | Active | Portfolio website (nginx) |
| racknerd | 100.88.247.93 | 107.172.145.203 | racknerd.tahr-bass.ts.net | Active | VPS (nginx) |
| adguard | 100.94.4.16 | - | adguard.tahr-bass.ts.net | Idle | AdGuard DNS (exit node) |
| arr | 100.122.192.4 | - | arr.tahr-bass.ts.net | Active | Media automation |
| plex | 100.78.95.63 | - | plex.tahr-bass.ts.net | Active | Media server |
| rustdeskserver | 100.113.36.19 | - | rustdeskserver.tahr-bass.ts.net | Active | Remote desktop |
| unifios | 100.71.131.95 | - | unifios.tahr-bass.ts.net | Active | UniFi controller |
| samsung-sm-g990b | 100.75.23.13 | - | - | Active | Phone |
| ffxiv | 100.114.151.95 | 192.168.1.156 | ffxiv.tahr-bass.ts.net | Active | Gaming PC |

### Offline Devices
- caddy, claude-ai, ffxiv-1, kali, kalivm, n8n, nginx, nvidia-shield-android-tv, tinyprox, wazuh

---

## 📍 Key Infrastructure Services

### Proxmox Host (fjeld - 192.168.1.99)
- **Role:** Hypervisor for all LXC containers and VMs
- **Tailscale IP:** 100.64.220.69
- **Current access:** http://192.168.1.99:8006
- **Target DNS:** proxmox.fjeld.internal

### LXC Containers on Proxmox

| Container ID | Service | Local IP | Port | Current Access | Target DNS |
|--------------|---------|----------|------|----------------|------------|
| 104 | Telegram Bot + Prometheus | 192.168.1.104 | 9090 | http://192.168.1.104:9090 | prometheus.fjeld.internal |
| 105 | Grafana | 192.168.1.105 | 3000 | http://192.168.1.105:3000 | grafana.fjeld.internal |
| 141 | Portfolio (nginx) | 192.168.1.141 | 80 | http://192.168.1.141 | portfolio.fjeld.internal |
| ? | Portainer | ? | 9443 | ? | portainer.fjeld.internal |

**Note:** Currently, LXC containers are NOT on Tailscale - only the host is. Services are accessed via local IPs.

---

## 🎯 Target Architecture: Hybrid DNS Strategy

### Option A: Proxy Through Host (Quick)
**Concept:** Access LXC services via Proxmox host's Tailscale connection

```
Your Device → Tailscale → fjeld (100.64.220.69) → LXC containers (192.168.1.x)
```

**Implementation:**
- Set up reverse proxy on Proxmox host
- Route fjeld.internal subdomains to local containers
- Example: grafana.fjeld.internal → 192.168.1.105:3000

**Pros:**
- ✅ Quick to implement
- ✅ Only one Tailscale connection needed
- ✅ Works immediately

**Cons:**
- ❌ Single point of failure
- ❌ All traffic goes through host

---

### Option B: Tailscale in Each Container (Recommended)
**Concept:** Install Tailscale directly in each LXC container

```
Your Device → Tailscale → LXC Container (direct)
```

**Implementation:**
- Install Tailscale in each key container
- Each container gets its own Tailscale IP
- Each container gets its own DNS name

**Pros:**
- ✅ Direct connections
- ✅ Better performance
- ✅ No single point of failure
- ✅ Easier to manage

**Cons:**
- ❌ More Tailscale devices
- ❌ Requires Tailscale in each container

---

## 🗺️ Recommended DNS Naming Scheme

### Private Services (Tailscale - fjeld.internal)

**Infrastructure Management:**
```
proxmox.fjeld.internal          → Proxmox host (192.168.1.99)
portainer.fjeld.internal        → Portainer UI
```

**Monitoring & Observability:**
```
grafana.fjeld.internal          → Grafana (192.168.1.105)
prometheus.fjeld.internal       → Prometheus (192.168.1.104)
netdata.fjeld.internal          → Real-time monitoring
uptime.fjeld.internal           → Uptime Kuma (private)
```

**Home Automation:**
```
home.fjeld.internal             → Home Assistant
adguard.fjeld.internal          → AdGuard Home
unifi.fjeld.internal            → UniFi controller
```

**Media & Entertainment:**
```
plex.fjeld.internal             → Plex server
arr.fjeld.internal              → *arr stack
```

**Development & Tools:**
```
code.fjeld.internal             → VS Code Server
git.fjeld.internal              → Gitea/Forgejo
api.fjeld.internal              → Private API
```

**Control Panel (New!):**
```
portal.fjeld.internal           → Your custom homelab portal
```

---

### Public Services (Cloudflare - fjeld.tech)

**Content & Portfolio:**
```
fjeld.tech                      → Professional homepage
blog.fjeld.tech                 → Technical blog
docs.fjeld.tech                 → Documentation
cv.fjeld.tech                   → Resume/CV
```

**Status & Monitoring:**
```
status.fjeld.tech               → Public status page
```

---

### Hybrid Services (Tailscale Funnel)

**Public Demos:**
```
demo.fjeld.tech                 → Read-only Grafana dashboard
api-docs.fjeld.tech             → Public API documentation
```

---

## 🚀 Implementation Roadmap

### Phase 1: Enable Custom Domain (Today)
**Time: 30 minutes**

1. **Go to Tailscale Admin Console**
   - https://login.tailscale.com/admin
   - Navigate to DNS settings

2. **Enable custom domain:**
   - Add domain: `fjeld.internal`
   - This replaces `tahr-bass.ts.net` with your custom domain

3. **Verify:**
   ```bash
   # Test from any Tailscale device:
   ping fjeld.fjeld.internal
   curl http://fjeld.fjeld.internal
   ```

---

### Phase 2: Proxy LXC Services Through Host (Day 1)
**Time: 2-3 hours**

**Option: Use Nginx or Caddy on Proxmox host**

**Install Caddy on Proxmox host:**
```bash
# On fjeld (192.168.1.99)
apt install -y caddy

# Configure Caddyfile
cat > /etc/caddy/Caddyfile << 'EOF'
# Grafana
grafana.fjeld.internal {
    reverse_proxy 192.168.1.105:3000
}

# Prometheus
prometheus.fjeld.internal {
    reverse_proxy 192.168.1.104:9090
}

# Proxmox
proxmox.fjeld.internal {
    reverse_proxy 192.168.1.99:8006
}

# Portfolio
portfolio.fjeld.internal {
    reverse_proxy 192.168.1.141:80
}

# Control Portal (future)
portal.fjeld.internal {
    reverse_proxy 192.168.1.xxx:3000
}
EOF

systemctl enable caddy
systemctl start caddy
```

**Test access:**
```bash
# From any Tailscale device:
curl http://grafana.fjeld.internal
curl http://prometheus.fjeld.internal
```

---

### Phase 3: Build Control Portal (Day 2-3)
**Time: 1-2 days**

**Create a new LXC container for the portal:**
- Container ID: 106 (or next available)
- OS: Ubuntu 24.04
- Resources: 2 CPU, 2GB RAM, 20GB disk
- IP: 192.168.1.106

**Tech Stack:**
- Frontend: Next.js 14 + shadcn/ui
- Backend: FastAPI (reuse existing agents)
- Database: PostgreSQL (existing)
- Deployment: Docker in LXC

**Features:**
- Dashboard with service status
- Quick links to all Tailscale services
- Embedded Grafana dashboards
- Recent alerts from Telegram bot
- Quick actions (restart VMs, etc.)
- Mobile-responsive PWA

**Access:**
```
portal.fjeld.internal → 192.168.1.106:3000 (via Caddy proxy)
```

---

### Phase 4: Public Status Page (Day 4)
**Time: 2-3 hours**

**Deploy Uptime Kuma publicly:**

**Option A: On RackNerd VPS**
```bash
# SSH to racknerd (100.88.247.93)
docker run -d \
  --name=uptime-kuma \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:1
```

**Configure Cloudflare DNS:**
```
status.fjeld.tech → CNAME → racknerd VPS IP
```

**Option B: Tailscale Funnel (Alternative)**
```bash
# Run Uptime Kuma on Tailscale network
# Expose via Funnel:
tailscale funnel --bg 3001
```

---

### Phase 5: Homepage & Blog (Week 2)
**Time: 1-2 days**

**Simple professional homepage:**
- Deploy on Cloudflare Pages (free)
- Or use racknerd VPS
- Static site (Next.js, Astro, or Hugo)

**Content:**
- About you
- Skills & technologies
- Homelab showcase
- Blog section
- Contact info

---

## 📊 Current vs Target State

### Current State (Before Implementation)
```
Services access:
  Grafana: http://192.168.1.105:3000 (local network only)
  Prometheus: http://192.168.1.104:9090 (local network only)
  Proxmox: http://192.168.1.99:8006 (local network only)

Remote access:
  Via Telegram bot (commands only)
  Via Tailscale to host, then local IPs

DNS:
  All services use IP addresses
  No easy-to-remember names
```

### Target State (After Implementation)
```
Private services (Tailscale):
  Grafana: https://grafana.fjeld.internal (anywhere via Tailscale)
  Prometheus: https://prometheus.fjeld.internal
  Proxmox: https://proxmox.fjeld.internal
  Portal: https://portal.fjeld.internal (new!)

Public services:
  Homepage: https://fjeld.tech (Cloudflare)
  Status: https://status.fjeld.tech
  Blog: https://blog.fjeld.tech

Hybrid (Tailscale Funnel):
  Demo: https://demo.fjeld.tech (read-only Grafana)

Access:
  Phone/laptop → Tailscale app → Easy DNS names
  Bookmarkable URLs
  No IP addresses to remember
  Works from anywhere (cellular, WiFi, etc.)
```

---

## 🔧 Quick Start Commands

### Check Tailscale Status
```bash
tailscale status
tailscale status --json | jq '.MagicDNSSuffix'
```

### Test Service Connectivity
```bash
# Via Tailscale IP
curl http://100.64.220.69:8006  # Proxmox

# Via MagicDNS (current)
curl http://fjeld.tahr-bass.ts.net:8006

# Via custom domain (after setup)
curl http://proxmox.fjeld.internal
```

### Access from Phone
```
1. Install Tailscale app
2. Connect to network
3. Open Safari/Chrome
4. Go to: grafana.fjeld.internal
5. Bookmark to home screen
```

---

## 🎯 Next Steps

**Immediate (Today):**
1. ✅ Verify Tailscale setup (DONE)
2. 📝 Create infrastructure map (DONE)
3. ⏭️ Enable custom domain (fjeld.internal) in Tailscale console
4. ⏭️ Set up Caddy proxy on Proxmox host
5. ⏭️ Test access to services via new DNS names

**This Week:**
6. Build control portal (portal.fjeld.internal)
7. Deploy public status page (status.fjeld.tech)
8. Create simple homepage (fjeld.tech)

**Next Week:**
9. Add more services to DNS map
10. Set up Tailscale Funnel for demo dashboard
11. Create documentation site

---

## 📱 Mobile Access Vision

**Before:**
```
Open Telegram → Type /metrics → Wait for response
Or remember: http://192.168.1.105:3000
```

**After:**
```
Open phone → Tap "Homelab Portal" PWA icon → See dashboard
Or type: grafana.fjeld.internal → Instant access
All services bookmarked with easy names
Works from coffee shop, work, anywhere
```

---

**Status:** Infrastructure mapped, ready for implementation!
**Next Action:** Enable custom domain `fjeld.internal` in Tailscale console
