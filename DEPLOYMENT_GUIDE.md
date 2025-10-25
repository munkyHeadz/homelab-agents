# Fjeld.tech Homelab Deployment Guide

## 🎯 Architecture Principle: Keep Proxmox Host Clean

**Important:** NEVER install services directly on the Proxmox host. Always use LXC containers for isolation, maintainability, and easy backups.

---

## 📋 Implementation Steps

### Step 1: Enable Tailscale Custom Domain (Manual - 5 min)

**You need to do this manually in the Tailscale admin console:**

1. Go to https://login.tailscale.com/admin/dns
2. Under "MagicDNS", ensure it's enabled (should already be enabled)
3. Under "Custom domain", add: `fjeld.internal`
4. Click "Save"

**What this does:**
- Changes DNS from `hostname.tahr-bass.ts.net` → `hostname.fjeld.internal`
- Makes all your services have clean, easy-to-remember names

**Verify:**
```bash
# From any Tailscale device:
tailscale status --json | jq '.MagicDNSSuffix'
# Should show: "fjeld.internal"

# Test ping:
ping fjeld.fjeld.internal
```

---

### Step 2: Create Reverse Proxy LXC Container (30 min)

**Create a new LXC container for Caddy reverse proxy:**

#### Option A: Via Proxmox Web UI

1. Go to Proxmox UI: http://192.168.1.99:8006
2. Click "Create CT"
3. Configure:
   - **CT ID:** 110 (or next available)
   - **Hostname:** `gateway`
   - **Password:** (set a secure password)
   - **Template:** Ubuntu 24.04 (or Debian 12)
   - **Disk:** 8 GB
   - **CPU:** 2 cores
   - **Memory:** 1024 MB
   - **Network:**
     - Bridge: vmbr0
     - IPv4: Static - 192.168.1.110/24
     - Gateway: 192.168.1.1
   - **DNS:** 192.168.1.1
4. Start the container

#### Option B: Via Command Line

```bash
# On Proxmox host (fjeld)
sudo pct create 110 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname gateway \
  --memory 1024 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.110/24,gw=192.168.1.1 \
  --rootfs local-lvm:8 \
  --password \
  --start 1

# Start the container
sudo pct start 110
```

---

### Step 3: Install Tailscale in Gateway Container (10 min)

**Enter the container:**
```bash
# From Proxmox host:
sudo pct exec 110 -- bash
```

**Inside the container, install Tailscale:**
```bash
# Update system
apt update && apt upgrade -y

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale
tailscale up

# Copy the auth link and open in browser to authorize
# This will add "gateway" to your Tailscale network
```

**Verify Tailscale is working:**
```bash
tailscale status
tailscale ip -4
# Should show a 100.x.x.x IP
```

**Exit the container:**
```bash
exit
```

---

### Step 4: Install and Configure Caddy (20 min)

**Enter the container again:**
```bash
sudo pct exec 110 -- bash
```

**Install Caddy:**
```bash
# Add Caddy repository
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list

# Install Caddy
apt update
apt install -y caddy

# Verify installation
caddy version
```

**Create Caddyfile configuration:**
```bash
cat > /etc/caddy/Caddyfile << 'EOF'
# Fjeld.tech Homelab Reverse Proxy
# This routes Tailscale DNS names to internal services

# Global options
{
    # Disable automatic HTTPS (Tailscale provides it)
    auto_https off
}

# Grafana
http://grafana.fjeld.internal {
    reverse_proxy 192.168.1.105:3000
}

# Prometheus
http://prometheus.fjeld.internal {
    reverse_proxy 192.168.1.104:9090
}

# Proxmox (via Tailscale host IP)
http://proxmox.fjeld.internal {
    reverse_proxy https://192.168.1.99:8006 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}

# Portfolio
http://portfolio.fjeld.internal {
    reverse_proxy 192.168.1.141:80
}

# AdGuard Home
http://adguard.fjeld.internal {
    reverse_proxy 100.94.4.16:80
}

# Plex
http://plex.fjeld.internal {
    reverse_proxy 100.78.95.63:32400
}

# UniFi Controller
http://unifi.fjeld.internal {
    reverse_proxy 100.71.131.95:8443 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}

# Future: Control Portal
http://portal.fjeld.internal {
    reverse_proxy 192.168.1.106:3000
}

# Catch-all for undefined services
http://:80 {
    respond "Fjeld Homelab Gateway - Service not configured" 404
}
EOF
```

**Test and reload Caddy:**
```bash
# Test configuration
caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
systemctl reload caddy

# Check status
systemctl status caddy

# Check logs
journalctl -u caddy -f
```

**Exit container:**
```bash
exit
```

---

### Step 5: Configure Tailscale DNS for Gateway (10 min)

**Now we need to tell Tailscale that gateway.fjeld.internal should handle all *.fjeld.internal requests**

**Option A: DNS Split in Tailscale Console (Recommended)**

1. Go to https://login.tailscale.com/admin/dns
2. Under "Nameservers", add a nameserver entry:
   - **Restricted to:** `fjeld.internal`
   - **Nameserver:** `100.x.x.x` (gateway's Tailscale IP)

**Option B: Use Tailscale DNS Records**

Since Tailscale MagicDNS will automatically resolve `gateway.fjeld.internal` to the gateway container's Tailscale IP, users can access services through the gateway.

**Actually, simpler approach:**

The gateway container with Caddy will listen on its Tailscale IP. When you visit `grafana.fjeld.internal`, you'll need to ensure it resolves to the gateway's Tailscale IP.

**Let me correct the approach:**

---

### 🔄 REVISED Step 5: Configure DNS Properly (15 min)

**The issue:** We want `grafana.fjeld.internal` to point to the gateway container, but Tailscale's MagicDNS will try to resolve `grafana` as a hostname.

**Solution: Use Tailscale DNS records in the admin console**

1. Go to https://login.tailscale.com/admin/dns
2. Under "DNS", add DNS records:
   ```
   grafana.fjeld.internal     → Gateway's Tailscale IP (100.x.x.x)
   prometheus.fjeld.internal  → Gateway's Tailscale IP
   proxmox.fjeld.internal     → Gateway's Tailscale IP
   portal.fjeld.internal      → Gateway's Tailscale IP
   adguard.fjeld.internal     → 100.94.4.16 (direct)
   plex.fjeld.internal        → 100.78.95.63 (direct)
   unifi.fjeld.internal       → 100.71.131.95 (direct)
   ```

**For services already on Tailscale:** Point DNS directly to them
**For services NOT on Tailscale (LXC containers):** Point DNS to gateway, which proxies

---

### Alternative Simpler Approach: Subdomain Per Service Container

**Actually, the cleanest approach:**

1. **Install Tailscale in EVERY key LXC container** (Grafana, Prometheus, Portal, etc.)
2. **Let Tailscale MagicDNS automatically create hostnames**
3. **Rename containers to match desired DNS names**

**For example:**
```bash
# Rename LXC 104 → "prometheus"
pct set 104 --hostname prometheus

# Rename LXC 105 → "grafana"
pct set 105 --hostname grafana

# Inside each container, install Tailscale
pct exec 104 -- bash -c "curl -fsSL https://tailscale.com/install.sh | sh && tailscale up"
pct exec 105 -- bash -c "curl -fsSL https://tailscale.com/install.sh | sh && tailscale up"
```

**Then Tailscale MagicDNS automatically creates:**
- `prometheus.fjeld.internal` → LXC 104 directly
- `grafana.fjeld.internal` → LXC 105 directly

**This is MUCH simpler and more scalable!**

---

## 🎯 Recommended Architecture: Tailscale in Every Container

### Why This is Better:

✅ **Direct connections** - No reverse proxy bottleneck
✅ **Automatic DNS** - MagicDNS creates names automatically
✅ **Better security** - Each service is independently secured
✅ **Easier to manage** - No complex proxy configuration
✅ **More resilient** - No single point of failure

### Implementation:

**For each service you want accessible via Tailscale:**

1. Install Tailscale in the container
2. Set hostname to desired DNS name
3. Join to Tailscale network
4. Done! MagicDNS handles the rest

**Example for Grafana (LXC 105):**
```bash
# Set hostname
sudo pct set 105 --hostname grafana

# Install Tailscale in container
sudo pct exec 105 -- bash -c "curl -fsSL https://tailscale.com/install.sh | sh"

# Start Tailscale (will show auth link)
sudo pct exec 105 -- tailscale up

# Verify
sudo pct exec 105 -- tailscale status
```

**Repeat for:**
- LXC 104 (prometheus)
- LXC 141 (portfolio)
- Future LXC 106 (portal)

**For Proxmox host:**
- Already has Tailscale (fjeld.fjeld.internal)
- Can create DNS alias: `proxmox.fjeld.internal` → `fjeld.fjeld.internal`

---

## 📝 Final DNS Architecture

### Services with Tailscale Installed (Direct Access)

| Service | Container | Tailscale | DNS Name |
|---------|-----------|-----------|----------|
| Prometheus | LXC 104 | ✅ | prometheus.fjeld.internal |
| Grafana | LXC 105 | ✅ | grafana.fjeld.internal |
| Portfolio | LXC 141 | ✅ | portfolio.fjeld.internal |
| Control Portal | LXC 106 | ✅ (new) | portal.fjeld.internal |
| Gateway/Proxy | LXC 110 | ✅ (new) | gateway.fjeld.internal |
| AdGuard | ? | ✅ Already | adguard.fjeld.internal |
| Plex | ? | ✅ Already | plex.fjeld.internal |
| UniFi | ? | ✅ Already | unifi.fjeld.internal |

### Aliases (Manual DNS Records in Tailscale)

| DNS Name | Points To |
|----------|-----------|
| proxmox.fjeld.internal | fjeld.fjeld.internal:8006 |

---

## 🚀 Deployment Checklist

### Phase 1: Tailscale Setup (Day 1)

- [ ] Enable custom domain `fjeld.internal` in Tailscale console
- [ ] Install Tailscale in Prometheus LXC (104)
- [ ] Install Tailscale in Grafana LXC (105)
- [ ] Install Tailscale in Portfolio LXC (141)
- [ ] Rename containers to match desired DNS names
- [ ] Test access: `curl http://grafana.fjeld.internal`
- [ ] Test from phone with Tailscale app

### Phase 2: Control Portal (Day 2-3)

- [ ] Create new LXC container (106) for portal
- [ ] Install Tailscale in portal container
- [ ] Build Next.js + FastAPI portal app
- [ ] Deploy portal to container
- [ ] Configure portal.fjeld.internal DNS
- [ ] Test access from all devices

### Phase 3: Public Services (Day 4)

- [ ] Deploy Uptime Kuma for status page
- [ ] Configure status.fjeld.tech in Cloudflare
- [ ] Create simple homepage at fjeld.tech
- [ ] Add blog subdomain (optional)

### Phase 4: Polish & Documentation (Day 5+)

- [ ] Add all services to portal dashboard
- [ ] Create PWA for mobile
- [ ] Document everything in docs.fjeld.tech
- [ ] Set up Tailscale ACLs for sharing
- [ ] Configure Tailscale Funnel for demo dashboard

---

## 🛠️ Quick Commands Reference

### Create LXC Container (from Proxmox host)
```bash
sudo pct create <ID> local:vztmpl/<template> \
  --hostname <name> \
  --memory 2048 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.<X>/24,gw=192.168.1.1 \
  --rootfs local-lvm:10 \
  --start 1
```

### Install Tailscale in Container
```bash
sudo pct exec <ID> -- bash -c "curl -fsSL https://tailscale.com/install.sh | sh && tailscale up"
```

### Set Container Hostname
```bash
sudo pct set <ID> --hostname <name>
```

### Test Service Access
```bash
# Via Tailscale from any device:
curl http://<service>.fjeld.internal

# Example:
curl http://grafana.fjeld.internal
```

---

## 🎯 Next Actions for You

**Manual steps required:**

1. **Go to Tailscale admin console** → Enable custom domain `fjeld.internal`
2. **Tell me when done**, and I'll proceed with installing Tailscale in containers

**Automated steps I'll handle:**

3. Install Tailscale in key containers (104, 105, 141)
4. Rename containers appropriately
5. Test all DNS names
6. Build control portal
7. Deploy public status page

---

**Ready to proceed?** Just let me know when you've enabled the custom domain in Tailscale!
