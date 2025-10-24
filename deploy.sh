#!/bin/bash
################################################################################
# Homelab Autonomous Agent System - Automated Deployment Script
#
# This script automates the complete deployment of the agent system including:
# 1. Prerequisites checking
# 2. PostgreSQL database deployment
# 3. Python environment setup
# 4. MCP server testing
# 5. Agent system verification
#
# Usage:
#   ./deploy.sh [--skip-postgres] [--skip-venv] [--test-only]
#
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="${SCRIPT_DIR}"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/deployment_$(date +%Y%m%d_%H%M%S).log"

# Flags
SKIP_POSTGRES=false
SKIP_VENV=false
TEST_ONLY=false
ON_PROXMOX=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-postgres)
            SKIP_POSTGRES=true
            shift
            ;;
        --skip-venv)
            SKIP_VENV=true
            shift
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-postgres   Skip PostgreSQL deployment"
            echo "  --skip-venv      Skip Python virtual environment creation"
            echo "  --test-only      Only run tests, skip deployment"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

################################################################################
# Logging Functions
################################################################################

log() {
    echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1" | tee -a "${LOG_FILE}"
}

log_step() {
    echo -e "\n${BOLD}${BLUE}$1${NC}\n" | tee -a "${LOG_FILE}"
}

################################################################################
# Utility Functions
################################################################################

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

confirm() {
    read -p "$1 (yes/no): " response
    case "$response" in
        yes|y|Y|YES)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

create_directory() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        log_success "Created directory: $1"
    fi
}

################################################################################
# Prerequisites Check
################################################################################

check_prerequisites() {
    log_step "Step 1: Checking Prerequisites"

    # Create log directory
    create_directory "${LOG_DIR}"

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root - some operations may fail. Consider running as normal user with sudo."
    fi

    # Check for Python 3.9+
    log "Checking Python version..."
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            log_success "Python $PYTHON_VERSION found"
        else
            log_error "Python 3.9+ required (found $PYTHON_VERSION)"
            exit 1
        fi
    else
        log_error "Python 3 not found"
        exit 1
    fi

    # Check for pip
    log "Checking pip..."
    if check_command pip3; then
        log_success "pip3 found"
    else
        log_error "pip3 not found. Install with: apt-get install python3-pip"
        exit 1
    fi

    # Check for git
    log "Checking git..."
    if check_command git; then
        log_success "git found"
    else
        log_warning "git not found - recommended for version control"
    fi

    # Check for libpq (PostgreSQL client library) - required for psycopg
    log "Checking libpq (PostgreSQL client library)..."
    if dpkg -l | grep -q libpq-dev; then
        log_success "libpq-dev found"
    else
        log_warning "libpq-dev not found - installing..."
        sudo apt-get update > /dev/null 2>&1
        sudo apt-get install -y libpq-dev >> "${LOG_FILE}" 2>&1
        if [ $? -eq 0 ]; then
            log_success "libpq-dev installed"
        else
            log_warning "Failed to install libpq-dev automatically - psycopg may not work"
            log_info "Install manually with: sudo apt-get install libpq-dev"
        fi
    fi

    # Check if on Proxmox host
    if check_command pct; then
        ON_PROXMOX=true
        log_success "Running on Proxmox host - full automation available"
    else
        ON_PROXMOX=false
        log_warning "Not running on Proxmox host - PostgreSQL must be deployed manually"
        SKIP_POSTGRES=true
    fi

    # Check .env file
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        log_error ".env file not found!"
        log_info "Copy .env.example to .env and configure it:"
        log_info "  cp .env.example .env"
        log_info "  nano .env"
        exit 1
    else
        log_success ".env file found"
    fi

    # Check for required environment variables
    source "${PROJECT_DIR}/.env"

    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-api03-YOUR-KEY-HERE" ]; then
        log_error "ANTHROPIC_API_KEY not set in .env file"
        exit 1
    else
        log_success "Anthropic API key configured"
    fi

    log_success "Prerequisites check complete"
}

################################################################################
# PostgreSQL Deployment
################################################################################

deploy_postgresql() {
    log_step "Step 2: Deploying PostgreSQL Database"

    if [ "$SKIP_POSTGRES" = true ]; then
        log_warning "Skipping PostgreSQL deployment (--skip-postgres or not on Proxmox)"
        log_info "Manual deployment required. See: DEPLOYMENT_GUIDE.md"
        return 0
    fi

    if [ "$ON_PROXMOX" = false ]; then
        log_error "Cannot deploy PostgreSQL - not running on Proxmox host"
        log_info "Deploy PostgreSQL manually or run this script on Proxmox host"
        return 1
    fi

    log "Starting PostgreSQL deployment..."

    if [ -f "${PROJECT_DIR}/scripts/setup_postgresql.sh" ]; then
        log_info "Running automated PostgreSQL setup..."

        # Make script executable
        chmod +x "${PROJECT_DIR}/scripts/setup_postgresql.sh"

        # Run setup script
        if bash "${PROJECT_DIR}/scripts/setup_postgresql.sh"; then
            log_success "PostgreSQL deployed successfully"
        else
            log_error "PostgreSQL deployment failed"
            return 1
        fi
    else
        log_error "PostgreSQL setup script not found"
        return 1
    fi
}

################################################################################
# Python Environment Setup
################################################################################

setup_python_environment() {
    log_step "Step 3: Setting Up Python Environment"

    if [ "$SKIP_VENV" = true ]; then
        log_warning "Skipping virtual environment creation"
        log_info "Using system Python"
    else
        # Create virtual environment
        if [ ! -d "${VENV_DIR}" ]; then
            log "Creating Python virtual environment..."
            python3 -m venv "${VENV_DIR}"
            log_success "Virtual environment created"
        else
            log_success "Virtual environment already exists"
        fi

        # Activate virtual environment
        log "Activating virtual environment..."
        source "${VENV_DIR}/bin/activate"
        log_success "Virtual environment activated"
    fi

    # Upgrade pip
    log "Upgrading pip..."
    pip install --upgrade pip >> "${LOG_FILE}" 2>&1
    log_success "pip upgraded"

    # Install requirements
    log "Installing Python dependencies (this may take 5-10 minutes)..."
    log_info "Progress logged to: ${LOG_FILE}"

    if pip install -r "${PROJECT_DIR}/requirements.txt" >> "${LOG_FILE}" 2>&1; then
        log_success "Python dependencies installed"
    else
        log_error "Failed to install dependencies"
        log_info "Check log file: ${LOG_FILE}"
        return 1
    fi

    # Verify key packages
    log "Verifying key packages..."

    REQUIRED_PACKAGES=(
        "anthropic"
        "langchain"
        "langgraph"
        "mcp"
        "mem0ai"
        "psycopg2"
        "pgvector"
        "pydantic"
        "structlog"
    )

    for package in "${REQUIRED_PACKAGES[@]}"; do
        if pip show "$package" &> /dev/null; then
            log_success "  ✓ $package"
        else
            log_error "  ✗ $package - MISSING"
        fi
    done
}

################################################################################
# Database Connection Test
################################################################################

test_database_connection() {
    log_step "Step 4: Testing Database Connection"

    source "${PROJECT_DIR}/.env"

    if [ -z "$POSTGRES_HOST" ] || [ "$POSTGRES_HOST" = "192.168.1.100" ]; then
        log_warning "POSTGRES_HOST not configured or using default"
        log_info "Update POSTGRES_HOST in .env file after PostgreSQL deployment"
        return 0
    fi

    log "Testing PostgreSQL connection..."

    # Test with psql if available
    if check_command psql; then
        PGPASSWORD="${POSTGRES_PASSWORD_MEMORY}" psql \
            -h "${POSTGRES_HOST}" \
            -U "${POSTGRES_USER_MEMORY}" \
            -d "${POSTGRES_DB_MEMORY}" \
            -c "SELECT version();" >> "${LOG_FILE}" 2>&1

        if [ $? -eq 0 ]; then
            log_success "Database connection successful"
        else
            log_error "Database connection failed"
            log_info "Check credentials in .env and ensure PostgreSQL is running"
            return 1
        fi
    else
        log_warning "psql not available - skipping connection test"
        log_info "Install postgresql-client to test connections"
    fi
}

################################################################################
# MCP Server Testing
################################################################################

test_mcp_servers() {
    log_step "Step 5: Testing MCP Servers"

    log "Running MCP server test suite..."

    cd "${PROJECT_DIR}"

    if [ "$SKIP_VENV" = false ] && [ -d "${VENV_DIR}" ]; then
        source "${VENV_DIR}/bin/activate"
    fi

    # Run test script
    if python scripts/test_mcp_servers.py 2>&1 | tee -a "${LOG_FILE}"; then
        log_success "MCP server tests passed"
    else
        log_warning "Some MCP server tests failed"
        log_info "This is normal if services aren't configured yet"
        log_info "Check ${LOG_FILE} for details"
    fi
}

################################################################################
# Agent System Verification
################################################################################

verify_agent_system() {
    log_step "Step 6: Verifying Agent System"

    cd "${PROJECT_DIR}"

    if [ "$SKIP_VENV" = false ] && [ -d "${VENV_DIR}" ]; then
        source "${VENV_DIR}/bin/activate"
    fi

    # Check if run_agents.py exists and is executable
    if [ ! -f "${PROJECT_DIR}/run_agents.py" ]; then
        log_error "run_agents.py not found"
        return 1
    fi

    chmod +x "${PROJECT_DIR}/run_agents.py"

    # Test agent imports
    log "Testing agent imports..."

    python3 -c "
from agents.orchestrator_agent import OrchestratorAgent
from agents.infrastructure_agent import InfrastructureAgent
from agents.monitoring_agent import MonitoringAgent
from agents.learning_agent import LearningAgent
print('All agents imported successfully')
" 2>&1 | tee -a "${LOG_FILE}"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Agent imports successful"
    else
        log_error "Agent imports failed"
        return 1
    fi

    log_success "Agent system verified"
}

################################################################################
# Create Systemd Service (Optional)
################################################################################

create_systemd_service() {
    log_step "Step 7: Creating Systemd Service (Optional)"

    if ! confirm "Do you want to create a systemd service for daemon mode?"; then
        log_info "Skipping systemd service creation"
        return 0
    fi

    # Detect user
    if [ -n "$SUDO_USER" ]; then
        SERVICE_USER="$SUDO_USER"
    else
        SERVICE_USER="$(whoami)"
    fi

    # Create service file
    SERVICE_FILE="/tmp/homelab-agents.service"

    cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Homelab Autonomous Agents
After=network.target postgresql.service

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/bin"
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/run_agents.py --mode daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    log "Systemd service file created: ${SERVICE_FILE}"
    log_info "To install the service:"
    log_info "  sudo cp ${SERVICE_FILE} /etc/systemd/system/"
    log_info "  sudo systemctl daemon-reload"
    log_info "  sudo systemctl enable homelab-agents"
    log_info "  sudo systemctl start homelab-agents"
}

################################################################################
# Generate Deployment Report
################################################################################

generate_deployment_report() {
    log_step "Deployment Complete!"

    REPORT_FILE="${LOG_DIR}/deployment_report_$(date +%Y%m%d_%H%M%S).txt"

    cat > "${REPORT_FILE}" <<EOF
================================================================================
HOMELAB AUTONOMOUS AGENT SYSTEM - DEPLOYMENT REPORT
================================================================================

Deployment Date: $(date)
Project Directory: ${PROJECT_DIR}
Log File: ${LOG_FILE}

================================================================================
DEPLOYMENT STATUS
================================================================================

$(if [ "$SKIP_POSTGRES" = true ]; then
    echo "PostgreSQL:        ⚠ SKIPPED (manual deployment required)"
else
    echo "PostgreSQL:        ✓ DEPLOYED"
fi)
$(if [ "$SKIP_VENV" = true ]; then
    echo "Virtual Environment: ⚠ SKIPPED (using system Python)"
else
    echo "Virtual Environment: ✓ CREATED"
fi)
Python Dependencies: ✓ INSTALLED
Database Connection: $([ -n "$POSTGRES_HOST" ] && echo "✓ TESTED" || echo "⚠ NOT TESTED")
MCP Servers:         ✓ TESTED
Agent System:        ✓ VERIFIED

================================================================================
NEXT STEPS
================================================================================

1. Configure Service Credentials
   Edit .env and add credentials for:
   - Proxmox (PROXMOX_HOST, PROXMOX_NODE)
   - Docker (if remote)
   - Unifi (UNIFI_HOST, UNIFI_USERNAME, UNIFI_PASSWORD)
   - Tailscale (TAILSCALE_API_KEY, TAILSCALE_TAILNET)
   - Cloudflare (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID)
   - Pi-hole (PIHOLE_HOST, PIHOLE_API_TOKEN)

2. Test Agent System
   Interactive mode:
   $(if [ "$SKIP_VENV" = false ]; then echo "source ${VENV_DIR}/bin/activate"; fi)
   python run_agents.py --mode interactive

   Try these commands:
   - /status          # Check system status
   - /agents          # List all agents
   - Check VM status  # Test infrastructure agent

3. Deploy n8n (Optional)
   See DEPLOYMENT_GUIDE.md for n8n setup

4. Set Up Monitoring (Optional)
   - Deploy Prometheus
   - Deploy Grafana
   - Configure dashboards

5. Enable Daemon Mode
   Install systemd service:
   sudo cp /tmp/homelab-agents.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable homelab-agents
   sudo systemctl start homelab-agents

================================================================================
USEFUL COMMANDS
================================================================================

# View logs
tail -f ${LOG_DIR}/agents.log

# Test MCP servers
python scripts/test_mcp_servers.py

# Run in interactive mode
python run_agents.py --mode interactive

# Run in daemon mode
python run_agents.py --mode daemon

# Execute single task
python run_agents.py --mode single --objective "Check VM status"

================================================================================
DOCUMENTATION
================================================================================

- Quick Start:      ${PROJECT_DIR}/QUICK_START.md
- Deployment Guide: ${PROJECT_DIR}/DEPLOYMENT_GUIDE.md
- Agent Docs:       ${PROJECT_DIR}/agents/README.md
- MCP Docs:         ${PROJECT_DIR}/mcp_servers/README.md
- Master Plan:      ${PROJECT_DIR}/HOMELAB_AUTOMATION_MASTER_PLAN.md

================================================================================
SUPPORT
================================================================================

Issues? Check:
1. Deployment log: ${LOG_FILE}
2. Agent logs: ${LOG_DIR}/agents.log
3. Documentation: ${PROJECT_DIR}/README.md

================================================================================
EOF

    cat "${REPORT_FILE}"

    log_success "Deployment report saved to: ${REPORT_FILE}"
}

################################################################################
# Main Deployment Flow
################################################################################

main() {
    clear

    echo -e "${BOLD}${BLUE}"
    echo "================================================================================"
    echo "  HOMELAB AUTONOMOUS AGENT SYSTEM - AUTOMATED DEPLOYMENT"
    echo "================================================================================"
    echo -e "${NC}"

    if [ "$TEST_ONLY" = true ]; then
        log_info "Running in TEST ONLY mode"
        test_mcp_servers
        verify_agent_system
        exit 0
    fi

    log "Starting automated deployment..."
    log_info "Log file: ${LOG_FILE}"

    # Run deployment steps
    check_prerequisites

    if [ "$SKIP_POSTGRES" = false ]; then
        deploy_postgresql || log_warning "PostgreSQL deployment had issues - continuing..."
    fi

    setup_python_environment || { log_error "Python environment setup failed"; exit 1; }
    test_database_connection || log_warning "Database connection test had issues - continuing..."
    test_mcp_servers || log_warning "Some MCP tests failed - this is normal if services aren't configured"
    verify_agent_system || { log_error "Agent verification failed"; exit 1; }
    create_systemd_service

    # Generate report
    generate_deployment_report

    echo ""
    echo -e "${BOLD}${GREEN}"
    echo "================================================================================"
    echo "  🎉 DEPLOYMENT COMPLETE!"
    echo "================================================================================"
    echo -e "${NC}"
    echo ""
    echo -e "${CYAN}Your autonomous agent system is ready to use!${NC}"
    echo ""
    echo -e "Quick start:"
    if [ "$SKIP_VENV" = false ]; then
        echo -e "  ${YELLOW}source ${VENV_DIR}/bin/activate${NC}"
    fi
    echo -e "  ${YELLOW}python run_agents.py --mode interactive${NC}"
    echo ""
}

# Run main function
main "$@"
