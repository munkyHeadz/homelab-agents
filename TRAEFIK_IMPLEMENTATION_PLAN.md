# Traefik Reverse Proxy - Complete Implementation Plan

## 🎯 Why Traefik?

Traefik is **excellent** for your setup - here's why:

### Traefik vs Caddy Comparison

| Feature | Traefik | Caddy |
|---------|---------|-------|
| **Docker Integration** | ✅✅✅ Auto-discovery! | ❌ Manual config |
| **Dashboard UI** | ✅ Beautiful web UI | ❌ No UI |
| **Dynamic Config** | ✅ Automatic updates | ❌ Requires reload |
| **Let's Encrypt** | ✅ Built-in | ✅ Built-in |
| **Middleware** | ✅ Rich middleware | ✅ Basic |
| **Kubernetes Ready** | ✅ Native support | ❌ Limited |
| **Learning Curve** | Moderate | Easy |
| **Configuration** | YAML/Labels | Caddyfile |

### Traefik's Killer Features

**1. Automatic Service Discovery**
```yaml
# Just label your Docker containers - Traefik finds them automatically!
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.grafana.rule=Host(`grafana.fjeld.internal`)"
```

**2. Beautiful Dashboard**
- See all routes in real-time
- Monitor backends
- View middleware
- Check certificates

**3. Multiple Providers**
- Docker (auto-discovery)
- File (manual config)
- Kubernetes
- Consul
- And more!

---

## 🏗️ Architecture with Traefik

```
┌─────────────────────────────────────────────────────┐
│              Tailscale Network                       │
└─────────────────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │   Traefik Gateway     │
            │   (LXC 110)          │
            │   :443 (HTTPS)        │
            │   :80 (HTTP→HTTPS)    │
            │   :8080 (Dashboard)   │
            └───────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼────┐    ┌─────▼─────┐   ┌────▼─────┐
    │Grafana │    │Prometheus │   │ Portal   │
    │  :3000 │    │   :9090   │   │  :3000   │
    └────────┘    └───────────┘   └──────────┘
        │               │               │
    Auto-discovered via Docker labels or
    Configured via static file
```

---

## 🚀 Implementation Options

### Option 1: Traefik + Docker (Recommended)

**Best for:** Services running in Docker containers

**Benefits:**
- Automatic service discovery
- Just add labels to containers
- Zero configuration for new services
- Dynamic updates

### Option 2: Traefik + File Provider

**Best for:** Non-Docker services (LXC containers, VMs)

**Benefits:**
- Full control over routing
- Works with any service
- YAML configuration

### Option 3: Hybrid (Both!)

**Best for:** Mixed environment (Docker + LXC)

**Benefits:**
- Auto-discovery for Docker
- Manual config for LXC
- Best of both worlds

---

## 📦 Deployment Plan

### Step 1: Create Traefik Gateway Container (20 min)

```bash
# Create LXC 110 for Traefik
sudo pct create 110 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname traefik-gateway \
  --memory 2048 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.110/24,gw=192.168.1.1 \
  --rootfs local-lvm:12 \
  --features nesting=1,keyctl=1

# Add TUN device for Tailscale
echo "lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net dev/net none bind,create=dir" | sudo tee -a /etc/pve/lxc/110.conf

# Start container
sudo pct start 110
```

### Step 2: Install Docker + Tailscale (15 min)

```bash
# Enter container
sudo pct exec 110 -- bash

# Install Docker
apt update
apt install -y docker.io docker-compose curl

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Join Tailscale network
tailscale up \
  --authkey=tskey-auth-kYKTFYXKCm11CNTRL-eKzAaQhmdVBt2tF3g15wUBTi7Mii7rkUA \
  --ssh \
  --hostname=traefik-gateway

exit
```

### Step 3: Create Traefik Configuration (15 min)

```bash
# Create directory structure
sudo pct exec 110 -- mkdir -p /opt/traefik/{config,certs}

# Create docker-compose.yml
cat > /tmp/traefik-compose.yml << 'EOF'
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - traefik
    ports:
      - 80:80      # HTTP
      - 443:443    # HTTPS
      - 8080:8080  # Dashboard
    environment:
      - TZ=Europe/Amsterdam
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /opt/traefik/traefik.yml:/traefik.yml:ro
      - /opt/traefik/config:/config:ro
      - /opt/traefik/certs:/certs
    labels:
      # Dashboard
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`traefik.fjeld.internal`)"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.middlewares=auth"
      # Basic auth (username: admin, password: change_me)
      - "traefik.http.middlewares.auth.basicauth.users=admin:$$apr1$$h7qe7LGq$$Qbp0DKZZcBqe4xXjvQzNO1"

networks:
  traefik:
    name: traefik
    external: true
EOF

sudo pct push 110 /tmp/traefik-compose.yml /opt/traefik/docker-compose.yml
```

### Step 4: Create Traefik Static Configuration (10 min)

```bash
cat > /tmp/traefik.yml << 'EOF'
# Traefik Static Configuration
api:
  dashboard: true
  debug: false

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true

  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: traefik

  file:
    directory: /config
    watch: true

# Logging
log:
  level: INFO
  format: common

# Access logs
accessLog:
  format: common

# Internal TLS (for Tailscale network)
tls:
  options:
    default:
      minVersion: VersionTLS12
      sniStrict: false
EOF

sudo pct push 110 /tmp/traefik.yml /opt/traefik/traefik.yml
```

### Step 5: Create Dynamic Configuration for LXC Services (15 min)

```bash
cat > /tmp/services.yml << 'EOF'
# Dynamic Configuration for non-Docker services
http:
  routers:
    # Grafana
    grafana:
      rule: "Host(`grafana.fjeld.internal`)"
      service: grafana
      tls: {}

    # Prometheus
    prometheus:
      rule: "Host(`prometheus.fjeld.internal`)"
      service: prometheus
      tls: {}

    # Portal (or Homepage when you deploy it)
    portal:
      rule: "Host(`portal.fjeld.internal`)"
      service: portal
      tls: {}

    # Proxmox
    proxmox:
      rule: "Host(`proxmox.fjeld.internal`)"
      service: proxmox
      tls:
        options: default

    # PostgreSQL (web UI if you add one)
    postgres:
      rule: "Host(`postgres.fjeld.internal`)"
      service: postgres
      tls: {}

  services:
    # Grafana
    grafana:
      loadBalancer:
        servers:
          - url: "http://grafana:3000"

    # Prometheus
    prometheus:
      loadBalancer:
        servers:
          - url: "http://prometheus:9090"

    # Portal
    portal:
      loadBalancer:
        servers:
          - url: "http://portal:3000"

    # Proxmox
    proxmox:
      loadBalancer:
        servers:
          - url: "https://fjeld:8006"
        serversTransport: insecureTransport

    # PostgreSQL
    postgres:
      loadBalancer:
        servers:
          - url: "http://postgres:5432"

  # Middleware
  middlewares:
    # Security headers
    secure-headers:
      headers:
        browserXssFilter: true
        contentTypeNosniff: true
        frameDeny: true
        sslRedirect: true

    # Rate limiting
    rate-limit:
      rateLimit:
        average: 100
        burst: 50

  # Server transports
  serversTransports:
    insecureTransport:
      insecureSkipVerify: true
EOF

sudo pct push 110 /tmp/services.yml /opt/traefik/config/services.yml
```

### Step 6: Start Traefik (5 min)

```bash
# Create network
sudo pct exec 110 -- docker network create traefik

# Start Traefik
sudo pct exec 110 -- bash -c "cd /opt/traefik && docker-compose up -d"

# Check logs
sudo pct exec 110 -- docker logs traefik -f
```

---

## 🎨 Traefik Dashboard Access

Once running, access the Traefik dashboard:

**URL:** http://traefik.fjeld.internal:8080 (or https://traefik-gateway.tahr-bass.ts.net:8080)

**Default credentials:**
- Username: `admin`
- Password: `change_me` (change this!)

**Generate new password:**
```bash
# Generate bcrypt hash
echo $(htpasswd -nb admin YOUR_PASSWORD) | sed -e s/\\$/\\$\\$/g
```

---

## 🐳 Docker Container Auto-Discovery

For any Docker container, just add labels:

```yaml
version: '3.8'

services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    container_name: homepage
    networks:
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.homepage.rule=Host(`home.fjeld.internal`)"
      - "traefik.http.routers.homepage.tls=true"
      - "traefik.http.services.homepage.loadbalancer.server.port=3000"

networks:
  traefik:
    external: true
```

Traefik **automatically** discovers it and creates the route!

---

## 🔐 SSL Certificates Options

### Option 1: Self-Signed (Internal Use)

Traefik generates these automatically for `.fjeld.internal` domains.

### Option 2: Tailscale Certificates

Use Tailscale's cert provisioning:

```bash
# Get cert for gateway
sudo pct exec 110 -- tailscale cert traefik-gateway.tahr-bass.ts.net

# Configure Traefik to use it
# Update traefik.yml:
tls:
  certificates:
    - certFile: /certs/traefik-gateway.tahr-bass.ts.net.crt
      keyFile: /certs/traefik-gateway.tahr-bass.ts.net.key
```

### Option 3: Let's Encrypt (Public Domains)

If you expose services publicly via `fjeld.tech`:

```yaml
# In traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com
      storage: /certs/acme.json
      httpChallenge:
        entryPoint: web
```

---

## 📊 Complete Service URLs

After Traefik deployment:

| Service | URL | Port-Free |
|---------|-----|-----------|
| Grafana | https://grafana.fjeld.internal | ✅ |
| Prometheus | https://prometheus.fjeld.internal | ✅ |
| Portal/Homepage | https://portal.fjeld.internal | ✅ |
| Proxmox | https://proxmox.fjeld.internal | ✅ |
| Traefik Dashboard | https://traefik.fjeld.internal | ✅ |
| Plex | https://plex.fjeld.internal | ✅ |
| AdGuard | https://adguard.fjeld.internal | ✅ |

All accessible on **port 443** with **HTTPS**!

---

## 🎯 Traefik Features You'll Love

### 1. Middleware Support

Add authentication, rate limiting, headers:

```yaml
labels:
  - "traefik.http.routers.service.middlewares=auth,rate-limit"
  - "traefik.http.middlewares.auth.basicauth.users=user:$$apr1$$..."
  - "traefik.http.middlewares.rate-limit.ratelimit.average=100"
```

### 2. Load Balancing

Multiple backends automatically balanced:

```yaml
services:
  grafana:
    loadBalancer:
      servers:
        - url: "http://grafana1:3000"
        - url: "http://grafana2:3000"
      healthCheck:
        path: /api/health
        interval: 10s
```

### 3. Circuit Breaker

Automatic failover if service is down:

```yaml
middlewares:
  circuit-breaker:
    circuitBreaker:
      expression: "NetworkErrorRatio() > 0.3"
```

### 4. Metrics & Monitoring

Exposes Prometheus metrics:

```yaml
# In traefik.yml
metrics:
  prometheus:
    addEntryPointsLabels: true
    addServicesLabels: true
```

Then scrape from Prometheus:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'traefik'
    static_configs:
      - targets: ['traefik-gateway:8080']
```

---

## 🆚 Final Comparison: Traefik vs Caddy vs Tailscale Serve

| Solution | Ease of Setup | Features | Docker Support | Best For |
|----------|---------------|----------|----------------|----------|
| **Tailscale Serve** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ | Quick SSL, simple setup |
| **Caddy** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | Simple reverse proxy |
| **Traefik** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Docker, complex routing |

---

## 💡 My Recommendation

**Use Traefik if:**
- ✅ You have Docker containers (auto-discovery is amazing!)
- ✅ You want a beautiful dashboard
- ✅ You need advanced features (middleware, load balancing)
- ✅ You plan to scale (add more services)

**Use Caddy if:**
- ✅ You want simplicity
- ✅ You have mostly non-Docker services
- ✅ You don't need a dashboard

**Use Tailscale Serve if:**
- ✅ You want the quickest solution
- ✅ You're okay with `.ts.net` domains
- ✅ You don't need a central proxy

---

## 🚀 Quick Start: Deploy Traefik Now

**I can deploy Traefik in ~45 minutes with:**
1. LXC 110 created
2. Docker + Tailscale installed
3. Traefik configured
4. All services routed
5. Dashboard accessible
6. HTTPS working

**Plus, I can deploy Homepage with Docker auto-discovery:**
```yaml
# Homepage automatically discovered by Traefik!
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.homepage.rule=Host(`home.fjeld.internal`)"
```

**Ready to deploy Traefik?** 🚀

It's the perfect solution for your Docker-heavy homelab!
