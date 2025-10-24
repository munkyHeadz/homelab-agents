# 🚀 Deployment Instructions - Homelab Agent System v2.5

## Current Situation

Your Telegram bot is running the **old version** and the `/update` command was failing due to git configuration issues.

## What's Been Done

✅ **All code completed and pushed to GitHub**
- Autonomous self-healing agent
- Enhanced Telegram bot with 15+ new commands
- Interactive button menus
- Approval workflows
- Comprehensive documentation

✅ **Git issues fixed in the code**
- Improved `/update` command to handle branch tracking automatically
- Created fix script for one-time setup
- Added detailed troubleshooting docs

## 📋 Step-by-Step Deployment

### Step 1: Run Fix Script on Proxmox Host

**SSH into your Proxmox host** and run:

```bash
# Download and run the fix script
curl -sSL https://raw.githubusercontent.com/munkyHeadz/homelab-agents/claude/clarify-next-steps-011CUSDuUKwx17RApEQCQ38j/scripts/fix_bot_git.sh | bash
```

**Or manually:**

```bash
# Fix git ownership
pct exec 104 -- git config --global --add safe.directory /root/homelab-agents

# Fetch updates
pct exec 104 -- bash -c "cd /root/homelab-agents && git fetch origin"

# Switch to main branch
pct exec 104 -- bash -c "cd /root/homelab-agents && git checkout main"

# Set up branch tracking
pct exec 104 -- bash -c "cd /root/homelab-agents && git branch --set-upstream-to=origin/main main"

# Pull latest from main
pct exec 104 -- bash -c "cd /root/homelab-agents && git pull"

# Restart bot
pct exec 104 -- systemctl restart homelab-telegram-bot
```

**Verify it worked:**
```bash
pct exec 104 -- systemctl status homelab-telegram-bot
```

Should show: `active (running)`

---

### Step 2: Merge PR on GitHub

1. Go to GitHub: https://github.com/munkyHeadz/homelab-agents/pulls
2. Find the PR: **"Add Autonomous Self-Healing System v2.5"**
3. Review the changes:
   - New autonomous health agent
   - Enhanced Telegram bot
   - Interactive features
4. Click **"Merge pull request"**
5. Confirm the merge

---

### Step 3: Update Bot via Telegram

Now the `/update` command will work because:
- Git ownership is fixed
- Branch tracking is configured
- The improved `/update` command handles edge cases

**In Telegram, send:**
```
/update
```

**You'll see:**
```
🔄 Fetching updates from GitHub...
🔄 Pulling latest changes...
✅ Update Complete

Latest commit:
64c3429 Improve /update command robustness and add git fix script

🔄 Restarting bot in 3 seconds...
```

---

### Step 4: Verify New Features

After the bot restarts, test the new commands:

```
/help
```

**You should now see:**
- All the new commands (start_vm, restart_container, etc.)
- Health monitoring commands
- Interactive menu option

```
/menu
```

**Should display interactive buttons:**
```
🤖 Homelab Control Menu

[📊 Status] [🖥️ Node]
[📦 VMs]    [🐳 Docker]
[🏥 Health] [💾 Backups]
[🔄 Refresh]
```

---

### Step 5: Enable Auto-Healing (Optional)

To activate the autonomous monitoring system:

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

---

## 🧪 Test the New Features

### Test VM Control
```
/vms                    # List all VMs
/start_vm 104           # Start a VM (change ID as needed)
```

### Test Docker Control
```
/containers             # List containers
/restart_container nginx-proxy  # Restart a container
```

### Test Health Monitoring
```
/health                 # View health report
```

### Test Interactive Menu
```
/menu                   # Open button menu
[Click any button to test]
```

### Test Backup Status
```
/backup                 # All VMs backup status
/backup 104             # Specific VM
```

---

## 📊 What Each Command Does

### System Commands
- `/status` - Complete system overview with node, Docker, and bot status
- `/uptime` - Bot and system uptime
- `/monitor` - Real-time resource monitoring
- `/menu` - Interactive button-based control panel

### VM/Container Control
- `/start_vm <id>` - Start a stopped VM or LXC container
- `/stop_vm <id>` - Stop a running VM or LXC container
- `/restart_vm <id>` - Restart a VM or LXC container

### Docker Control
- `/restart_container <name>` - Restart a Docker container
- `/stop_container <name>` - Stop a Docker container

### Health & Auto-Healing
- `/health` - System health report with active issues
- `/enable_autohealing` - Start autonomous monitoring (checks every 60s)
- `/disable_autohealing` - Stop autonomous monitoring

### Backup Management
- `/backup` - Show recent backup status for all VMs
- `/backup <vmid>` - Show backup status for specific VM

---

## 🏥 How Auto-Healing Works

When enabled, the system:

1. **Monitors** (every 60 seconds):
   - Proxmox node health (CPU, memory, disk)
   - VM/Container status
   - Docker daemon and containers
   - MCP server connectivity

2. **Detects Issues** like:
   - Crashed containers
   - High resource usage
   - Stopped critical services
   - Unhealthy containers

3. **Diagnoses** using Claude AI:
   - Analyzes root cause
   - Generates remediation plan
   - Assesses risk level

4. **Takes Action**:
   - **LOW Risk** → Auto-fix immediately
   - **MEDIUM/HIGH Risk** → Request approval via Telegram

5. **Reports** via Telegram:
   - Notification of auto-fixes
   - Approval requests with buttons
   - Results of executed actions

### Example Auto-Fix

```
🔧 Auto-Healing Action

Component: docker_container_nginx-proxy
Issue: Container exited unexpectedly
Action: Restart container 'nginx-proxy'
Result: ✅ Successfully restarted container 'nginx-proxy'
```

### Example Approval Request

```
⚠️ Action Approval Required

Component: lxc_104
Issue: Critical container stopped
Severity: 🔴 CRITICAL
Risk Level: MEDIUM

Suggested Fix: Start container 104

[✅ Approve] [❌ Reject]
```

---

## 📖 Documentation

### Full Documentation Files
- **AUTONOMOUS_FEATURES.md** - Complete guide to auto-healing system
- **FIX_GIT_OWNERSHIP.md** - Git troubleshooting
- **README.md** - Updated with all v2.5 features
- **BOT_IMPROVEMENTS.md** - Telegram bot features

### Key Sections
- Architecture diagrams
- Command reference
- Configuration options
- Security considerations
- Troubleshooting guide

---

## ⚠️ Troubleshooting

### /update Still Fails

**Run the fix script again:**
```bash
pct exec 104 -- git config --global --add safe.directory /root/homelab-agents
pct exec 104 -- bash -c "cd /root/homelab-agents && git fetch && git checkout main && git branch --set-upstream-to=origin/main main"
pct exec 104 -- systemctl restart homelab-telegram-bot
```

### Bot Not Showing New Commands

1. Make sure you merged the PR on GitHub
2. Run `/update` in Telegram
3. Check bot logs:
   ```bash
   pct exec 104 -- journalctl -u homelab-telegram-bot -n 50
   ```

### Auto-Healing Not Working

1. Enable it: `/enable_autohealing`
2. Check health: `/health`
3. Wait 60 seconds for first check
4. Watch for notifications

### Can't Control VMs/Containers

- Check MCP servers are accessible
- Verify Proxmox/Docker credentials in .env
- Test with `/vms` or `/containers` first

---

## 🎯 Success Checklist

After deployment, you should be able to:

- [ ] Run `/help` and see all new commands
- [ ] Run `/menu` and interact with button menu
- [ ] Run `/health` and see health report
- [ ] Run `/vms` and see list of VMs
- [ ] Run `/start_vm <id>` and control a VM
- [ ] Run `/containers` and see Docker containers
- [ ] Run `/restart_container <name>` and restart a container
- [ ] Run `/enable_autohealing` and activate monitoring
- [ ] Run `/backup` and see backup status
- [ ] Receive auto-healing notifications (wait 60s after enabling)

---

## 📞 Need Help?

### Check Logs
```bash
# Bot logs
pct exec 104 -- journalctl -u homelab-telegram-bot -f

# Git status
pct exec 104 -- bash -c "cd /root/homelab-agents && git status"

# Bot status
pct exec 104 -- systemctl status homelab-telegram-bot
```

### Common Issues

**Issue:** `/update` says "no tracking information"
**Fix:** Run Step 1 again (fix script)

**Issue:** Bot doesn't show new commands
**Fix:** Merge PR, then run `/update`

**Issue:** Auto-healing not running
**Fix:** Run `/enable_autohealing`

**Issue:** Commands return errors
**Fix:** Check .env file has correct credentials

---

## 🎉 You're All Set!

Once all steps are complete, your homelab will have:

✅ Autonomous self-healing capabilities
✅ Complete VM/Container control via Telegram
✅ Interactive button menus
✅ Smart approval workflows
✅ Health monitoring and reporting
✅ Backup status checking
✅ Improved reliability with robust /update command

**Your homelab is now truly autonomous!** 🤖

---

**Questions or issues?** Check the documentation or logs above.
