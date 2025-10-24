#!/bin/bash
################################################################################
# Homelab Agents - One-Line Installer
#
# Quick installation without PostgreSQL (for testing):
#   curl -fsSL https://raw.githubusercontent.com/yourusername/homelab-agents/main/install.sh | bash
#
# Or run locally:
#   ./install.sh
#
################################################################################

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Homelab Autonomous Agents - Quick Install                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect if we're in the project directory
if [ -f "deploy.sh" ] && [ -f "run_agents.py" ]; then
    echo -e "${GREEN}✓ Running from project directory${NC}"
    PROJECT_DIR="$(pwd)"
else
    echo -e "${YELLOW}⚠ Not in project directory${NC}"
    echo "Please cd to /home/munky/homelab-agents first"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo ""
    echo "Creating .env from template..."

    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ .env created from template${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT: Edit .env and set your API keys:${NC}"
        echo "  nano .env"
        echo ""
        echo "Required:"
        echo "  - ANTHROPIC_API_KEY=sk-ant-api03-..."
        echo ""
        echo "Optional (configure services you want to use):"
        echo "  - PROXMOX_HOST, PROXMOX_NODE"
        echo "  - UNIFI_HOST, UNIFI_USERNAME, UNIFI_PASSWORD"
        echo "  - TAILSCALE_API_KEY, TAILSCALE_TAILNET"
        echo "  - CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID"
        echo ""
        read -p "Press Enter after editing .env to continue..."
    else
        echo -e "${YELLOW}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Run the main deployment script
echo ""
echo -e "${BLUE}Running automated deployment...${NC}"
echo ""

# Skip PostgreSQL by default (manual deployment recommended)
bash deploy.sh --skip-postgres

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation Complete!                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo -e "1. Activate Python environment:"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo -e "2. Test the system:"
echo -e "   ${YELLOW}python run_agents.py --mode interactive${NC}"
echo ""
echo -e "3. Try some commands:"
echo -e "   ${YELLOW}/status${NC}              # System status"
echo -e "   ${YELLOW}/agents${NC}              # List agents"
echo -e "   ${YELLOW}Check VM status${NC}      # Test task"
echo ""
echo -e "4. Deploy PostgreSQL (for persistent memory):"
echo -e "   See: ${YELLOW}DEPLOYMENT_GUIDE.md${NC}"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo -e "  • Quick Start:  ${YELLOW}QUICK_START.md${NC}"
echo -e "  • Full Guide:   ${YELLOW}DEPLOYMENT_GUIDE.md${NC}"
echo -e "  • Agent Docs:   ${YELLOW}agents/README.md${NC}"
echo ""
