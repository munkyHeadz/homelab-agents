# MCP Servers - Homelab Automation

This directory contains Model Context Protocol (MCP) servers that provide tools for autonomous agents to interact with homelab infrastructure and services.

## What is MCP?

Model Context Protocol (MCP) is an open standard that enables AI agents to securely interact with external systems through a standardized interface. Each MCP server exposes a set of tools that agents can discover and invoke.

## Available MCP Servers

### Infrastructure Management

#### 1. **Proxmox MCP Server** (`proxmox_mcp/`)
Manages Proxmox VE infrastructure including VMs, LXC containers, and resources.

**Tools:**
- `list_vms` - List all VMs and containers
- `get_vm_status` - Get detailed VM/container status
- `start_vm`, `stop_vm`, `reboot_vm` - VM lifecycle control
- `create_lxc` - Create new LXC containers
- `delete_vm` - Remove VMs/containers
- `get_node_status` - Node resource usage
- `list_storage` - Storage devices and usage
- `create_backup`, `restore_backup` - Backup operations
- `get_cluster_resources` - Cluster-wide overview

**Environment Variables:**
```bash
PROXMOX_HOST=192.168.1.XXX
PROXMOX_PORT=8006
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_password
PROXMOX_TOKEN_ID=root@pam!agent-token  # Recommended
PROXMOX_TOKEN_SECRET=your_token_secret
PROXMOX_NODE=fjeld
PROXMOX_VERIFY_SSL=false
```

**Usage:**
```bash
python mcp_servers/proxmox_mcp/server.py
```

---

#### 2. **Docker MCP Server** (`docker_mcp/`)
Manages Docker containers, images, networks, and volumes.

**Tools:**
- `list_containers` - List all containers
- `get_container_details` - Detailed container info
- `start_container`, `stop_container`, `restart_container` - Container lifecycle
- `remove_container` - Delete containers
- `get_container_logs` - Retrieve container logs
- `get_container_stats` - Real-time resource usage
- `list_images`, `pull_image`, `remove_image` - Image management
- `list_networks`, `list_volumes` - Network/volume listing
- `prune_system` - Clean up unused resources
- `get_system_info` - Docker system information

**Environment Variables:**
```bash
DOCKER_HOST=unix:///var/run/docker.sock
DOCKER_TLS_VERIFY=0
```

**Usage:**
```bash
python mcp_servers/docker_mcp/server.py
```

---

### Networking & Security

#### 3. **Tailscale MCP Server** (`tailscale_mcp/`)
Manages Tailscale VPN network, ACLs, and devices.

**Tools:**
- `list_tailscale_devices` - List all devices in tailnet
- `get_tailscale_device` - Device details
- `authorize_tailscale_device` - Authorize new devices
- `remove_tailscale_device` - Remove devices
- `get_tailscale_acl` - Get ACL policy
- `update_tailscale_acl` - Update ACL policy
- `get_tailscale_dns` - DNS configuration
- `update_tailscale_dns` - Update DNS nameservers
- `enable_subnet_routes` - Configure subnet routing

**Environment Variables:**
```bash
TAILSCALE_API_KEY=tskey-api-YOUR_KEY
TAILSCALE_TAILNET=your-tailnet.ts.net
```

**Usage:**
```bash
python mcp_servers/tailscale_mcp/server.py
```

---

#### 4. **Cloudflare MCP Server** (`cloudflare_mcp/`)
Manages Cloudflare DNS, tunnels, WAF, and CDN.

**Tools:**
- `list_dns_records` - List all DNS records
- `create_dns_record`, `update_dns_record`, `delete_dns_record` - DNS management
- `list_cloudflare_tunnels` - List all tunnels
- `get_tunnel_status` - Tunnel status
- `purge_cache` - Purge CDN cache
- `get_zone_analytics` - Traffic analytics
- `get_firewall_rules`, `create_firewall_rule` - WAF management

**Environment Variables:**
```bash
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_ZONE_ID=your_zone_id
CLOUDFLARE_ACCOUNT_ID=your_account_id
```

**Usage:**
```bash
python mcp_servers/cloudflare_mcp/server.py
```

---

#### 5. **Unifi MCP Server** (`unifi_mcp/`)
Manages Unifi network infrastructure (clients, devices, firewall).

**Tools:**
- `list_unifi_clients` - List connected clients
- `get_client_details` - Client information
- `block_client`, `unblock_client` - Client access control
- `reconnect_client` - Force client reconnection
- `list_unifi_devices` - List APs, switches, gateways
- `get_device_details` - Device information
- `reboot_device` - Reboot Unifi devices
- `get_network_stats` - Network health statistics
- `list_firewall_rules`, `create_firewall_rule` - Firewall management
- `create_guest_voucher` - Generate guest WiFi vouchers

**Environment Variables:**
```bash
UNIFI_HOST=192.168.1.XXX
UNIFI_PORT=8443
UNIFI_USERNAME=admin
UNIFI_PASSWORD=your_password
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
```

**Usage:**
```bash
python mcp_servers/unifi_mcp/server.py
```

---

#### 6. **Pi-hole MCP Server** (`pihole_mcp/`)
Manages Pi-hole DNS ad blocking.

**Tools:**
- `get_pihole_summary` - Summary statistics
- `enable_pihole_blocking`, `disable_pihole_blocking` - Toggle blocking
- `get_pihole_top_items` - Top domains and blocks
- `get_pihole_top_clients` - Top clients
- `whitelist_domain`, `blacklist_domain` - Domain list management
- `remove_whitelist_domain`, `remove_blacklist_domain` - Remove from lists
- `update_pihole_gravity` - Update blocklists
- `get_recent_blocked` - Recently blocked domains
- `get_forward_destinations` - Upstream DNS servers
- `get_query_types` - Query type statistics

**Environment Variables:**
```bash
PIHOLE_HOST=192.168.1.XXX
PIHOLE_PORT=80
PIHOLE_API_TOKEN=your_api_token
```

**Usage:**
```bash
python mcp_servers/pihole_mcp/server.py
```

---

### Agent Intelligence

#### 7. **Mem0 Memory MCP Server** (`mem0_mcp/`)
Provides persistent memory for autonomous agents using Mem0 + PostgreSQL + pgvector.

**Tools:**
- `add_memory` - Store new memory
- `search_memories` - Semantic memory search
- `get_all_memories` - Retrieve all memories
- `update_memory` - Update existing memory
- `delete_memory` - Delete specific memory
- `delete_all_memories` - Bulk delete (use with caution)
- `get_memory_history` - Memory version history
- `summarize_memories` - AI-generated memory summary

**Environment Variables:**
```bash
POSTGRES_HOST=192.168.1.XXX
POSTGRES_PORT=5432
POSTGRES_DB_MEMORY=agent_memory
POSTGRES_USER_MEMORY=mem0_user
POSTGRES_PASSWORD_MEMORY=your_password
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Usage:**
```bash
python mcp_servers/mem0_mcp/server.py
```

---

## Running MCP Servers

### Standalone Mode
Each MCP server can run independently:

```bash
cd /home/munky/homelab-agents
python -m mcp_servers.proxmox_mcp.server
```

### Agent Integration
Agents connect to MCP servers via stdio:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to Proxmox MCP server
server_params = StdioServerParameters(
    command="python",
    args=["mcp_servers/proxmox_mcp/server.py"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List available tools
        tools = await session.list_tools()

        # Call a tool
        result = await session.call_tool("list_vms", {"type": "all"})
```

### n8n Integration
MCP servers can be triggered from n8n workflows via webhooks or HTTP requests to the agents.

---

## Adding New MCP Servers

To add a new MCP server:

1. **Create directory:**
   ```bash
   mkdir mcp_servers/myservice_mcp
   ```

2. **Create server.py:**
   ```python
   from mcp.server import Server
   import mcp.types as types

   server = Server("myservice-mcp")

   @server.list_tools()
   async def handle_list_tools() -> List[types.Tool]:
       return [
           types.Tool(
               name="my_tool",
               description="Description of what this tool does",
               inputSchema={
                   "type": "object",
                   "properties": {
                       "param": {"type": "string"}
                   },
                   "required": ["param"]
               }
           )
       ]

   @server.call_tool()
   async def handle_call_tool(name: str, arguments: dict):
       if name == "my_tool":
           # Implement tool logic
           return [types.TextContent(type="text", text="Result")]
   ```

3. **Add to .env.example:**
   ```bash
   # My Service
   MYSERVICE_ENABLED=true
   MYSERVICE_HOST=192.168.1.XXX
   MYSERVICE_API_KEY=your_key
   ```

4. **Update requirements.txt** if new dependencies are needed.

5. **Document in this README.**

---

## Security Best Practices

1. **Never commit .env files** - Use .env.example as template
2. **Use API tokens over passwords** where possible
3. **Rotate credentials quarterly**
4. **Use least-privilege access** for service accounts
5. **Enable SSL verification** in production
6. **Firewall MCP servers** to only allow agent access
7. **Audit tool usage** through structured logging

---

## Monitoring MCP Servers

All MCP servers log to the shared logging system:

```python
from shared.logging import get_logger

logger = get_logger(__name__)
logger.info("Tool executed", tool_name="list_vms", user="agent")
```

Prometheus metrics are automatically collected for:
- Tool invocation counts
- Tool execution duration
- Error rates
- Memory usage

---

## Troubleshooting

### MCP Server Won't Start
- Check environment variables are set in `.env`
- Verify service is reachable (network, firewall)
- Check logs: `tail -f logs/agents.log`

### Tool Execution Fails
- Verify credentials are correct
- Check service API is accessible
- Review error message in tool response
- Test API manually with curl/httpie

### Memory Server Issues
- Ensure PostgreSQL is running
- Verify pgvector extension is installed
- Check database connection string
- Run: `psql -h $POSTGRES_HOST -U $POSTGRES_USER_MEMORY -d $POSTGRES_DB_MEMORY`

---

## Next Steps

1. **Implement remaining MCP servers:**
   - Traefik MCP (reverse proxy management)
   - Portainer MCP (Docker GUI management)
   - Netbox MCP (IPAM/DCIM)
   - PBS MCP (Proxmox Backup Server)

2. **Create orchestrator agent** that coordinates multiple MCP servers

3. **Build n8n workflows** for common automation patterns

4. **Set up monitoring dashboards** for MCP server health

---

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Anthropic MCP Documentation](https://docs.anthropic.com/en/docs/agents/mcp)
- [Homelab Automation Master Plan](../HOMELAB_AUTOMATION_MASTER_PLAN.md)
