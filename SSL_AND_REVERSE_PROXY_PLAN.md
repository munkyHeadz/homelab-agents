# SSL Certificates & Reverse Proxy Solution

## 🎯 Goal
Access services like this:
- ❌ `http://grafana:3000` (current - with port)
- ✅ `https://grafana.fjeld.internal` (target - no port, SSL)

---

## 🔐 Solution Options

### Option 1: Tailscale HTTPS (Recommended - Easiest)

Tailscale provides **automatic HTTPS certificates** for free!

**How it works:**
```
https://grafana.tahr-bass.ts.net  ← Automatic SSL!
https://prometheus.tahr-bass.ts.net
https://portal.tahr-bass.ts.net
```

**Enable it:**
```bash
# In each container, enable HTTPS
sudo pct exec 107 -- tailscale cert grafana.tahr-bass.ts.net
```

**Benefits:**
- ✅ Automatic certificate management
- ✅ Auto-renewal
- ✅ Valid certificates (no browser warnings)
- ✅ No configuration needed
- ✅ Works immediately

**Limitations:**
- Uses `.ts.net` domain (not `.fjeld.internal`)
- Each service needs to support HTTPS natively OR use a reverse proxy

---

### Option 2: Caddy Reverse Proxy (Best Solution)

Use Caddy as a central reverse proxy in a dedicated container.

**Architecture:**
```
Client → Caddy (LXC 110) → Services
         ├─ grafana.fjeld.internal:443 → grafana:3000
         ├─ prometheus.fjeld.internal:443 → prometheus:9090
         ├─ portal.fjeld.internal:443 → portal:3000
         └─ proxmox.fjeld.internal:443 → fjeld:8006
```

**Create Caddy Container:**
```bash
# Create LXC 110 for Caddy
pct create 110 local:vztmpl/ubuntu-24.04.tar.zst \
  --hostname gateway \
  --memory 1024 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.110/24,gw=192.168.1.1

# Install Tailscale + Caddy
pct exec 110 -- apt install -y caddy
pct exec 110 -- tailscale up --authkey=<your-key> --hostname=gateway
```

**Caddyfile Configuration:**
```caddy
# /etc/caddy/Caddyfile

# Grafana
https://grafana.fjeld.internal {
    reverse_proxy grafana:3000
    tls internal  # Use Caddy's internal CA
}

# Prometheus
https://prometheus.fjeld.internal {
    reverse_proxy prometheus:9090
}

# Portal
https://portal.fjeld.internal {
    reverse_proxy portal:3000
}

# Proxmox
https://proxmox.fjeld.internal {
    reverse_proxy https://fjeld:8006 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}

# Plex
https://plex.fjeld.internal {
    reverse_proxy plex:32400
}

# AdGuard
https://adguard.fjeld.internal {
    reverse_proxy adguard:80
}
```

**Why Caddy?**
- ✅ Automatic HTTPS (self-signed for internal use)
- ✅ Simple configuration
- ✅ Automatic certificate management
- ✅ HTTP/2 and HTTP/3 support
- ✅ No port numbers needed
- ✅ One central place to manage all routing

---

### Option 3: Tailscale Serve (Per-Service)

Configure Tailscale Serve on each container to expose HTTPS without ports.

**Example for Grafana:**
```bash
# In Grafana container (LXC 107)
sudo pct exec 107 -- tailscale serve https / http://localhost:3000
```

**Result:**
```
https://grafana.tahr-bass.ts.net  ← Works! No port number!
```

**Benefits:**
- ✅ No central proxy needed
- ✅ Automatic SSL from Tailscale
- ✅ Per-service configuration

**Limitations:**
- ❌ Must configure each service individually
- ❌ Uses `.ts.net` domain
- ❌ More management overhead

---

## 🏗️ Recommended Architecture

**Best approach: Caddy as central gateway**

```
┌─────────────────────────────────────────────────┐
│           Tailscale Network                      │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │   Caddy Gateway       │
        │   (LXC 110)          │
        │   gateway.ts.net      │
        │   Port 443 (HTTPS)    │
        └───────────┬───────────┘
                    │
        ┌───────────┴────────────────────┐
        │                                │
    ┌───▼────┐  ┌────▼────┐  ┌─────▼─────┐
    │Grafana │  │Prometheus│  │  Portal   │
    │  :3000 │  │   :9090  │  │   :3000   │
    └────────┘  └──────────┘  └───────────┘
```

**Access:**
- https://grafana.fjeld.internal (no port!)
- https://prometheus.fjeld.internal
- https://portal.fjeld.internal

---

## 🚀 Implementation Steps

### Step 1: Create Gateway Container (15 min)
```bash
# Create LXC
sudo pct create 110 local:vztmpl/ubuntu-24.04.tar.zst \
  --hostname gateway \
  --memory 1024 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.110/24,gw=192.168.1.1 \
  --features nesting=1,keyctl=1

# Add TUN device
echo "lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net dev/net none bind,create=dir" | sudo tee -a /etc/pve/lxc/110.conf

# Start container
sudo pct start 110
```

### Step 2: Install Caddy + Tailscale (10 min)
```bash
# Install Caddy
sudo pct exec 110 -- bash -c "apt update && apt install -y caddy curl"

# Install Tailscale
sudo pct exec 110 -- bash -c "curl -fsSL https://tailscale.com/install.sh | sh"

# Join Tailscale network
sudo pct exec 110 -- tailscale up \
  --authkey=tskey-auth-kYKTFYXKCm11CNTRL-eKzAaQhmdVBt2tF3g15wUBTi7Mii7rkUA \
  --hostname=gateway
```

### Step 3: Configure Caddy (10 min)
```bash
# Create Caddyfile
sudo pct exec 110 -- bash -c 'cat > /etc/caddy/Caddyfile << "EOF"
{
    # Use internal CA for self-signed certs
    # Or use Tailscale certs (more complex)
}

# Services
https://grafana.fjeld.internal, grafana.fjeld.internal {
    reverse_proxy grafana:3000
    tls internal
}

https://prometheus.fjeld.internal, prometheus.fjeld.internal {
    reverse_proxy prometheus:9090
    tls internal
}

https://portal.fjeld.internal, portal.fjeld.internal {
    reverse_proxy portal:3000
    tls internal
}

https://proxmox.fjeld.internal, proxmox.fjeld.internal {
    reverse_proxy https://fjeld:8006 {
        transport http {
            tls_insecure_skip_verify
        }
    }
    tls internal
}

# Fallback
:443 {
    respond "Fjeld Gateway - Service not found" 404
}
EOF'

# Reload Caddy
sudo pct exec 110 -- systemctl reload caddy
```

### Step 4: Configure DNS (5 min)

**Option A: Update /etc/hosts on each device**
```bash
# On devices connecting
echo "100.x.x.x grafana.fjeld.internal" >> /etc/hosts
echo "100.x.x.x prometheus.fjeld.internal" >> /etc/hosts
echo "100.x.x.x portal.fjeld.internal" >> /etc/hosts
```

**Option B: Use Tailscale DNS (Better)**
In Tailscale console, add DNS records pointing to gateway's IP.

### Step 5: Trust Caddy's CA (One-time)

Export Caddy's root CA and install on your devices:
```bash
# Get Caddy's root CA
sudo pct exec 110 -- caddy trust --ca-root

# Install on macOS
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain caddy-ca.crt

# Install on Linux
sudo cp caddy-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

---

## 🎯 Alternative: Use Tailscale's Built-in HTTPS

**Simplest solution - no reverse proxy needed!**

Each service can get its own HTTPS cert from Tailscale:

```bash
# For Grafana
sudo pct exec 107 -- tailscale serve https:443 http://localhost:3000

# For Prometheus
sudo pct exec 104 -- tailscale serve https:443 http://localhost:9090

# For Portal
sudo pct exec 108 -- tailscale serve https:443 http://localhost:3000
```

**Access:**
```
https://grafana.tahr-bass.ts.net  ← No port!
https://prometheus.tahr-bass.ts.net
https://portal.tahr-bass.ts.net
```

**Pros:**
- ✅ Real SSL certificates (trusted by browsers)
- ✅ No reverse proxy needed
- ✅ Automatic renewal
- ✅ No port numbers

**Cons:**
- ❌ Uses `.tahr-bass.ts.net` instead of `.fjeld.internal`
- ❌ Must configure each service

---

## 💡 My Recommendation

**For ease of use: Tailscale Serve**
- Enable `tailscale serve` on each service
- Get instant HTTPS without ports
- Uses `.ts.net` domain (but that's fine!)

**For custom domains: Caddy Gateway**
- One gateway container
- Full control over domain names
- Can use `.fjeld.internal`

**Quick win:**
```bash
# Enable HTTPS on portal (takes 10 seconds)
sudo pct exec 108 -- tailscale serve https:443 http://localhost:3000

# Now access at:
https://portal.tahr-bass.ts.net  ← No port!
```

Want me to implement either solution?
