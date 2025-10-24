#!/bin/bash
# Setup API Tokens and Permissions

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}API Token & Permissions Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Fix Docker socket permissions
echo -e "\n${YELLOW}[1/3] Fixing Docker socket permissions...${NC}"
if groups | grep -q docker; then
    echo -e "${GREEN}✓ User already in docker group${NC}"
else
    echo -e "${YELLOW}Adding user to docker group...${NC}"
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✓ User added to docker group${NC}"
    echo -e "${YELLOW}⚠ You'll need to log out and back in for this to take effect${NC}"
    echo -e "${YELLOW}  Or run: newgrp docker${NC}"
fi

# Create Proxmox API Token
echo -e "\n${YELLOW}[2/3] Creating Proxmox API Token...${NC}"
echo -e "${BLUE}Please create a Proxmox API token manually:${NC}"
echo -e ""
echo -e "1. Open Proxmox web UI: https://$(hostname -I | awk '{print $1}'):8006"
echo -e "2. Go to: Datacenter → Permissions → API Tokens"
echo -e "3. Click 'Add' button"
echo -e "4. Fill in:"
echo -e "   - User: root@pam"
echo -e "   - Token ID: agent-token"
echo -e "   - Privilege Separation: UNCHECKED (disable)"
echo -e "5. Click 'Add'"
echo -e "6. COPY the secret token that appears (it won't be shown again!)"
echo -e ""
read -p "Press Enter when you have the token ready..."
echo -e ""
read -p "Paste the Proxmox API Token Secret: " PROXMOX_TOKEN
echo -e ""

# Update .env file
echo -e "${YELLOW}[3/3] Updating .env file...${NC}"
sed -i "s|^PROXMOX_TOKEN_SECRET=.*|PROXMOX_TOKEN_SECRET=${PROXMOX_TOKEN}|" /home/munky/homelab-agents/.env
sed -i "s|^PROXMOX_HOST=192.168.1.1|PROXMOX_HOST=localhost|" /home/munky/homelab-agents/.env

echo -e "${GREEN}✓ .env file updated${NC}"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "API Tokens configured:"
echo -e "  ✓ Cloudflare API Token"
echo -e "  ✓ Tailscale API Key"
echo -e "  ✓ Tailscale Auth Key"
echo -e "  ✓ Proxmox API Token (just added)"
echo -e ""
echo -e "Docker permissions:"
echo -e "  ✓ User added to docker group"
echo -e "  ⚠ Run 'newgrp docker' or log out/in for it to take effect"
echo -e ""
echo -e "Next step: Test the system!"
echo -e "  cd /home/munky/homelab-agents"
echo -e "  newgrp docker"
echo -e "  source venv/bin/activate"
echo -e "  python run_agents.py --mode single --objective \"Show Proxmox node status\""
echo -e ""
echo -e "${BLUE}========================================${NC}"
