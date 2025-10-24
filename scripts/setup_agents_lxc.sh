#!/bin/bash
# Setup Agents LXC Container

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VMID=104
HOSTNAME="homelab-agents"
MEMORY=2048
CORES=2
DISK=20
IP="192.168.1.102/24"
GATEWAY="192.168.1.1"
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Homelab Agents LXC Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Step 1: Create LXC
echo -e "\n${YELLOW}[1/6] Creating Debian LXC for agents...${NC}"
sudo pct create $VMID $TEMPLATE \
  --hostname $HOSTNAME \
  --memory $MEMORY \
  --cores $CORES \
  --rootfs local-lvm:$DISK \
  --net0 name=eth0,bridge=vmbr0,ip=$IP,gw=$GATEWAY \
  --unprivileged 1 \
  --password agents123

echo -e "${GREEN}✓ LXC created${NC}"

# Step 2: Start LXC
echo -e "\n${YELLOW}[2/6] Starting LXC...${NC}"
sudo pct start $VMID
sleep 10
echo -e "${GREEN}✓ LXC started${NC}"

# Step 3: Install Python and dependencies
echo -e "\n${YELLOW}[3/6] Installing Python 3.13 and dependencies...${NC}"
sudo pct exec $VMID -- bash -c "
  apt-get update
  apt-get install -y python3 python3-pip python3-venv git curl wget
  python3 --version
"
echo -e "${GREEN}✓ Python installed${NC}"

# Step 4: Copy agent code
echo -e "\n${YELLOW}[4/6] Copying agent code to LXC...${NC}"
sudo pct push $VMID /home/munky/homelab-agents /root/homelab-agents --recursive
echo -e "${GREEN}✓ Code copied${NC}"

# Step 5: Install Python dependencies
echo -e "\n${YELLOW}[5/6] Installing Python packages...${NC}"
sudo pct exec $VMID -- bash -c "
  cd /root/homelab-agents
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
"
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 6: Setup systemd service
echo -e "\n${YELLOW}[6/6] Setting up Telegram bot service...${NC}"
sudo pct exec $VMID -- bash -c "
  cp /root/homelab-agents/scripts/homelab-telegram-bot.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable homelab-telegram-bot.service
  systemctl start homelab-telegram-bot.service
"
echo -e "${GREEN}✓ Service configured${NC}"

# Display summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Agents LXC Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Container ID: ${YELLOW}${VMID}${NC}"
echo -e "IP Address: ${YELLOW}${IP%/*}${NC}"
echo -e "Hostname: ${YELLOW}${HOSTNAME}${NC}"
echo -e ""
echo -e "Access LXC:"
echo -e "  ${BLUE}sudo pct enter ${VMID}${NC}"
echo -e ""
echo -e "Check Telegram bot:"
echo -e "  ${BLUE}sudo pct exec ${VMID} -- systemctl status homelab-telegram-bot${NC}"
echo -e ""
echo -e "View logs:"
echo -e "  ${BLUE}sudo pct exec ${VMID} -- journalctl -u homelab-telegram-bot -f${NC}"
echo -e "${BLUE}========================================${NC}"
