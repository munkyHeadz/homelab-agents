#!/bin/bash
# Homelab Agent Service Control Script

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="homelab-agents.service"

case "$1" in
    start)
        echo -e "${BLUE}Starting agent system in daemon mode...${NC}"
        sudo systemctl start $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    stop)
        echo -e "${YELLOW}Stopping agent system...${NC}"
        sudo systemctl stop $SERVICE_NAME
        echo -e "${GREEN}✓ Service stopped${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Restarting agent system...${NC}"
        sudo systemctl restart $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    status)
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    logs)
        echo -e "${BLUE}Agent system logs (Ctrl+C to exit):${NC}"
        sudo journalctl -u $SERVICE_NAME -f
        ;;

    logs-recent)
        echo -e "${BLUE}Recent agent system logs:${NC}"
        sudo journalctl -u $SERVICE_NAME -n 50 --no-pager
        ;;

    enable)
        echo -e "${BLUE}Enabling service to start on boot...${NC}"
        sudo systemctl enable $SERVICE_NAME
        echo -e "${GREEN}✓ Service enabled${NC}"
        ;;

    disable)
        echo -e "${YELLOW}Disabling service from starting on boot...${NC}"
        sudo systemctl disable $SERVICE_NAME
        echo -e "${GREEN}✓ Service disabled${NC}"
        ;;

    *)
        echo "Homelab Agent Service Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|logs-recent|enable|disable}"
        echo ""
        echo "Commands:"
        echo "  start        - Start the agent daemon"
        echo "  stop         - Stop the agent daemon"
        echo "  restart      - Restart the agent daemon"
        echo "  status       - Show service status"
        echo "  logs         - Follow live logs (Ctrl+C to exit)"
        echo "  logs-recent  - Show recent logs"
        echo "  enable       - Enable service to start on boot"
        echo "  disable      - Disable service from starting on boot"
        exit 1
        ;;
esac
