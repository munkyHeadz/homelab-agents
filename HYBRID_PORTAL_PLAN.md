# Fjeld.tech Hybrid Portal - Tailscale + Public Strategy

## 🎯 The Smart Approach: Private by Default, Public by Choice

**Philosophy:** Keep your homelab **private and secure** via Tailscale, expose only what **needs** to be public.

---

## 🏗️ Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRIVATE (Tailscale)                           │
│                  100.x.x.x or fdxx:xxxx                          │
│                                                                   │
│  ┌──────────────────────────────────────────────────┐           │
│  │         Tailscale MagicDNS                        │           │
│  │  (Easy to remember names on your private network) │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                   │
│  grafana.tail-xxxxx.ts.net    → Grafana                         │
│  portainer.tail-xxxxx.ts.net  → Portainer                       │
│  proxmox.tail-xxxxx.ts.net    → Proxmox                         │
│  home.tail-xxxxx.ts.net       → Home Assistant                  │
│  code.tail-xxxxx.ts.net       → Code Server                     │
│  pbs.tail-xxxxx.ts.net        → Proxmox Backup                  │
│                                                                   │
│  OR custom domain via Tailscale:                                │
│  grafana.fjeld.internal       → Grafana (via Tailscale DNS)     │
│  proxmox.fjeld.internal       → Proxmox                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                              ▼

┌─────────────────────────────────────────────────────────────────┐
│                    PUBLIC (Selective)                            │
│                   fjeld.tech (Cloudflare)                        │
│                                                                   │
│  fjeld.tech                   → Professional homepage            │
│  status.fjeld.tech            → Public status page               │
│  blog.fjeld.tech              → Technical blog                   │
│  docs.fjeld.tech              → Public documentation             │
│                                                                   │
│  Optional public services:                                       │
│  share.fjeld.tech             → File sharing (if needed)         │
│  paste.fjeld.tech             → Pastebin (if useful)             │
└─────────────────────────────────────────────────────────────────┘

                              ▼

┌─────────────────────────────────────────────────────────────────┐
│              HYBRID (Tailscale Funnel)                           │
│        Selective public access to private services               │
│                                                                   │
│  demo.fjeld.tech              → Public demo Grafana dashboard    │
│                                 (read-only, via Tailscale Funnel)│
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Security Model: Zero Trust

### Private Network (Tailscale) - **Default for Everything**

**Access via:**
- Tailscale VPN on your devices (phone, laptop, etc.)
- MagicDNS for easy names
- No public exposure
- No firewall rules needed
- End-to-end encryption

**Services on Tailscale:**
```
# Management & Control
proxmox.fjeld.internal         → Proxmox VE Web UI
portainer.fjeld.internal        → Docker/Container Management
code.fjeld.internal             → VS Code Server
ssh.fjeld.internal              → SSH jump host

# Monitoring & Observability
grafana.fjeld.internal          → Full Grafana (private)
prometheus.fjeld.internal       → Prometheus
alertmanager.fjeld.internal     → Alertmanager
netdata.fjeld.internal          → Real-time monitoring
uptime.fjeld.internal           → Uptime Kuma (private)

# Backups & Storage
pbs.fjeld.internal              → Proxmox Backup Server
files.fjeld.internal            → File server
nextcloud.fjeld.internal        → Private cloud storage

# Home Automation
home.fjeld.internal             → Home Assistant
frigate.fjeld.internal          → Camera system
zigbee.fjeld.internal           → Zigbee2MQTT

# Network Services
unifi.fjeld.internal            → UniFi Controller
pihole.fjeld.internal           → Pi-hole (if you add it)
adguard.fjeld.internal          → AdGuard Home

# Development
git.fjeld.internal              → Gitea/Forgejo
ci.fjeld.internal               → CI/CD pipeline
registry.fjeld.internal         → Docker registry

# Control Panel
portal.fjeld.internal           → Your homelab control panel
api.fjeld.internal              → Private API
```

**Benefits:**
- ✅ Access from anywhere (phone, laptop, tablet)
- ✅ No port forwarding
- ✅ No public attack surface
- ✅ Easy to remember names
- ✅ Automatic HTTPS via Tailscale
- ✅ ACLs for fine-grained access control
- ✅ Works on cellular, WiFi, anywhere

---

### Public Services (Cloudflare) - **Only What's Needed**

**Truly public (no auth required):**
```
fjeld.tech                      → Professional homepage/portfolio
status.fjeld.tech               → Public status page (Uptime Kuma)
blog.fjeld.tech                 → Technical blog
docs.fjeld.tech                 → Public documentation
```

**Semi-public (optional, with auth):**
```
share.fjeld.tech                → Temporary file sharing
paste.fjeld.tech                → Code snippets/pastebin
cv.fjeld.tech                   → Interactive resume
```

**Benefits:**
- ✅ SEO for your personal brand
- ✅ Portfolio for job hunting
- ✅ Share knowledge publicly
- ✅ No sensitive data exposed
- ✅ Professional web presence

---

### Hybrid Services (Tailscale Funnel) - **Best of Both Worlds**

**Use Tailscale Funnel to selectively expose private services:**

```
demo.fjeld.tech                 → Read-only Grafana dashboard
                                  (shows off your homelab publicly)

Public URL → Tailscale Funnel → Private Grafana → Prometheus
```

**How it works:**
1. Service runs privately on Tailscale
2. Tailscale Funnel creates public HTTPS endpoint
3. Cloudflare CNAME points to Tailscale Funnel URL
4. Public users see demo, you control access
5. Easy to enable/disable

**Benefits:**
- ✅ Keep service private by default
- ✅ Expose specific dashboards/pages publicly
- ✅ No reverse proxy needed
- ✅ Automatic HTTPS
- ✅ Can revoke at any time

---

## 🎨 Recommended Split: What Goes Where

### ✅ Keep Private (Tailscale)

**Infrastructure Management:**
- Proxmox
- Portainer
- Docker registries
- SSH access
- Code-Server/IDEs

**Monitoring (Full Access):**
- Grafana (with edit permissions)
- Prometheus
- Alertmanager
- Log viewers

**Personal Services:**
- Home Assistant
- Security cameras
- File storage
- Password managers
- VPN server

**Development:**
- Git servers
- CI/CD pipelines
- Test environments

**Why:** These are **your tools**, no benefit to exposing publicly, massive security risk if exposed.

---

### ✅ Make Public (Cloudflare)

**Content:**
- Personal homepage
- Blog posts
- Technical documentation
- Resume/Portfolio

**Status/Transparency:**
- Status page (read-only)
- Public uptime metrics
- Incident history

**Sharing (Optional):**
- Temporary file sharing
- Code snippets
- Public demos

**Why:** These **benefit from being public** - SEO, portfolio, sharing knowledge.

---

### ✅ Hybrid (Tailscale Funnel + Cloudflare)

**Read-only Dashboards:**
- Public Grafana dashboard showing homelab metrics
- Network topology visualization
- Service architecture diagram

**Demo Services:**
- API documentation
- Interactive demos
- Showcase projects

**Why:** Shows off your work without compromising security.

---

## 🛠️ Implementation Plan

### Phase 1: Tailscale Foundation (Day 1-2)

**1. Enable Tailscale MagicDNS**
```bash
# Already have Tailscale, just need to enable MagicDNS
# In Tailscale admin console:
# DNS → Enable MagicDNS
# DNS → Add custom domain: fjeld.internal
```

**2. Configure Split DNS**
```
# Tailscale DNS settings:
*.fjeld.internal → Resolved via Tailscale
*.fjeld.tech → Resolved via public DNS (Cloudflare)
```

**3. Set up HTTPS for Tailscale services**
```bash
# Tailscale provides automatic HTTPS via:
# https://hostname.tail-xxxxx.ts.net
# OR via custom domain with cert provisioning
```

**4. Create DNS records for all services**
```
# In Tailscale console, assign names:
100.x.x.1 → proxmox.fjeld.internal
100.x.x.2 → portainer.fjeld.internal
100.x.x.3 → grafana.fjeld.internal
100.x.x.4 → home.fjeld.internal
# etc.
```

**Result:** Easy-to-remember URLs for all your homelab services, accessible only via Tailscale.

---

### Phase 2: Public Services (Day 3-4)

**1. Public Status Page**
```bash
# Deploy Uptime Kuma on Tailscale network
# Enable Tailscale Funnel for status.fjeld.tech
# OR deploy on RackNerd VPS for true external monitoring
```

**2. Professional Homepage**
```bash
# Simple Next.js site on RackNerd VPS
# Or Cloudflare Pages (free hosting)
# Content: About, Skills, Projects, Contact
```

**3. Blog (Optional)**
```bash
# Ghost on Tailscale + Funnel
# OR static site (Hugo/Astro) on Cloudflare Pages
```

**Result:** Professional web presence without exposing infrastructure.

---

### Phase 3: Homelab Control Portal (Day 5-7)

**Build a private web portal (Tailscale only):**

**URL:** `portal.fjeld.internal`

**Features:**
- Dashboard showing all services
- Quick links to all Tailscale services
- Embedded Grafana dashboards
- Service health checks
- Quick actions (restart services, etc.)
- Mobile-friendly PWA

**Tech Stack:**
```
Frontend: Next.js + shadcn/ui
Backend: FastAPI (connects to existing agents)
Auth: Tailscale Auth (SSO via your Tailscale account!)
Deployment: Docker on Portainer LXC
Access: Tailscale only
```

**Result:** Beautiful control panel, accessible from phone/laptop anywhere via Tailscale.

---

### Phase 4: Selective Public Exposure (Day 8+)

**Use Tailscale Funnel for demo dashboards:**

```bash
# Example: Public Grafana dashboard
tailscale funnel --bg --https=443 \
  --set-path=/public-dashboard \
  http://localhost:3000

# Create Cloudflare CNAME:
demo.fjeld.tech → funnel-xxx.ts.net
```

**What to expose:**
- Read-only Grafana dashboard
- Service topology map
- Public API documentation
- Showcase projects

**Result:** Show off your homelab safely.

---

## 🔐 Tailscale ACLs: Fine-Grained Control

**Example ACL policy:**

```json
{
  "acls": [
    // Your phone/laptop can access everything
    {
      "action": "accept",
      "src": ["you@example.com"],
      "dst": ["*:*"]
    },

    // Friends can only see status page
    {
      "action": "accept",
      "src": ["group:friends"],
      "dst": ["uptime.fjeld.internal:443"]
    },

    // Family can access Home Assistant
    {
      "action": "accept",
      "src": ["group:family"],
      "dst": ["home.fjeld.internal:8123"]
    },

    // Block everything else
    {
      "action": "deny",
      "src": ["*"],
      "dst": ["*:*"]
    }
  ]
}
```

**Benefits:**
- Share specific services with specific people
- No VPN clients to configure
- Just send them a Tailscale invite
- Revoke access anytime

---

## 📱 Mobile Access Strategy

### Your Phone Setup

**Install Tailscale app → Access everything:**

```
Safari/Chrome → grafana.fjeld.internal
             → portainer.fjeld.internal
             → home.fjeld.internal
             → portal.fjeld.internal (your control panel)
```

**Bookmark all your services:**
- Add to home screen as PWA
- Looks like native apps
- Works over cellular + WiFi
- Automatic HTTPS

**Telegram bot (existing) + Portal (new):**
- Quick actions → Telegram bot
- Detailed views → Portal via Tailscale
- Alerts → Telegram
- Monitoring → Portal

---

## 🌐 DNS Strategy

### Split-Horizon DNS

**Tailscale DNS (Private):**
```
*.fjeld.internal → Tailscale MagicDNS
grafana.fjeld.internal → 100.x.x.3
proxmox.fjeld.internal → 100.x.x.1
```

**Cloudflare DNS (Public):**
```
fjeld.tech → Your homepage
status.fjeld.tech → Status page
blog.fjeld.tech → Blog
*.fjeld.tech → Other public services
```

**Result:**
- Clean separation
- `.internal` = always private
- `.tech` = public or hybrid
- No confusion

---

## 💡 The Portal Architecture

### Private Control Panel (`portal.fjeld.internal`)

**Dashboard View:**
```
┌─────────────────────────────────────────────────────┐
│  Fjeld Homelab Portal                    [Profile]  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ⚡ Quick Actions                                    │
│  [Restart VM 101] [View Alerts] [Run Backup]        │
│                                                      │
│  📊 System Status                                    │
│  CPU: 🟢 23%  Memory: 🟡 78%  Disk: 🟢 45%          │
│                                                      │
│  🔗 Quick Links                                      │
│  [Grafana] [Portainer] [Proxmox] [Home Assistant]   │
│                                                      │
│  🚨 Recent Alerts (3)                                │
│  ⚠️ High memory on LXC 104                           │
│  ✅ Backup completed successfully                    │
│  ℹ️ System update available                          │
│                                                      │
│  📈 Embedded Grafana Dashboard                       │
│  [Live metrics chart]                                │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Features:**
- SSO via Tailscale (no separate login!)
- Mobile-responsive
- Installable PWA
- Real-time updates (WebSocket)
- Quick access to all services
- Integrates with existing Telegram bot backend

---

## 🎯 Recommended Services Split

### Must Have on Tailscale (Private)

| Service | URL | Why Private |
|---------|-----|-------------|
| Proxmox | proxmox.fjeld.internal | Full infrastructure control |
| Portainer | portainer.fjeld.internal | Docker management |
| Grafana | grafana.fjeld.internal | Full monitoring access |
| Prometheus | prometheus.fjeld.internal | Metrics data |
| Home Assistant | home.fjeld.internal | Home control & cameras |
| Code-Server | code.fjeld.internal | Development environment |
| PBS | pbs.fjeld.internal | Backup management |
| Control Portal | portal.fjeld.internal | Your custom dashboard |
| SSH Jump | ssh.fjeld.internal | Shell access |

### Nice to Have Public

| Service | URL | Why Public |
|---------|-----|------------|
| Homepage | fjeld.tech | Portfolio/resume |
| Status Page | status.fjeld.tech | Transparency/showcase |
| Blog | blog.fjeld.tech | Knowledge sharing |
| Docs | docs.fjeld.tech | Technical writing |

### Optional Hybrid (Tailscale Funnel)

| Service | URL | Why Hybrid |
|---------|-----|-----------|
| Demo Dashboard | demo.fjeld.tech | Show off homelab safely |
| API Docs | api.fjeld.tech | Public documentation |
| Project Showcase | projects.fjeld.tech | Portfolio pieces |

---

## 💰 Cost Comparison

### Option 1: Pure Tailscale (Recommended)
```
Tailscale Free: $0/month (up to 3 users, 100 devices)
Cloudflare DNS: $0/month (just for public website)
Domain: $12/year ≈ $1/month

Total: $1/month
```

### Option 2: Tailscale + Funnel
```
Tailscale Free: $0/month
Funnel: $0/month (included in free tier!)
Cloudflare: $0/month

Total: $1/month
```

### Option 3: Full Public (Previous Plan)
```
Cloudflare Tunnel: $0/month
Auth Service: $0/month (self-hosted)
BUT: Higher security risk, more maintenance

Total: $1/month (but riskier)
```

**Winner: Tailscale approach is both cheaper AND more secure!** 🎉

---

## 🚀 Quick Start: Tailscale MVP (Today!)

### 30-Minute Setup

**Step 1: Enable MagicDNS (5 min)**
```bash
# Tailscale admin console → DNS → Enable MagicDNS
# Now all your devices have automatic DNS names
```

**Step 2: Access your services (5 min)**
```bash
# From your phone/laptop with Tailscale:
http://100.x.x.x:9090  # Old way (IP)
http://hostname.tail-xxx.ts.net  # New way (MagicDNS)
```

**Step 3: Set up custom domain (10 min)**
```bash
# Tailscale admin → DNS → Custom domain
# Add: fjeld.internal
# Assign names to your machines
```

**Step 4: Bookmark services (5 min)**
```bash
# Add to phone home screen:
- grafana.fjeld.internal
- portainer.fjeld.internal
- home.fjeld.internal
```

**Step 5: Enable HTTPS (5 min)**
```bash
# Tailscale automatically provides HTTPS certs
# All your .ts.net URLs already have HTTPS!
```

**Result:** Clean, easy-to-remember URLs for everything, accessible anywhere!

---

## 🎨 The Control Portal (Your Next Build)

### Scope: Single-Page Dashboard

**What it does:**
- Shows status of all services
- Quick links to all Tailscale URLs
- Embedded Grafana dashboards
- Recent alerts from Telegram bot
- Quick actions (restart VMs, etc.)

**What it doesn't do:**
- Replace Telegram bot (they complement!)
- Duplicate existing UIs (just links to them)
- Overcomplicate things

**Why build it:**
- One place to see everything
- Mobile-friendly
- Bookmarkable on phone
- Faster than Telegram for browsing
- Learning project (Next.js + FastAPI)

**Timeline:** 1-2 days to build MVP

---

## 📊 Decision Matrix

| Approach | Security | Convenience | Cost | Maintenance |
|----------|----------|-------------|------|-------------|
| **Pure Tailscale** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $0 | ⭐⭐⭐⭐⭐ |
| **Hybrid (TS + Public)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $0 | ⭐⭐⭐⭐ |
| **Full Public** | ⭐⭐ | ⭐⭐⭐⭐⭐ | $0 | ⭐⭐⭐ |

**Recommendation: Hybrid approach!**
- Tailscale for everything private (99% of services)
- Public only for content (blog, homepage, status)
- Tailscale Funnel for selective demos

---

## 🎯 My Recommendation

### Week 1: Foundation
1. **Enable Tailscale MagicDNS** (30 min)
2. **Set up custom domain: fjeld.internal** (1 hour)
3. **Configure all service names** (2 hours)
4. **Bookmark on all devices** (30 min)

### Week 2: Public Presence
5. **Deploy status page on status.fjeld.tech** (2 hours)
6. **Create homepage on fjeld.tech** (1 day)
7. **Optional: Start blog** (1 day)

### Week 3: Control Portal
8. **Build private portal dashboard** (2 days)
9. **Deploy on portal.fjeld.internal** (1 day)
10. **Install as PWA on phone** (10 min)

### Week 4: Polish
11. **Set up Tailscale Funnel for demo** (2 hours)
12. **Configure ACLs for sharing** (1 hour)
13. **Document everything in docs.fjeld.tech** (ongoing)

---

## 🎁 What You Get

**Private Network:**
- ✅ Easy names for all services (no IPs!)
- ✅ Access from anywhere (phone, laptop)
- ✅ Automatic HTTPS
- ✅ No port forwarding
- ✅ Zero trust security
- ✅ Share with family/friends (optional)

**Public Presence:**
- ✅ Professional homepage
- ✅ Technical blog
- ✅ Status page
- ✅ Portfolio material

**Best of Both:**
- ✅ Security of private network
- ✅ Convenience of public access
- ✅ Flexibility to expose what you want
- ✅ Easy to change your mind

---

## 🤔 Next Steps

**What sounds good?**

1. **Start with Tailscale setup** (30 min, I'll guide you)
2. **Build the control portal** (1-2 days)
3. **Set up public homepage** (1 day)
4. **Hybrid: Do all three!**

**I can start implementing any of these right now!**

Which approach do you prefer? Pure Tailscale? Hybrid? Something else?
