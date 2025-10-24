#!/bin/bash
# PostgreSQL Setup Script for Homelab Agents
# Deploys PostgreSQL LXC and configures databases with pgvector extension

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_VMID="${POSTGRES_VMID:-200}"
POSTGRES_IP="${POSTGRES_IP:-192.168.1.50}"
POSTGRES_GATEWAY="${POSTGRES_GATEWAY:-192.168.1.1}"
POSTGRES_MEMORY="${POSTGRES_MEMORY:-2048}"
POSTGRES_CORES="${POSTGRES_CORES:-2}"
POSTGRES_DISK="${POSTGRES_DISK:-20}"
AUTO_CONFIRM=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --yes|-y)
            AUTO_CONFIRM=true
            shift
            ;;
    esac
done

# Source environment variables
if [ -f "/home/munky/homelab-agents/.env" ]; then
    source /home/munky/homelab-agents/.env
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PostgreSQL Setup for Homelab Agents${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to check if we're on Proxmox host
check_proxmox() {
    if ! command -v pct &> /dev/null; then
        echo -e "${RED}Error: This script must be run on a Proxmox host${NC}"
        exit 1
    fi
}

# Function to deploy PostgreSQL LXC using community script
deploy_lxc() {
    echo -e "\n${YELLOW}[1/6] Deploying PostgreSQL LXC...${NC}"

    # Check if VMID already exists
    if pct status $POSTGRES_VMID &> /dev/null; then
        echo -e "${YELLOW}Warning: LXC $POSTGRES_VMID already exists${NC}"
        read -p "Do you want to destroy and recreate? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            pct stop $POSTGRES_VMID 2>/dev/null || true
            pct destroy $POSTGRES_VMID
        else
            echo -e "${GREEN}Skipping LXC creation, using existing container${NC}"
            return 0
        fi
    fi

    # Download and run PostgreSQL install script
    bash -c "$(wget -qLO - https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/postgresql.sh)" \
        -s --verbose \
        -CTID="$POSTGRES_VMID" \
        -HOSTNAME="postgres" \
        -DISK_SIZE="$POSTGRES_DISK" \
        -CORE_COUNT="$POSTGRES_CORES" \
        -RAM_SIZE="$POSTGRES_MEMORY" \
        -BRG="vmbr0" \
        -NET="dhcp" \
        -GATE="$POSTGRES_GATEWAY" \
        -APT_CACHER="" \
        -APT_CACHER_IP="" \
        -DISABLEIP6="yes" \
        -MTU="" \
        -SD="" \
        -NS="" \
        -MAC="" \
        -VLAN="" \
        -SSH="no" \
        -VERB="yes" || true

    # Give the container time to start
    sleep 10

    echo -e "${GREEN}✓ PostgreSQL LXC deployed${NC}"
}

# Function to install pgvector extension
install_pgvector() {
    echo -e "\n${YELLOW}[2/6] Installing pgvector extension...${NC}"

    pct exec $POSTGRES_VMID -- bash -c "
        apt-get update
        apt-get install -y postgresql-contrib build-essential git

        # Clone and build pgvector
        cd /tmp
        git clone --branch v0.5.0 https://github.com/pgvector/pgvector.git
        cd pgvector
        make
        make install

        # Clean up
        cd /
        rm -rf /tmp/pgvector
    "

    echo -e "${GREEN}✓ pgvector extension installed${NC}"
}

# Function to configure PostgreSQL
configure_postgresql() {
    echo -e "\n${YELLOW}[3/6] Configuring PostgreSQL...${NC}"

    # Allow remote connections
    pct exec $POSTGRES_VMID -- bash -c "
        # Enable remote connections
        echo \"listen_addresses = '*'\" >> /etc/postgresql/*/main/postgresql.conf

        # Configure pg_hba.conf for remote access
        echo \"host    all             all             0.0.0.0/0               md5\" >> /etc/postgresql/*/main/pg_hba.conf

        # Restart PostgreSQL
        systemctl restart postgresql
    "

    echo -e "${GREEN}✓ PostgreSQL configured for remote access${NC}"
}

# Function to create databases and users
create_databases() {
    echo -e "\n${YELLOW}[4/6] Creating databases and users...${NC}"

    # Create SQL script
    cat > /tmp/setup_dbs.sql <<EOF
-- Enable pgvector extension in template1 (will be copied to new databases)
\c template1
CREATE EXTENSION IF NOT EXISTS vector;

-- Create databases
CREATE DATABASE ${POSTGRES_DB_MEMORY:-agent_memory};
CREATE DATABASE ${POSTGRES_DB_CHECKPOINTS:-agent_checkpoints};
CREATE DATABASE ${POSTGRES_DB_N8N:-n8n};

-- Create users
CREATE USER ${POSTGRES_USER_MEMORY:-mem0_user} WITH PASSWORD '${POSTGRES_PASSWORD_MEMORY}';
CREATE USER ${POSTGRES_USER_AGENT:-agent_user} WITH PASSWORD '${POSTGRES_PASSWORD_AGENT}';
CREATE USER ${POSTGRES_USER_N8N:-n8n_user} WITH PASSWORD '${POSTGRES_PASSWORD_N8N}';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB_MEMORY:-agent_memory} TO ${POSTGRES_USER_MEMORY:-mem0_user};
GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB_CHECKPOINTS:-agent_checkpoints} TO ${POSTGRES_USER_AGENT:-agent_user};
GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB_N8N:-n8n} TO ${POSTGRES_USER_N8N:-n8n_user};

-- Enable pgvector in each database
\c ${POSTGRES_DB_MEMORY:-agent_memory}
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO ${POSTGRES_USER_MEMORY:-mem0_user};

\c ${POSTGRES_DB_CHECKPOINTS:-agent_checkpoints}
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO ${POSTGRES_USER_AGENT:-agent_user};

\c ${POSTGRES_DB_N8N:-n8n}
GRANT ALL ON SCHEMA public TO ${POSTGRES_USER_N8N:-n8n_user};
EOF

    # Copy SQL script to container
    pct push $POSTGRES_VMID /tmp/setup_dbs.sql /tmp/setup_dbs.sql

    # Execute SQL script
    pct exec $POSTGRES_VMID -- su - postgres -c "psql -f /tmp/setup_dbs.sql"

    # Clean up
    rm /tmp/setup_dbs.sql
    pct exec $POSTGRES_VMID -- rm /tmp/setup_dbs.sql

    echo -e "${GREEN}✓ Databases and users created${NC}"
}

# Function to set static IP
set_static_ip() {
    echo -e "\n${YELLOW}[5/6] Setting static IP address...${NC}"

    pct exec $POSTGRES_VMID -- bash -c "
        cat > /etc/network/interfaces <<EOF2
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address ${POSTGRES_IP}/24
    gateway ${POSTGRES_GATEWAY}
EOF2

        # Restart networking
        systemctl restart networking
    "

    # Update Proxmox configuration
    pct set $POSTGRES_VMID -net0 name=eth0,bridge=vmbr0,ip=${POSTGRES_IP}/24,gw=${POSTGRES_GATEWAY}

    # Restart container to apply changes
    pct reboot $POSTGRES_VMID
    sleep 15

    echo -e "${GREEN}✓ Static IP configured: ${POSTGRES_IP}${NC}"
}

# Function to test connection
test_connection() {
    echo -e "\n${YELLOW}[6/6] Testing database connection...${NC}"

    # Test from host using psql (if available)
    if command -v psql &> /dev/null; then
        echo "Testing connection to agent_memory database..."
        PGPASSWORD="${POSTGRES_PASSWORD_MEMORY}" psql -h ${POSTGRES_IP} -U ${POSTGRES_USER_MEMORY} -d ${POSTGRES_DB_MEMORY} -c "SELECT version();" || true
    else
        echo -e "${YELLOW}psql not available on host, testing from container...${NC}"
        pct exec $POSTGRES_VMID -- su - postgres -c "psql -c 'SELECT version();'"
    fi

    echo -e "${GREEN}✓ Database connection test complete${NC}"
}

# Function to display summary
display_summary() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${GREEN}PostgreSQL Setup Complete!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "Container ID: ${YELLOW}${POSTGRES_VMID}${NC}"
    echo -e "IP Address: ${YELLOW}${POSTGRES_IP}:5432${NC}"
    echo -e ""
    echo -e "Databases created:"
    echo -e "  - ${POSTGRES_DB_MEMORY} (user: ${POSTGRES_USER_MEMORY})"
    echo -e "  - ${POSTGRES_DB_CHECKPOINTS} (user: ${POSTGRES_USER_AGENT})"
    echo -e "  - ${POSTGRES_DB_N8N} (user: ${POSTGRES_USER_N8N})"
    echo -e ""
    echo -e "Extensions installed:"
    echo -e "  - pgvector (v0.5.0) - Vector similarity search"
    echo -e ""
    echo -e "Connection strings:"
    echo -e "${BLUE}Agent Memory:${NC}"
    echo -e "  postgresql://${POSTGRES_USER_MEMORY}:****@${POSTGRES_IP}:5432/${POSTGRES_DB_MEMORY}"
    echo -e "${BLUE}Agent Checkpoints:${NC}"
    echo -e "  postgresql://${POSTGRES_USER_AGENT}:****@${POSTGRES_IP}:5432/${POSTGRES_DB_CHECKPOINTS}"
    echo -e ""
    echo -e "Next steps:"
    echo -e "  1. Update .env file with POSTGRES_HOST=${POSTGRES_IP}"
    echo -e "  2. Test Mem0 MCP: python mcp_servers/mem0_mcp/server.py"
    echo -e "  3. Test agents: python run_agents.py --mode interactive"
    echo -e "${BLUE}========================================${NC}"
}

# Main execution
main() {
    # Uncomment if running on Proxmox host
    # check_proxmox

    echo -e "${YELLOW}This script will:${NC}"
    echo -e "  1. Deploy PostgreSQL LXC (VMID: ${POSTGRES_VMID})"
    echo -e "  2. Install pgvector extension"
    echo -e "  3. Configure remote access"
    echo -e "  4. Create 3 databases with users"
    echo -e "  5. Set static IP: ${POSTGRES_IP}"
    echo -e "  6. Test connections"
    echo -e ""

    if [ "$AUTO_CONFIRM" = false ]; then
        read -p "Continue? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo -e "${RED}Aborted${NC}"
            exit 0
        fi
    else
        echo -e "${GREEN}Auto-confirming (--yes flag)${NC}"
    fi

    deploy_lxc
    install_pgvector
    configure_postgresql
    create_databases
    set_static_ip
    test_connection
    display_summary
}

# Run main function
main
