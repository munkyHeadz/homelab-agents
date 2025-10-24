#!/bin/bash
set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VMID=107
HOSTNAME="monitoring"
MEMORY=4096
CORES=2
DISK=30
IP="192.168.1.107/24"
GATEWAY="192.168.1.1"
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Homelab Monitoring Stack Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Create LXC container
echo -e "\n${YELLOW}[1/8] Creating Debian LXC for monitoring...${NC}"
sudo pct create $VMID $TEMPLATE \
  --hostname $HOSTNAME \
  --memory $MEMORY \
  --cores $CORES \
  --rootfs local-lvm:$DISK \
  --net0 name=eth0,bridge=vmbr0,ip=$IP,gw=$GATEWAY \
  --unprivileged 1 \
  --password monitoring123 \
  --features nesting=1
echo -e "${GREEN}✓ LXC created${NC}"

# Start container
echo -e "\n${YELLOW}[2/8] Starting LXC...${NC}"
sudo pct start $VMID
sleep 5
echo -e "${GREEN}✓ LXC started${NC}"

# Update system and install dependencies
echo -e "\n${YELLOW}[3/8] Installing dependencies...${NC}"
sudo pct exec $VMID -- bash -c "apt-get update && apt-get install -y curl wget gnupg2 apt-transport-https software-properties-common"
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install Prometheus
echo -e "\n${YELLOW}[4/8] Installing Prometheus...${NC}"
sudo pct exec $VMID -- bash -c "
  useradd --no-create-home --shell /bin/false prometheus
  mkdir -p /etc/prometheus /var/lib/prometheus
  cd /tmp
  wget https://github.com/prometheus/prometheus/releases/download/v2.54.1/prometheus-2.54.1.linux-amd64.tar.gz
  tar xzf prometheus-2.54.1.linux-amd64.tar.gz
  cd prometheus-2.54.1.linux-amd64
  cp prometheus promtool /usr/local/bin/
  cp -r consoles console_libraries /etc/prometheus/
  chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus /usr/local/bin/prometheus /usr/local/bin/promtool
  rm -rf /tmp/prometheus-*
"
echo -e "${GREEN}✓ Prometheus installed${NC}"

# Configure Prometheus
echo -e "\n${YELLOW}[5/8] Configuring Prometheus...${NC}"
sudo pct exec $VMID -- bash -c "cat > /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'docker'
    static_configs:
      - targets: ['192.168.1.101:9323']

  - job_name: 'homelab-agents'
    static_configs:
      - targets: ['192.168.1.102:8000']
EOF
chown prometheus:prometheus /etc/prometheus/prometheus.yml
"

# Create Prometheus systemd service
sudo pct exec $VMID -- bash -c "cat > /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus Monitoring System
After=network.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus/ \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
"
echo -e "${GREEN}✓ Prometheus configured and started${NC}"

# Install Node Exporter
echo -e "\n${YELLOW}[6/8] Installing Node Exporter...${NC}"
sudo pct exec $VMID -- bash -c "
  useradd --no-create-home --shell /bin/false node_exporter
  cd /tmp
  wget https://github.com/prometheus/node_exporter/releases/download/v1.8.2/node_exporter-1.8.2.linux-amd64.tar.gz
  tar xzf node_exporter-1.8.2.linux-amd64.tar.gz
  cp node_exporter-1.8.2.linux-amd64/node_exporter /usr/local/bin/
  chown node_exporter:node_exporter /usr/local/bin/node_exporter
  rm -rf /tmp/node_exporter-*
"

# Create Node Exporter systemd service
sudo pct exec $VMID -- bash -c "cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
"
echo -e "${GREEN}✓ Node Exporter installed and started${NC}"

# Install Grafana
echo -e "\n${YELLOW}[7/8] Installing Grafana...${NC}"
sudo pct exec $VMID -- bash -c "
  wget -q -O - https://packages.grafana.com/gpg.key | gpg --dearmor | tee /etc/apt/trusted.gpg.d/grafana.gpg > /dev/null
  echo 'deb [signed-by=/etc/apt/trusted.gpg.d/grafana.gpg] https://packages.grafana.com/oss/deb stable main' | tee /etc/apt/sources.list.d/grafana.list
  apt-get update
  apt-get install -y grafana
  systemctl daemon-reload
  systemctl enable grafana-server
  systemctl start grafana-server
"
echo -e "${GREEN}✓ Grafana installed and started${NC}"

# Verify services
echo -e "\n${YELLOW}[8/8] Verifying services...${NC}"
sleep 5
sudo pct exec $VMID -- bash -c "
  systemctl is-active prometheus && echo 'Prometheus: ✓'
  systemctl is-active node_exporter && echo 'Node Exporter: ✓'
  systemctl is-active grafana-server && echo 'Grafana: ✓'
"
echo -e "${GREEN}✓ All services verified${NC}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Monitoring Stack Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nAccess URLs:"
echo -e "  Prometheus: ${BLUE}http://192.168.1.107:9090${NC}"
echo -e "  Grafana:    ${BLUE}http://192.168.1.107:3000${NC}"
echo -e "               Default credentials: admin/admin"
echo -e "\nMetrics Endpoints:"
echo -e "  Node Exporter:    ${BLUE}http://192.168.1.107:9100/metrics${NC}"
echo -e "  Prometheus API:   ${BLUE}http://192.168.1.107:9090/api/v1${NC}"
