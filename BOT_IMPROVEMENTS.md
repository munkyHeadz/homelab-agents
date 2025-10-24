# Telegram Bot Improvements

## Overview

The Telegram bot has been completely overhauled with improved formatting, better error handling, new commands, and automatic update capabilities.

## What Was Fixed

### 1. Output Formatting
**Before:** Raw JSON/text dumps from MCP servers - messy and hard to read
**After:** Clean, structured, human-readable output with:
- Color-coded status indicators (🟢 🟡 🔴)
- Formatted data (bytes, percentages, uptime)
- Hierarchical organization
- Proper emoji usage for visual clarity

### 2. Data Parsing
**Added helper functions:**
- `parse_json_response()` - Extract and parse JSON from MCP responses
- `parse_proxmox_node_status()` - Format Proxmox node data nicely
- `parse_docker_info()` - Format Docker system info
- `parse_vm_list()` - Format VM/container lists with status
- `parse_container_list()` - Format Docker container lists
- `format_bytes()` - Human-readable byte formatting
- `format_uptime()` - Human-readable uptime (8d 4h 23m)
- `format_percentage()` - Percentage with color-coded indicators

### 3. Command Improvements

#### Fixed Commands:
- `/status` - Now shows comprehensive system overview with formatted data
- `/node` - Properly formatted Proxmox node status
- `/monitor` - Clean resource monitoring display
- `/docker` - Formatted Docker system information
- `/vms` - Organized list of VMs and containers with status

#### New Commands:
- `/uptime` - Show bot uptime and system uptime
- `/containers` - List all Docker containers with detailed status
- `/infra` - Infrastructure overview
- `/update` - Automatic update mechanism (git pull + restart)

### 4. Automatic Updates
The `/update` command now:
1. Runs `git pull` to get latest code
2. Shows update output
3. Automatically restarts the bot service
4. Notifies user before restart

Usage: Just send `/update` and the bot will update itself!

### 5. Better Error Handling
- All commands now use try/except blocks
- Detailed error messages for debugging
- Graceful fallbacks when parsing fails
- Timeout handling for long operations

### 6. UI/UX Improvements
- Messages update in-place (using `edit_text`)
- Loading indicators ("🔄 Checking...")
- Consistent emoji usage
- Cleaner command list in /help
- Better organized /start menu

## Available Commands

### System Status
```
/status     - Complete system overview with all metrics
/uptime     - Bot and system uptime information
/monitor    - Real-time resource monitoring
```

### Proxmox Management
```
/node       - Detailed Proxmox node status
/vms        - List all VMs and LXC containers with status
/infra      - Infrastructure overview
```

### Docker Management
```
/docker     - Docker system information
/containers - List all Docker containers with detailed status
```

### Bot Management
```
/update     - Pull latest code and restart bot
/help       - Show command reference
/start      - Show welcome message
```

### Natural Language
Just send a message like:
- "Show status of LXC 101"
- "List running Docker containers"
- "Check system resources"

## Example Output

### /status Command
```
📊 System Status Report
🕐 2025-10-24 10:43:30 UTC

🖥️ Node: fjeld

CPU Usage: 🟢 35.2%
Memory: 45.2 GB / 62.7 GB (🟡 72.1%)
Uptime: 8d 2h 15m
Load Average: 3.45

🐳 Docker System

Containers: 12 total
  └ Running: 10 | Stopped: 2 | Paused: 0
Images: 45
Version: 28.5.1
Storage Driver: overlay2

🤖 Bot Status
Uptime: 2h 15m
Health: 🟢 Operational
```

### /vms Command
```
📦 LXC Containers
🟢 100 - arr
  └ CPU: 5.2% | Mem: 512.0 MB
🟢 101 - docker
  └ CPU: 12.5% | Mem: 2.1 GB
🟢 104 - homelab-agents
  └ CPU: 8.3% | Mem: 89.3 MB

🖥️ Virtual Machines
🟢 102 - unifiOS
  └ CPU: 25.1% | Mem: 4.0 GB
```

### /containers Command
```
🐳 Docker Containers

🟢 nginx-proxy
  └ Image: nginx:latest
  └ Status: Up 8 days

🟢 postgres-db
  └ Image: postgres:15
  └ Status: Up 8 days

🔴 temp-worker
  └ Image: python:3.11
  └ Status: Exited (0) 2 hours ago
```

## Technical Details

### Deployment
- **Location:** LXC 104 at `/root/homelab-agents`
- **Service:** `homelab-telegram-bot.service`
- **Metrics:** http://192.168.1.102:8000/metrics
- **Logs:** `sudo pct exec 104 -- journalctl -u homelab-telegram-bot -f`

### Code Structure
```
interfaces/telegram_bot.py (693 lines)
├── Helper Functions (68-237)
│   ├── parse_json_response()
│   ├── format_bytes()
│   ├── format_uptime()
│   ├── format_percentage()
│   ├── parse_proxmox_node_status()
│   ├── parse_docker_info()
│   ├── parse_vm_list()
│   ├── parse_container_list()
│   └── _format_text_data()
│
├── Command Handlers (239-642)
│   ├── start_command()
│   ├── help_command()
│   ├── status_command()
│   ├── uptime_command()
│   ├── node_command()
│   ├── vms_command()
│   ├── docker_command()
│   ├── containers_command()
│   ├── monitor_command()
│   ├── infra_command()
│   ├── update_command()
│   └── handle_message()
│
└── Main Application (648-692)
    └── run() - Register all handlers
```

### Performance
- Startup time: ~6 seconds
- Memory usage: ~89 MB
- Response time: 2-8 seconds per command
- Metrics tracking: All commands instrumented

## Testing

### Test the bot in Telegram:

1. **Basic Commands**
   ```
   /start
   /help
   /status
   ```

2. **Proxmox Commands**
   ```
   /node
   /vms
   ```

3. **Docker Commands**
   ```
   /docker
   /containers
   ```

4. **New Features**
   ```
   /uptime
   /infra
   /update
   ```

5. **Natural Language**
   ```
   Show me all running containers
   What is the system status?
   Check Proxmox node
   ```

## Automatic Updates

To update the bot with new features:

1. Push code to the repository
2. In Telegram, send `/update`
3. Bot will pull latest code and restart
4. New features are immediately available

**Note:** The `/update` command runs from within LXC 104, so it needs:
- Git repository initialized at `/root/homelab-agents`
- Systemd service `homelab-telegram-bot` configured
- Proper permissions for systemctl restart

## Monitoring

### Check Bot Status
```bash
sudo pct exec 104 -- systemctl status homelab-telegram-bot
```

### View Live Logs
```bash
sudo pct exec 104 -- journalctl -u homelab-telegram-bot -f
```

### Check Metrics
```bash
curl http://192.168.1.102:8000/metrics | grep telegram
```

## Next Steps

Potential future improvements:
1. **Scheduled Reports** - Daily/weekly status summaries
2. **Alert Integration** - Forward Prometheus alerts to Telegram
3. **Interactive Buttons** - Telegram inline keyboards for actions
4. **VM Control** - Start/stop VMs from Telegram
5. **Container Management** - Restart/stop containers
6. **Backup Status** - Check backup job status
7. **Network Monitoring** - Integration with Unifi/Tailscale data

## Troubleshooting

### Bot not responding?
1. Check service: `sudo pct exec 104 -- systemctl status homelab-telegram-bot`
2. Check logs: `sudo pct exec 104 -- journalctl -u homelab-telegram-bot -n 50`
3. Restart: `sudo pct exec 104 -- systemctl restart homelab-telegram-bot`

### Commands returning errors?
1. Check agent health: `curl http://192.168.1.102:8000/metrics | grep agent_health`
2. Verify MCP servers are accessible
3. Check Proxmox API: https://192.168.1.99:8006
4. Check Docker API: Ensure Docker daemon is running

### /update not working?
1. Ensure git repo is initialized
2. Check git remote is configured
3. Verify systemctl permissions
4. Check if running inside LXC 104

---

**Bot Status:** ✅ Deployed and Running
**Version:** v2.0 (Improved)
**Last Updated:** 2025-10-24
