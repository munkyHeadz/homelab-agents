# 🤖 Autonomous Self-Healing System

## Overview

The Homelab Agent System now includes a fully autonomous self-healing capability that continuously monitors infrastructure, diagnoses issues, and automatically fixes problems when safe to do so.

## Version 2.5 Features

### 🏥 Autonomous Health Agent

The **AutonomousHealthAgent** provides intelligent, self-improving infrastructure management:

#### Continuous Monitoring
- Checks system health every 60 seconds
- Monitors Proxmox node (CPU, memory, disk)
- Tracks VM/Container status and resources
- Watches Docker daemon and container health
- Detects MCP server connectivity issues

#### Intelligent Diagnosis
- Uses Claude AI to analyze root causes
- Generates remediation recommendations
- Assesses risk levels for each action
- Learns from successful/failed fixes

#### Risk-Based Auto-Healing
- **LOW Risk**: Auto-fix immediately (restart containers, clear cache)
- **MEDIUM Risk**: Request approval via Telegram
- **HIGH Risk**: Always ask, never auto-execute

### 🎮 Interactive Telegram Interface

#### New Commands

**VM/Container Control:**
```
/start_vm <id>        - Start a VM or LXC container
/stop_vm <id>         - Stop a VM or LXC container
/restart_vm <id>      - Restart a VM or LXC container
```

**Docker Control:**
```
/restart_container <name>  - Restart Docker container
/stop_container <name>     - Stop Docker container
```

**Health Monitoring:**
```
/health                    - View system health report
/enable_autohealing        - Start autonomous monitoring
/disable_autohealing       - Stop autonomous monitoring
```

**Backup Status:**
```
/backup                    - Show recent backup status
/backup <vmid>             - Show backup status for specific VM
```

**Interactive Menu:**
```
/menu                      - Interactive button menu
```

#### Approval Workflow

When a **MEDIUM** or **HIGH** risk issue is detected, you'll receive a Telegram message with:

**Example:**
```
⚠️ Action Approval Required

Component: docker_container_nginx
Issue: Container exited unexpectedly
Severity: 🟠 UNHEALTHY
Risk Level: MEDIUM

Suggested Fix: Restart container 'nginx-proxy'

Metrics:
{
  "container": "nginx-proxy",
  "state": "exited",
  "status": "Exited (1) 5 minutes ago"
}

Should I proceed with this action?

[✅ Approve] [❌ Reject]
```

**Response Options:**
- **✅ Approve**: System executes the fix and reports results
- **❌ Reject**: Issue remains unresolved, no action taken

### 🔧 Auto-Healing Capabilities

#### What It Can Fix Automatically (LOW Risk)

1. **Restart Crashed Containers**
   - Docker containers that exited recently
   - Unhealthy containers failing health checks

2. **Clean Up Disk Space**
   - Prune unused Docker images/volumes
   - Clear system caches
   - Remove old logs

3. **Restart Failed Services**
   - Services that stopped unexpectedly
   - MCP server reconnections

#### What Requires Approval (MEDIUM/HIGH Risk)

1. **VM/Container Reboots**
   - Critical services (LXC 104 - homelab agents)
   - Production VMs

2. **Memory Management**
   - Clear memory caches
   - Stop non-essential services

3. **Configuration Changes**
   - Network settings
   - Resource allocations

## Usage Guide

### 1. Enable Auto-Healing

```
/enable_autohealing
```

**Response:**
```
✅ Auto-Healing Enabled

The system will now:
• Monitor infrastructure every 60 seconds
• Auto-fix low-risk issues automatically
• Request approval for risky actions
• Send notifications to this chat

Use /health to view current status
Use /disable_autohealing to stop
```

### 2. Monitor System Health

```
/health
```

**Sample Output:**
```
🏥 System Health Report
🕐 2025-10-24 16:30:15 UTC

Active Issues: 2
Resolved Today: 5
Pending Approvals: 1

Issues by Severity:
🔴 Critical: 0
🟠 Unhealthy: 1
🟡 Degraded: 1

📋 Active Issues:

• docker_container_redis: Container stopped unexpectedly
• proxmox_node: High memory usage (92.5%)

✅ Recent Resolutions:

• docker_container_nginx: Restarted crashed container
• proxmox_node: Cleaned up disk space
• docker_container_postgres: Restarted unhealthy container
```

### 3. Control VMs and Containers

```
# Start a stopped VM
/start_vm 104

# Restart a problematic container
/restart_container nginx-proxy

# Stop a container for maintenance
/stop_container temp-worker
```

### 4. Check Backup Status

```
# All VMs
/backup

# Specific VM
/backup 102
```

### 5. Use Interactive Menu

```
/menu
```

Opens an interactive button menu with quick access to:
- 📊 Status
- 🖥️ Node Info
- 📦 VMs
- 🐳 Docker
- 🏥 Health
- 💾 Backups

## Architecture

```
┌─────────────────────────────────────────────────┐
│     Autonomous Health Agent (Every 60s)         │
│  ┌──────────────────────────────────────────┐  │
│  │ 1. Monitor: Proxmox, Docker, VMs, etc    │  │
│  │ 2. Detect: Find issues and anomalies     │  │
│  │ 3. Diagnose: Claude analyzes root cause  │  │
│  │ 4. Assess: Determine risk level          │  │
│  │ 5. Act: Fix or request approval          │  │
│  │ 6. Report: Notify via Telegram           │  │
│  │ 7. Learn: Remember successful fixes      │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
    [AUTO-FIX]            [ASK PERMISSION]
    LOW Risk              MED/HIGH Risk
         ↓                     ↓
    Execute & Report      Telegram Buttons
                         [✅ Approve][❌ Reject]
                              ↓
                         Execute if Approved
                              ↓
                         Report Results
```

## Health Check Matrix

| Component | Check | Threshold | Action | Risk |
|-----------|-------|-----------|--------|------|
| Proxmox Node | CPU Usage | > 90% | Identify high-CPU processes | LOW |
| Proxmox Node | Memory | > 90% | Clear caches / Stop services | MEDIUM |
| Proxmox Node | Disk Space | > 85% | Clean up old data | LOW |
| VM/Container | Stopped | Critical services | Start VM/Container | MEDIUM |
| VM/Container | High CPU | > 90% | Investigate process | LOW |
| Docker Container | Exited | Recent exit | Restart container | LOW |
| Docker Container | Unhealthy | Health check fail | Restart container | LOW |
| Docker Daemon | Not responding | Connection fail | Restart daemon | HIGH |

## Notification Examples

### Auto-Fix Notification

```
🔧 Auto-Healing Action

Component: docker_container_redis
Issue: Docker container 'redis' exited: Exited (1) 2 minutes ago
Action: Restart container 'redis'
Result: ✅ Successfully restarted container 'redis'
```

### Approval Request

```
⚠️ Action Approval Required

Component: lxc_104
Issue: Critical lxc 'homelab-agents' (ID: 104) is stopped
Severity: 🔴 CRITICAL
Risk Level: MEDIUM

Suggested Fix: Start lxc 104

Metrics:
{
  "vmid": 104,
  "name": "homelab-agents",
  "status": "stopped"
}

Should I proceed with this action?

[✅ Approve] [❌ Reject]
```

### Resolution Report

```
🔧 Action executed for lxc_104
✅ Successfully started VM/Container 104
```

## Advanced Features

### Learning from Actions

The system tracks:
- Successful auto-fixes
- Failed remediation attempts
- Approval decisions
- Resolution times

This data helps improve future diagnosis and decision-making.

### Issue Lifecycle

1. **Detected** → Issue found during monitoring
2. **Diagnosed** → Claude analyzes root cause
3. **Assessed** → Risk level determined
4. **Acted** → Fix applied or approval requested
5. **Resolved** → Issue fixed successfully
6. **Learned** → Pattern stored for future reference

### Health Status Levels

- **🟢 HEALTHY**: All systems operating normally
- **🟡 DEGRADED**: Minor issues, still functional
- **🟠 UNHEALTHY**: Significant issues requiring attention
- **🔴 CRITICAL**: Severe issues, immediate action needed

## Best Practices

### When to Enable Auto-Healing

**✅ Good for:**
- Development environments
- Non-critical infrastructure
- Systems with good monitoring
- When you're available to respond to approvals

**⚠️ Use with caution:**
- Production systems
- Systems with complex dependencies
- During major changes
- When approval response may be delayed

### Monitoring the Auto-Healer

1. **Check health regularly**: `/health`
2. **Review resolved issues**: See what was fixed automatically
3. **Adjust risk levels**: Modify if too aggressive/conservative
4. **Monitor notifications**: Don't miss approval requests

### Responding to Approvals

**Consider:**
- Current system load
- Time of day
- Other running operations
- Potential impact

**If unsure:**
- Reject and investigate manually
- Check logs first
- Verify system state

## Troubleshooting

### Auto-Healing Not Working

```bash
# Check if enabled
/health

# Enable if needed
/enable_autohealing

# Check logs
sudo pct exec 104 -- journalctl -u homelab-telegram-bot -f
```

### Too Many Notifications

```bash
# Disable temporarily
/disable_autohealing

# Adjust thresholds in autonomous_health_agent.py
# Increase monitoring interval from 60 to 300 seconds
```

### Missing Approval Requests

- Check Telegram notifications are enabled
- Verify bot has permission to send messages
- Check `allowed_users` in config

### Actions Not Executing

- Verify MCP servers are accessible
- Check Proxmox/Docker API credentials
- Review error logs

## Configuration

### Monitoring Interval

Default: 60 seconds

To change, edit in `autonomous_health_agent.py`:
```python
async def run_monitoring_loop(self, interval: int = 300):  # 5 minutes
```

### Risk Level Adjustments

Modify thresholds in `_check_*_health()` methods:
```python
# More aggressive
if cpu_usage > 85:  # instead of 90

# More conservative
if cpu_usage > 95:  # instead of 90
```

### Critical Services List

Edit in `_check_vm_health()`:
```python
critical_ids = [104, 101, 200]  # Add your critical VM IDs
```

## Metrics and Monitoring

### Prometheus Metrics

```
# Health agent status
agent_health_status{agent="autonomous_health_agent"}

# Active issues count
health_active_issues_total

# Auto-fix success rate
health_autofix_success_rate

# Approval response time
health_approval_response_seconds
```

### Grafana Dashboard

Create dashboard with panels for:
- Active issues over time
- Auto-fix success rate
- Issues by severity
- Resolution times
- Approval response times

## Security Considerations

### Authorization

- Only authorized Telegram users can approve actions
- User ID verification for all commands
- Audit log of all approvals and actions

### Risk Management

- Multi-level risk assessment
- Conservative defaults
- Human-in-the-loop for risky operations
- Rollback capabilities (planned)

### Data Privacy

- No sensitive data in Telegram messages
- Credentials never exposed
- Encrypted bot token storage

## Future Enhancements

### Planned Features

1. **Rollback Capability**
   - Automatic rollback on failed fixes
   - Snapshot before risky operations

2. **Predictive Monitoring**
   - Machine learning for anomaly detection
   - Predictive failure analysis

3. **Advanced Remediation**
   - Multi-step fix workflows
   - Dependency-aware actions

4. **Enhanced Learning**
   - Pattern recognition across issues
   - Success probability scoring

5. **Integration Extensions**
   - Alert forwarding from Prometheus
   - Webhook receivers for external systems
   - n8n workflow automation

## Examples

### Example 1: Container Crash

**Scenario**: nginx-proxy container crashes

**Flow:**
1. Health agent detects: Container exited (exit code 1)
2. Diagnoses: Application error, safe to restart
3. Assesses risk: LOW (standard restart)
4. Auto-fixes: Restarts container
5. Reports: Sends success notification to Telegram

**Notification:**
```
🔧 Auto-Healing Action

Component: docker_container_nginx-proxy
Issue: Docker container 'nginx-proxy' exited: Exited (1) 3 minutes ago
Action: Restart container 'nginx-proxy'
Result: ✅ Successfully restarted container 'nginx-proxy'
```

### Example 2: High Memory on Node

**Scenario**: Proxmox node memory usage reaches 95%

**Flow:**
1. Health agent detects: Memory usage 95.2%
2. Diagnoses: Memory pressure, need to free up resources
3. Assesses risk: MEDIUM (affects running VMs)
4. Requests approval: Sends Telegram message with buttons
5. User approves: Clears caches, stops non-essential services
6. Reports: Memory reduced to 78%

**Approval Request:**
```
⚠️ Action Approval Required

Component: proxmox_node
Issue: Proxmox node memory usage is high: 95.2%
Severity: 🔴 CRITICAL
Risk Level: MEDIUM

Suggested Fix: Clear caches or stop non-essential containers

Metrics:
{
  "memory_percent": 95.2,
  "used_gb": 59.6
}

Should I proceed with this action?

[✅ Approve] [❌ Reject]
```

### Example 3: Critical Service Down

**Scenario**: LXC 104 (homelab-agents) is stopped

**Flow:**
1. Health agent detects: Critical LXC container stopped
2. Diagnoses: Service failure, needs restart
3. Assesses risk: MEDIUM (bot depends on this)
4. Requests approval: Immediate Telegram notification
5. User approves: Starts container
6. Reports: Service restored

## Conclusion

The Autonomous Self-Healing System transforms your homelab into an intelligent, self-managing infrastructure. It continuously watches for issues, fixes what it can safely, and asks for help when needed.

**Key Benefits:**
- 🚀 Reduced downtime through automatic fixes
- 🧠 Intelligent diagnosis using Claude AI
- 🛡️ Safety through risk-based decision making
- 📊 Complete visibility via Telegram
- 🔄 Continuous learning and improvement

**Get Started:**
```
/enable_autohealing
```

Your homelab is now autonomous! 🤖
