#!/bin/bash
# Setup Docker LXC Container

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VMID=103
HOSTNAME="docker"
MEMORY=4096
CORES=4
DISK=50
IP="192.168.1.103/24"
GATEWAY="192.168.1.1"
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Docker LXC Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Step 1: Create LXC with nesting enabled (required for Docker)
echo -e "\n${YELLOW}[1/5] Creating Debian LXC with nesting...${NC}"
pct create $VMID $TEMPLATE \
  --hostname $HOSTNAME \
  --memory $MEMORY \
  --cores $CORES \
  --rootfs local-lvm:$DISK \
  --net0 name=eth0,bridge=vmbr0,ip=$IP,gw=$GATEWAY \
  --features nesting=1,keyctl=1 \
  --unprivileged 1 \
  --password docker123

echo -e "${GREEN}✓ LXC created${NC}"

# Step 2: Start LXC
echo -e "\n${YELLOW}[2/5] Starting LXC...${NC}"
pct start $VMID
sleep 10
echo -e "${GREEN}✓ LXC started${NC}"

# Step 3: Install Docker
echo -e "\n${YELLOW}[3/5] Installing Docker...${NC}"
pct exec $VMID -- bash -c "
  # Update and install prerequisites
  apt-get update
  apt-get install -y ca-certificates curl gnupg

  # Add Docker's official GPG key
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  # Add Docker repository
  echo \
    \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    \$(. /etc/os-release && echo \"\$VERSION_CODENAME\") stable\" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

  # Install Docker
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Enable and start Docker
  systemctl enable docker
  systemctl start docker
"
echo -e "${GREEN}✓ Docker installed${NC}"

# Step 4: Configure Docker Remote API
echo -e "\n${YELLOW}[4/5] Configuring Docker remote API...${NC}"
pct exec $VMID -- bash -c "
  # Create systemd override directory
  mkdir -p /etc/systemd/system/docker.service.d

  # Configure Docker to listen on TCP (in addition to socket)
  cat > /etc/systemd/system/docker.service.d/override.conf <<'DOCKER_EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:2375 --containerd=/run/containerd/containerd.sock
DOCKER_EOF

  # Reload and restart Docker
  systemctl daemon-reload
  systemctl restart docker
"
echo -e "${GREEN}✓ Docker remote API configured${NC}"

# Step 5: Test Docker
echo -e "\n${YELLOW}[5/5] Testing Docker installation...${NC}"
pct exec $VMID -- bash -c "
  docker --version
  docker compose version
  docker ps
"
echo -e "${GREEN}✓ Docker working${NC}"

# Display summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Docker LXC Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Container ID: ${YELLOW}${VMID}${NC}"
echo -e "IP Address: ${YELLOW}${IP%/*}${NC}"
echo -e "Hostname: ${YELLOW}${HOSTNAME}${NC}"
echo -e ""
echo -e "Docker API:"
echo -e "  TCP: ${BLUE}tcp://${IP%/*}:2375${NC}"
echo -e "  Socket (inside LXC): ${BLUE}unix:///var/run/docker.sock${NC}"
echo -e ""
echo -e "Access LXC:"
echo -e "  ${BLUE}pct enter ${VMID}${NC}"
echo -e ""
echo -e "Test Docker remotely:"
echo -e "  ${BLUE}docker -H tcp://${IP%/*}:2375 ps${NC}"
echo -e ""
echo -e "Next steps:"
echo -e "  1. Update .env with DOCKER_HOST=tcp://${IP%/*}:2375"
echo -e "  2. Test agent Docker connectivity"
echo -e "${BLUE}========================================${NC}"
