# Multi-Phase Implementation Status

## Overview

Implementing 5 major enhancement phases for the homelab agent system:
- **Phase A**: Alert Integration with Prometheus/Alertmanager
- **Phase B**: VM/Container Control Commands  
- **Phase C**: Backup Management
- **Phase D**: Scheduled Reports
- **Phase E**: Advanced Network Monitoring

## Current Status: Phase A & B Foundation Complete

### ✅ Phase A: Alert Integration (70% Complete)

**Completed:**
1. ✅ **Alert Management System** (`shared/alert_manager.py`)
   - Alert data model with status tracking
   - AlertManager webhook processing
   - Alert acknowledgment and silencing
   - Alert statistics and cleanup
   - Telegram formatting

2. ✅ **Webhook Server** (`interfaces/webhook_server.py`)
   - aiohttp-based HTTP server (port 8001)
   - `/webhook/alerts` endpoint for Alertmanager
   - `/health` endpoint with alert stats
   - Async alert callback system

3. ✅ **Bot Integration Started** (`interfaces/telegram_bot.py`)
   - Imports added
   - Alert manager initialized
   - Webhook server initialized
   - Pending confirmations dict added

4. ✅ **New Command Handlers Written**
   - `/alerts` - Show active alerts
   - `/ack <fingerprint>` - Acknowledge alerts
   - `/silence <fingerprint> [duration]` - Silence alerts
   - `on_alert_received()` - Push notifications

**Remaining Work:**
- ⏳ Integrate command handlers into bot class
- ⏳ Register commands in application
- ⏳ Update run() method to start webhook server
- ⏳ Configure Alertmanager webhook in LXC 107
- ⏳ Test end-to-end alert flow

**Files Created:**
- `/home/munky/homelab-agents/shared/alert_manager.py` (428 lines)
- `/home/munky/homelab-agents/interfaces/webhook_server.py` (95 lines)
- `/tmp/new_bot_commands.py` (command handlers ready to integrate)

### ✅ Phase B: VM/Container Control (60% Complete)

**Completed:**
1. ✅ **Command Handlers Written**
   - `/start_vm <vmid>` - Start VM/container
   - `/stop_vm <vmid>` - Stop with confirmation
   - `/restart_vm <vmid>` - Restart VM/container
   - `/confirm <id>` - Confirm destructive actions

2. ✅ **Confirmation System**
   - Pending confirmations tracking
   - 5-minute expiration
   - User-specific confirmations

**Remaining Work:**
- ⏳ Integrate command handlers into bot
- ⏳ Register commands
- ⏳ Test VM control operations
- ⏳ Add Docker container control commands

### ⏸️ Phase C: Backup Management (Not Started)

**Planned Features:**
- PBS (Proxmox Backup Server) MCP server
- `/backups` - List recent backups
- `/backup <vmid>` - Trigger backup
- `/restore` - Restore from backup
- Automated backup verification

**Estimated Time:** 3-4 hours

### ⏸️ Phase D: Scheduled Reports (Not Started)

**Planned Features:**
- Daily system summary (8am)
- Weekly resource trends (Monday)
- Monthly cost reports
- `/schedule` - Configure reports
- Report templates

**Estimated Time:** 2-3 hours

### ⏸️ Phase E: Advanced Network Monitoring (Not Started)

**Planned Features:**
- Enhanced Unifi integration
- Tailscale device management
- Cloudflare analytics
- Pi-hole query analysis
- Network anomaly detection

**Estimated Time:** 4-5 hours

## Architecture

### Alert Flow (Phase A)
```
Prometheus Alert Rule Fires
    ↓
Alertmanager processes alert
    ↓
Webhook sent to http://192.168.1.104:8001/webhook/alerts
    ↓
WebhookServer.handle_alert_webhook()
    ↓
AlertManager.process_webhook()
    ↓
Alert stored in memory
    ↓
Callback: TelegramBot.on_alert_received()
    ↓
📱 Notification sent to admin users
    ↓
User can: /ack, /silence, or /alerts
```

### VM Control Flow (Phase B)
```
User: /start_vm 101
    ↓
TelegramBot.start_vm_command()
    ↓
InfrastructureAgent.execute("Start VM 101")
    ↓
Proxmox MCP: start_vm tool
    ↓
✅ VM started, status sent to user

User: /stop_vm 101
    ↓
TelegramBot.stop_vm_command()
    ↓
⚠️ Confirmation requested
    ↓
User: /confirm abc123
    ↓
TelegramBot.confirm_command()
    ↓
InfrastructureAgent.execute("Stop VM 101")
    ↓
✅ VM stopped, status sent to user
```

## Integration Steps

### Step 1: Complete Phase A Integration

**Add command methods to bot class** (insert before `error_handler`):
```python
# Copy methods from /tmp/new_bot_commands.py:
# - on_alert_received()
# - alerts_command()
# - ack_command()
# - silence_command()
```

**Register commands** (in `run()` method):
```python
application.add_handler(CommandHandler("alerts", self.alerts_command))
application.add_handler(CommandHandler("ack", self.ack_command))
application.add_handler(CommandHandler("silence", self.silence_command))
```

**Start webhook server** (modify `run()` method):
```python
async def run_async(self):
    """Async run method"""
    # Start webhook server
    await self.webhook_server.start()
    
    # Run bot (this blocks)
    application = Application.builder().token(self.token).build()
    # ... register handlers ...
    self.application = application  # Store reference
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
def run(self):
    """Start bot and webhook server"""
    asyncio.run(self.run_async())
```

### Step 2: Configure Alertmanager

**Edit `/etc/prometheus/alertmanager.yml` in LXC 107:**
```yaml
route:
  receiver: 'telegram-webhook'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'telegram-webhook'
    webhook_configs:
      - url: 'http://192.168.1.104:8001/webhook/alerts'
        send_resolved: true
```

**Restart Alertmanager:**
```bash
sudo pct exec 107 -- systemctl restart alertmanager
```

### Step 3: Test Alert Flow

**Trigger test alert:**
```bash
# In Prometheus (LXC 107)
curl -X POST http://localhost:9090/api/v1/admin/tsdb/delete_series \
  -d 'match[]=up{job="node"}'

# This will trigger InstanceDown alert
```

**Expected behavior:**
1. Alert fires in Prometheus
2. Alertmanager sends webhook
3. Bot receives alert
4. 📱 Notification sent to Telegram
5. User can `/alerts` to see it
6. User can `/ack <fingerprint>` to acknowledge

### Step 4: Complete Phase B Integration

**Add VM control methods to bot class:**
```python
# Copy from /tmp/new_bot_commands.py:
# - start_vm_command()
# - stop_vm_command()
# - restart_vm_command()
# - confirm_command()
```

**Register commands:**
```python
application.add_handler(CommandHandler("start_vm", self.start_vm_command))
application.add_handler(CommandHandler("stop_vm", self.stop_vm_command))
application.add_handler(CommandHandler("restart_vm", self.restart_vm_command))
application.add_handler(CommandHandler("confirm", self.confirm_command))
```

### Step 5: Test VM Control

```
You: /start_vm 101
Bot: ✅ VM/Container Started...

You: /stop_vm 101
Bot: ⚠️ Confirm VM Stop... Send /confirm abc123

You: /confirm abc123
Bot: ✅ VM/Container Stopped...
```

## Dependencies

**New Python packages needed:**
```bash
pip install aiohttp
```

Already added to requirements.txt.

## Files Modified

1. `/home/munky/homelab-agents/interfaces/telegram_bot.py`
   - Added imports (alert_manager, webhook_server)
   - Added init attributes
   - **Needs**: Command method integration + run() update

2. `/home/munky/homelab-agents/shared/alert_manager.py` ✅ Created
3. `/home/munky/homelab-agents/interfaces/webhook_server.py` ✅ Created

## Testing Checklist

### Phase A - Alert Integration
- [ ] Webhook server starts on port 8001
- [ ] `/health` endpoint responds
- [ ] Alertmanager can send webhooks
- [ ] Alerts appear in bot memory
- [ ] `/alerts` command shows active alerts
- [ ] `/ack` acknowledges alerts
- [ ] `/silence` silences alerts
- [ ] Push notifications work
- [ ] Alert formatting looks good

### Phase B - VM Control
- [ ] `/start_vm` starts VMs/containers
- [ ] `/stop_vm` requests confirmation
- [ ] `/confirm` executes stop
- [ ] `/restart_vm` restarts VMs
- [ ] Confirmation expiration works
- [ ] Error handling works
- [ ] Status updates are accurate

## Next Steps

1. **Complete Bot Integration** (30 min)
   - Add command methods
   - Register handlers
   - Update run() method

2. **Deploy to LXC 104** (10 min)
   - Push to GitHub
   - `/update` in Telegram
   - Or manual deployment

3. **Configure Alertmanager** (15 min)
   - Edit alertmanager.yml
   - Restart service
   - Verify webhook URL

4. **Test End-to-End** (30 min)
   - Trigger test alert
   - Test all commands
   - Verify notifications

5. **Continue with Phases C, D, E** (8-12 hours)
   - Backup management
   - Scheduled reports
   - Network monitoring enhancements

## Summary

**Foundation built:**
- Alert system architecture complete
- Webhook server ready
- Command handlers written
- VM control logic implemented

**Remaining work:**
- Integrate handlers into bot (30 min)
- Configure Alertmanager (15 min)
- Test and debug (1-2 hours)

**Total progress: ~65% of Phases A & B complete**

The hard architectural work is done. Final integration is straightforward method additions and configuration.
