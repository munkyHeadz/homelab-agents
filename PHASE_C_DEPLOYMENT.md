# Phase C Deployment Guide: Backup Management

## ✅ Status: CODE COMPLETE - READY FOR DEPLOYMENT

All code for Phase C (Backup Management) is **already integrated** into the telegram bot!

**What's already done:**
- ✅ PBS (Proxmox Backup Server) client implemented
- ✅ Backup manager with health monitoring implemented
- ✅ `/backups` and `/backup_list` commands added to bot
- ✅ Commands registered in application
- ✅ Backup manager initializes automatically with bot
- ✅ Integration with PBS via proxmoxer library

---

## 🎯 What Phase C Does

Phase C adds comprehensive backup monitoring and management capabilities:

### Features
1. **Backup Status Monitoring**
   - Datastore usage and capacity tracking
   - Total backups and size calculation
   - Protected backup count
   - Latest backup age tracking
   - Backup health analysis

2. **Backup Health Checks**
   - Detects missing or old backups
   - Warns when datastore fills up (>85%)
   - Identifies unprotected backups
   - Provides health status: healthy/warning/critical

3. **Backup Listing**
   - Recent backups with timestamps
   - Verification status tracking
   - Protected backup indicators
   - Backup size information
   - Grouped by VM/container type

---

## 🚀 Quick Deployment Steps

### Step 1: Configure PBS Connection (10 min)

**Update `.env` file with PBS credentials:**

```bash
cd /home/munky/homelab-agents

# Edit .env
nano .env
```

**Add/update these PBS variables:**
```bash
# Proxmox Backup Server (PBS)
PBS_ENABLED=true
PBS_HOST=192.168.1.103
PBS_PORT=8007
PBS_USER=root@pam
PBS_PASSWORD=your-pbs-password
PBS_DATASTORE=backups

# OR use API token (recommended):
PBS_TOKEN_ID=root@pam!backup-token
PBS_TOKEN_SECRET=your-token-secret
```

**Note:** If PBS is not available or you don't use it, the commands will gracefully show "PBS not configured" messages.

---

### Step 2: Create PBS API Token (Recommended) (5 min)

**On PBS server (192.168.1.103):**

Via PBS Web UI (https://192.168.1.103:8007):
1. Navigate to **Configuration** → **Access Control** → **API Tokens**
2. Click **Add**
3. Fill in:
   - User: `root@pam`
   - Token ID: `backup-token`
   - Privilege Separation: Unchecked
4. Copy the token secret

**Update .env:**
```bash
PBS_TOKEN_ID=root@pam!backup-token
PBS_TOKEN_SECRET=<paste-token-secret-here>
```

---

### Step 3: Restart Telegram Bot (5 min)

The bot will automatically initialize the PBS client and backup manager.

**Option A: If bot is running via systemd:**
```bash
sudo systemctl restart homelab-bot
sudo systemctl status homelab-bot
```

**Option B: If running manually:**
```bash
cd /home/munky/homelab-agents
source venv/bin/activate
pkill -f telegram_bot.py  # Stop old instance
python interfaces/telegram_bot.py  # Start new instance
```

**Verify bot started successfully:**
```bash
# Check logs for backup manager initialization
journalctl -u homelab-bot -f | grep -i "backup"
# Should see: "Backup manager initialized" and "PBS client initialized successfully"
```

---

### Step 4: Test Backup Commands (10 min)

**Test 1: Check backup status**
```
You: /backups
Bot: 📦 **Backup Status**
     [Shows datastore usage, backup summary, health status, recent backups]
```

**Test 2: List recent backups**
```
You: /backup_list
Bot: 📋 **Recent Backups** (15 shown)
     [Shows list of recent backups with verification status]
```

**Test 3: Verify graceful handling when PBS not configured**
```
# If PBS_HOST is not set:
You: /backups
Bot: ⚠️ PBS (Proxmox Backup Server) integration not configured.
```

---

## 🎮 Available Commands

### Phase C: Backup Management

| Command | Description | Example |
|---------|-------------|---------|
| `/backups` | Show comprehensive backup status | `/backups` |
| `/backup_list` | List recent backups (up to 15) | `/backup_list` |

---

## 📊 Backup Status Information

The `/backups` command provides:

### Datastore Status
- Storage usage percentage
- Used and total capacity in GB
- Visual indicator (🟢 <80%, 🟡 80-90%, 🔴 >90%)

### Backup Summary
- Total number of snapshots
- Total backup size in GB
- Number of protected backups
- Latest backup age (hours/days ago)
- Breakdown by backup type (vm, ct, host)

### Health Status
- ✅ **Healthy** - All systems normal
- ⚠️ **Warning** - Minor issues detected
- 🔴 **Critical** - Immediate attention needed

### Health Issues Detected
- No backups found
- Latest backup over 1-2 days old
- No protected backups
- Datastore filling up

### Recent Backups
- Up to 3 most recent backups shown
- Includes:
  - Backup type and VM/container ID
  - Time since backup (e.g., "2h ago", "1d ago")
  - Backup size in GB
  - ✅ Verified or ⭕ Not verified
  - 🔒 Protected indicator

---

## 🔍 Troubleshooting

### PBS Connection Fails

**Check PBS is running:**
```bash
# On Proxmox host
pct status 103
# or
ssh root@192.168.1.103
systemctl status proxmox-backup-proxy
```

**Verify network connectivity:**
```bash
# From bot container
curl -k https://192.168.1.103:8007
# Should return HTML or API response
```

**Check credentials:**
```bash
# Test with API token
curl -k -H "Authorization: PBSAPIToken=root@pam!backup-token:<your-secret>" \
  https://192.168.1.103:8007/api2/json/version
```

### Commands Show "PBS not configured"

**Verify .env has PBS_HOST set:**
```bash
grep PBS_HOST /home/munky/homelab-agents/.env
# Should show: PBS_HOST=192.168.1.103
```

**Check bot logs for PBS client initialization:**
```bash
journalctl -u homelab-bot -n 100 | grep -i pbs
# Should see: "PBS client initialized successfully"
# or: "PBS integration disabled (PBS_HOST not configured)"
```

### Backups Command Shows Errors

**Check proxmoxer is installed:**
```bash
source /home/munky/homelab-agents/venv/bin/activate
python -c "from proxmoxer import ProxmoxAPI; print('OK')"
```

**Test PBS client directly:**
```bash
cd /home/munky/homelab-agents
source venv/bin/activate
python -c "
from integrations.pbs_client import get_pbs_client
import asyncio

async def test():
    client = get_pbs_client()
    if client:
        status = await client.get_datastore_status()
        print(status)
    else:
        print('PBS client not available')

asyncio.run(test())
"
```

---

## 📈 Integration Points

### Backup Monitoring Flow
```
User: /backups
    ↓
TelegramBot.backups_command()
    ↓
BackupManager.get_backup_report()
    ↓
  ├─ PBSClient.get_datastore_status()
  ├─ PBSClient.get_backup_summary()
  ├─ PBSClient.get_recent_backups()
  └─ BackupManager._check_backup_health()
    ↓
Formatted markdown report
    ↓
📱 Message sent to user
```

### PBS Client Architecture
```
BackupManager
    ↓
PBSClient (uses proxmoxer)
    ↓
ProxmoxAPI(service="PBS")
    ↓
PBS REST API (https://192.168.1.103:8007)
    ↓
  ├─ /admin/datastore/{name}/status
  ├─ /admin/datastore/{name}/groups
  └─ /admin/datastore/{name}/snapshots
```

---

## 🎯 Success Criteria

After deployment, verify:

- [ ] Bot restarts without errors
- [ ] Bot logs show "PBS client initialized successfully"
- [ ] Bot logs show "Backup manager initialized"
- [ ] `/backups` command displays backup status
- [ ] `/backup_list` command shows recent backups
- [ ] Datastore usage percentage displayed
- [ ] Health status calculated correctly
- [ ] Recent backups list formatted properly
- [ ] Verification status (✅/⭕) shown for backups
- [ ] Protected backups indicated with 🔒
- [ ] No errors in bot logs related to backups

---

## 🔧 Customization

### Changing Backup List Limit

Edit `/home/munky/homelab-agents/interfaces/telegram_bot.py` line 1061:

```python
# Change from 15 to desired number
result = await self.backup_manager.get_backup_list(limit=20)
```

### Adjusting Health Check Thresholds

Edit `/home/munky/homelab-agents/shared/backup_manager.py` lines 84-97:

```python
# Change backup age warning threshold
if age > timedelta(days=3):  # Changed from 2
    issues.append(f"Latest backup is {age.days} days old")
    status = "warning"
```

### Modifying Datastore Alert Levels

Edit `/home/munky/homelab-agents/shared/backup_manager.py` lines 331-342:

```python
# Change datastore capacity thresholds
if usage >= 90:  # Changed from 95
    alerts.append({
        "severity": "critical",
        "message": "Datastore nearly full",
        "details": f"Usage at {usage}%"
    })
elif usage >= 80:  # Changed from 85
    alerts.append({
        "severity": "warning",
        "message": "Datastore filling up",
        "details": f"Usage at {usage}%"
    })
```

---

## 📂 Files Modified/Created

### New Files
- `integrations/pbs_client.py` - PBS API client using proxmoxer
- `shared/backup_manager.py` - High-level backup monitoring
- `PHASE_C_DEPLOYMENT.md` - This deployment guide

### Modified Files
- `interfaces/telegram_bot.py`
  - Added `/backups` and `/backup_list` commands (lines 1020-1097)
  - Registered backup commands (lines 1604-1605)
  - Updated `/start` and `/help` documentation
  - Added backup_manager initialization (line 85)

---

## 📅 Next Steps After Deployment

Once Phase C is deployed and tested:

1. **Monitor backup health** - Check `/backups` daily for issues
2. **Set up alerts** - Configure Prometheus/Alertmanager for backup failures
3. **Document backup schedule** - Add backup schedule to documentation
4. **Test restore procedures** - Verify backups can be restored

**Future enhancements (not in Phase C):**
- Trigger backups from Telegram
- Restore backups via bot commands
- Automated backup verification
- Backup prune/cleanup commands

---

## 🆘 Support

- **Bot logs:** `journalctl -u homelab-bot -f`
- **Check backup manager:** Look for "Backup manager initialized" in logs
- **Test commands:** `/backups` or `/backup_list`
- **PBS Web UI:** `https://192.168.1.103:8007`
- **PBS docs:** https://pbs.proxmox.com/docs/

---

## 🏗️ Architecture

### Components

1. **PBSClient** (`integrations/pbs_client.py`)
   - Connects to PBS via proxmoxer
   - Retrieves datastore status
   - Lists backup snapshots
   - Gets backup groups and verification status
   - Supports both password and token auth

2. **BackupManager** (`shared/backup_manager.py`)
   - High-level backup monitoring
   - Health check analysis
   - Formatted report generation
   - Alert detection for critical issues

3. **Telegram Bot Integration** (`interfaces/telegram_bot.py`)
   - `/backups` - Comprehensive status report
   - `/backup_list` - Recent backups listing
   - Graceful handling when PBS not configured

### Data Flow

```
┌─────────────────────┐
│  Telegram User      │
│  /backups command   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  BackupManager      │
│  get_backup_report()│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PBSClient          │
│  (proxmoxer)        │
└──────────┬──────────┘
           │
     ┌─────┴─────────────┐
     ▼                   ▼
┌──────────┐      ┌──────────┐
│Datastore │      │ Snapshots│
│ Status   │      │   List   │
└──────────┘      └──────────┘
     │                   │
     └─────┬─────────────┘
           ▼
┌─────────────────────┐
│  Health Analysis    │
│  + Formatting       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  📱 Telegram        │
│  Markdown Report    │
└─────────────────────┘
```

### PBS API Endpoints Used

- `GET /admin/datastore/{name}/status` - Datastore capacity and usage
- `GET /admin/datastore/{name}/groups` - Backup groups (VMs/containers)
- `GET /admin/datastore/{name}/snapshots` - Backup snapshots for a group

---

**Deployment Time Estimate:** 20-30 minutes total
**Difficulty:** Easy (mostly configuration, no code changes needed)
**Status:** ✅ Ready to Deploy
**Requirements:** PBS server running and accessible at 192.168.1.103:8007

---

## 💡 Tips

1. **Use API tokens** instead of passwords for better security
2. **Monitor datastore usage** regularly to avoid filling up
3. **Protect important backups** to prevent automatic pruning
4. **Verify backups** periodically to ensure they're restorable
5. **Document your backup strategy** - retention policy, schedules, etc.

---

## ⚠️ Limitations

Current Phase C implementation provides **monitoring only**:
- ✅ View backup status
- ✅ List backups
- ✅ Health checks
- ❌ Trigger new backups (not implemented)
- ❌ Restore backups (not implemented)
- ❌ Delete/prune backups (not implemented)
- ❌ Modify backup protection (not implemented)

These features could be added in future phases if needed.
