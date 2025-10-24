#!/bin/bash
# ============================================================================
# HOMELAB AUTONOMOUS AGENT SYSTEM - SETUP SCRIPT
# ============================================================================
#
# This script bootstraps the complete agent system infrastructure
#
# Usage: ./setup.sh [options]
#   Options:
#     --skip-lxc       Skip LXC container deployment
#     --skip-python    Skip Python environment setup
#     --dry-run        Show what would be done without executing
#
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROXMOX_HELPER_SCRIPTS_BASE="https://github.com/community-scripts/ProxmoxVE/raw/main/ct"

# Parse arguments
SKIP_LXC=false
SKIP_PYTHON=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --skip-lxc)
            SKIP_LXC=true
            ;;
        --skip-python)
            SKIP_PYTHON=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

run_command() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} $1"
    else
        echo -e "${BLUE}▸${NC} $1"
        eval "$1"
    fi
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

# Main setup
main() {
    print_header "HOMELAB AUTONOMOUS AGENT SYSTEM SETUP"

    echo "Project root: $PROJECT_ROOT"
    echo "Dry run: $DRY_RUN"
    echo ""

    # Step 1: Check prerequisites
    print_header "Step 1: Checking Prerequisites"

    check_command git || exit 1
    check_command python3 || exit 1
    check_command pip3 || exit 1

    # Step 2: Deploy LXC containers (if not skipped)
    if [ "$SKIP_LXC" = false ]; then
        print_header "Step 2: Deploying LXC Containers on Proxmox"

        print_warning "This step requires SSH access to your Proxmox host."
        echo "You can skip this step with --skip-lxc if containers are already deployed."
        echo ""

        read -p "Do you want to deploy LXC containers now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter Proxmox host IP: " PROXMOX_IP

            echo ""
            echo "Deploying PostgreSQL LXC..."
            run_command "ssh root@$PROXMOX_IP 'bash -c \"\$(wget -qLO - $PROXMOX_HELPER_SCRIPTS_BASE/postgresql.sh)\"'"

            echo ""
            echo "Deploying n8n LXC..."
            run_command "ssh root@$PROXMOX_IP 'bash -c \"\$(wget -qLO - $PROXMOX_HELPER_SCRIPTS_BASE/n8n.sh)\"'"

            echo ""
            echo "Deploying Redis LXC..."
            run_command "ssh root@$PROXMOX_IP 'bash -c \"\$(wget -qLO - $PROXMOX_HELPER_SCRIPTS_BASE/redis.sh)\"'"

            print_success "LXC containers deployed successfully"
            print_warning "Please note the IP addresses assigned to each container and update your .env file"
        else
            print_warning "Skipping LXC deployment. Make sure containers are deployed before running agents."
        fi
    else
        print_warning "Skipping LXC deployment (--skip-lxc)"
    fi

    # Step 3: Python environment setup
    if [ "$SKIP_PYTHON" = false ]; then
        print_header "Step 3: Setting Up Python Environment"

        cd "$PROJECT_ROOT"

        # Create virtual environment
        if [ ! -d ".venv" ]; then
            print_warning "Creating Python virtual environment..."
            run_command "python3 -m venv .venv"
            print_success "Virtual environment created"
        else
            print_success "Virtual environment already exists"
        fi

        # Activate virtual environment
        print_warning "Activating virtual environment..."
        source .venv/bin/activate

        # Upgrade pip
        print_warning "Upgrading pip..."
        run_command "pip install --upgrade pip"

        # Install requirements
        if [ -f "requirements.txt" ]; then
            print_warning "Installing Python dependencies (this may take a few minutes)..."
            run_command "pip install -r requirements.txt"
            print_success "Python dependencies installed"
        else
            print_error "requirements.txt not found"
            exit 1
        fi
    else
        print_warning "Skipping Python environment setup (--skip-python)"
    fi

    # Step 4: Create logs directory
    print_header "Step 4: Creating Log Directory"

    run_command "mkdir -p $PROJECT_ROOT/logs"
    print_success "Log directory created"

    # Step 5: Validate configuration
    print_header "Step 5: Validating Configuration"

    if [ -f "$PROJECT_ROOT/.env" ]; then
        print_success ".env file exists"

        # Check for placeholder values
        if grep -q "YOUR" "$PROJECT_ROOT/.env"; then
            print_warning "Found placeholder values in .env file"
            echo "Please update the following in your .env file:"
            grep "YOUR" "$PROJECT_ROOT/.env" | sed 's/^/  - /'
        fi

        if grep -q "192.168.1.XXX" "$PROJECT_ROOT/.env"; then
            print_warning "Found default IP addresses in .env file"
            echo "Please update IP addresses for:"
            echo "  - POSTGRES_HOST"
            echo "  - REDIS_HOST"
            echo "  - N8N_HOST"
            echo "  - PROXMOX_HOST"
        fi

        # Test configuration loading
        if [ "$SKIP_PYTHON" = false ]; then
            print_warning "Testing configuration loading..."
            if python3 -c "from shared.config import config; from shared.config import validate_config; validate_config()"; then
                print_success "Configuration loaded successfully"
            else
                print_error "Configuration validation failed"
                echo "Please review and fix your .env file"
            fi
        fi
    else
        print_error ".env file not found"
        echo "Please copy .env.example to .env and configure it"
        exit 1
    fi

    # Step 6: Initialize Git repository (if not already initialized)
    print_header "Step 6: Git Repository"

    if [ -d "$PROJECT_ROOT/.git" ]; then
        print_success "Git repository already initialized"
    else
        print_warning "Initializing Git repository..."
        run_command "git init"
        print_success "Git repository initialized"

        print_warning "Don't forget to add a remote:"
        echo "  git remote add origin <your-git-url>"
    fi

    # Final summary
    print_header "SETUP COMPLETE!"

    echo -e "${GREEN}✓${NC} Your homelab agent system is ready!"
    echo ""
    echo "Next steps:"
    echo "  1. Update .env file with your actual credentials"
    echo "  2. Deploy PostgreSQL, n8n, Redis LXCs (if not already done)"
    echo "  3. Configure PostgreSQL (see README.md Step 3)"
    echo "  4. Create Telegram bot via @BotFather"
    echo "  5. Start building agents (see HOMELAB_AUTOMATION_MASTER_PLAN.md)"
    echo ""
    echo "To activate the Python environment:"
    echo "  source .venv/bin/activate"
    echo ""
    echo "To validate your configuration:"
    echo "  python3 shared/config.py"
    echo ""
    echo "To test the LLM router:"
    echo "  python3 shared/llm_router.py"
    echo ""
    echo "Full documentation: HOMELAB_AUTOMATION_MASTER_PLAN.md"
}

# Run main function
main "$@"
