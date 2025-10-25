# Phase D Deployment Guide: Scheduled Reports

## ✅ Status: CODE COMPLETE - READY FOR DEPLOYMENT

All code for Phase D (Scheduled Reports) is **already integrated** into the telegram bot!

**What's already done:**
- ✅ Report generator system implemented (daily/weekly/monthly)
- ✅ APScheduler-based report scheduler implemented
- ✅ `/report` and `/schedule` commands added to bot
- ✅ Commands registered in application
- ✅ Report scheduler initializes automatically with bot
- ✅ Integration with infrastructure, network, and alert agents

---

## 🎯 What Phase D Does

Phase D adds automated report generation and delivery capabilities:

### Report Types
1. **Daily Summary** - System health snapshot
   - Infrastructure status (VMs, containers, resources)
   - Network status (devices, bandwidth, uptime)
   - Alert summary (active, acknowledged, silenced)
   - Runs at 08:00 UTC daily

2. **Weekly Trends** - Performance analysis
   - Resource usage trends over 7 days
   - Network activity patterns
   - Alert statistics and patterns
   - Runs at 08:00 UTC on Mondays

3. **Monthly Summary** - Long-term overview
   - Monthly system performance
   - Resource utilization summary
   - Incident summary
   - Disabled by default (can be enabled)

---

## 🚀 Quick Deployment Steps

### Step 1: Restart Telegram Bot (5 min)

The bot will automatically start the report scheduler.

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
# Check logs for scheduler startup
journalctl -u homelab-bot -f | grep -i "report scheduler"
# Should see: "Report scheduler started with automated daily and weekly reports"
```

---

### Step 2: Test Report Commands (10 min)

**Test 1: Generate a daily report manually**
```
You: /report daily
Bot: 📊 Generating daily report...
Bot: [Shows daily system summary report]
```

**Test 2: Generate a weekly report**
```
You: /report weekly
Bot: 📊 Generating weekly report...
Bot: [Shows weekly trends report]
```

**Test 3: View schedule configuration**
```
You: /schedule
Bot: [Shows current report schedules and next run times]
```

**Test 4: Try monthly report (disabled by default)**
```
You: /report monthly
Bot: 📊 Generating monthly report...
Bot: [Shows monthly summary report]
```

---

## 🎮 Available Commands

### Phase D: Scheduled Reports

| Command | Description | Example |
|---------|-------------|---------|
| `/report daily` | Generate daily summary now | `/report daily` |
| `/report weekly` | Generate weekly trends now | `/report weekly` |
| `/report monthly` | Generate monthly summary now | `/report monthly` |
| `/schedule` | View scheduled report configuration | `/schedule` |

---

## 📊 Report Schedule Configuration

Default schedules are configured in `shared/report_scheduler.py`:

```python
ReportType.DAILY_SUMMARY:
  - enabled: True
  - hour: 8
  - minute: 0
  - (Runs at 08:00 UTC daily)

ReportType.WEEKLY_TRENDS:
  - enabled: True
  - hour: 8
  - minute: 0
  - day_of_week: 'mon'
  - (Runs at 08:00 UTC on Mondays)

ReportType.MONTHLY_SUMMARY:
  - enabled: False
  - hour: 8
  - minute: 0
  - day: 1
  - (Would run at 08:00 UTC on 1st of month if enabled)
```

To modify schedules, edit `/home/munky/homelab-agents/shared/report_scheduler.py` lines 73-94.

---

## 🔍 Troubleshooting

### Reports Not Generating

**Check bot logs:**
```bash
journalctl -u homelab-bot -f | grep -i report
```

**Verify scheduler is running:**
```bash
# Check logs for scheduler startup
journalctl -u homelab-bot -n 100 | grep "Report scheduler"
# Should see: "Report scheduler started with automated daily and weekly reports"
```

### Reports Show "Error retrieving data"

**Verify agents are initialized:**
```bash
# Check logs for agent initialization
journalctl -u homelab-bot -n 100 | grep -i agent
```

**Test infrastructure agent directly:**
```bash
cd /home/munky/homelab-agents
source venv/bin/activate
python -c "
from agents.infrastructure_agent import InfrastructureAgent
import asyncio

async def test():
    agent = InfrastructureAgent()
    result = await agent.execute('Get summary of all VMs')
    print(result)

asyncio.run(test())
"
```

### Scheduled Reports Not Arriving

**Check that APScheduler is running:**
```bash
# Look for scheduled jobs in logs
journalctl -u homelab-bot -f | grep -i "scheduled"
```

**Verify admin user ID is configured:**
```bash
# Check .env for TELEGRAM_ADMIN_IDS
grep TELEGRAM_ADMIN_IDS /home/munky/homelab-agents/.env
```

---

## 📈 Integration Points

### Report Generation Flow
```
User: /report daily
    ↓
TelegramBot.report_command()
    ↓
ReportScheduler.trigger_report_now(ReportType.DAILY_SUMMARY)
    ↓
ReportScheduler._generate_and_send_report()
    ↓
ReportGenerator.generate_daily_summary()
    ↓
  ├─ InfrastructureAgent.execute()
  ├─ NetworkAgent.get_network_status()
  └─ AlertManager.get_stats()
    ↓
Formatted markdown report
    ↓
on_scheduled_report() callback
    ↓
📱 Message sent to user
```

### Scheduled Report Flow
```
APScheduler CronTrigger fires (08:00 UTC)
    ↓
ReportScheduler._generate_and_send_report()
    ↓
ReportGenerator.generate_daily_summary()
    ↓
on_scheduled_report() callback
    ↓
📱 Report sent to all admin users
```

---

## 🎯 Success Criteria

After deployment, verify:

- [ ] Bot restarts without errors
- [ ] `/report daily` generates and displays daily report
- [ ] `/report weekly` generates and displays weekly report
- [ ] `/report monthly` generates and displays monthly report
- [ ] `/schedule` shows current schedules and next run times
- [ ] Reports include infrastructure data
- [ ] Reports include network status
- [ ] Reports include alert statistics
- [ ] Scheduler logs show it's running
- [ ] No errors in bot logs related to reports

---

## 🔧 Customization

### Changing Report Schedule Times

Edit `/home/munky/homelab-agents/shared/report_scheduler.py`:

```python
# Change daily report time to 6 AM UTC
ReportType.DAILY_SUMMARY: ReportSchedule(
    report_type=ReportType.DAILY_SUMMARY,
    enabled=True,
    hour=6,  # Changed from 8
    minute=0
),
```

Then restart the bot.

### Enabling Monthly Reports

Edit `/home/munky/homelab-agents/shared/report_scheduler.py`:

```python
ReportType.MONTHLY_SUMMARY: ReportSchedule(
    report_type=ReportType.MONTHLY_SUMMARY,
    enabled=True,  # Changed from False
    hour=8,
    minute=0,
    day=1
)
```

### Customizing Report Content

Edit `/home/munky/homelab-agents/shared/report_generator.py`:

- `generate_daily_summary()` - Lines 35-120
- `generate_weekly_trends()` - Lines 122-200
- `generate_monthly_summary()` - Lines 202-259

---

## 📂 Files Modified/Created

### New Files
- `shared/report_generator.py` - Report generation logic
- `shared/report_scheduler.py` - APScheduler integration
- `PHASE_D_DEPLOYMENT.md` - This deployment guide

### Modified Files
- `interfaces/telegram_bot.py`
  - Added `/report` and `/schedule` commands (lines 892-993)
  - Removed old duplicate commands
  - Updated command registrations (lines 1514-1515)
  - Initialized report scheduler in startup (lines 1540-1552)
  - Updated `/start` and `/help` documentation

---

## 📅 Next Steps After Deployment

Once Phase D is deployed and tested:

1. **Monitor report delivery** - Check logs for scheduled report execution
2. **Customize report content** - Adjust what data is included based on needs
3. **Adjust schedules** - Modify times to match preferences
4. **Enable monthly reports** - If long-term tracking is desired

---

## 🆘 Support

- **Bot logs:** `journalctl -u homelab-bot -f`
- **Check scheduler status:** Look for "Report scheduler started" in logs
- **Test reports manually:** `/report daily` or `/report weekly`
- **View schedules:** `/schedule`

---

## 🏗️ Architecture

### Components

1. **ReportGenerator** (`shared/report_generator.py`)
   - Generates formatted markdown reports
   - Integrates with infrastructure, network, and alert agents
   - Three report types: daily, weekly, monthly

2. **ReportScheduler** (`shared/report_scheduler.py`)
   - Uses APScheduler for cron-based scheduling
   - Manages report schedules (enable/disable, timing)
   - Triggers report generation and delivery

3. **Telegram Bot Integration** (`interfaces/telegram_bot.py`)
   - `/report <type>` - Manual report generation
   - `/schedule` - View/manage schedules
   - `on_scheduled_report()` - Callback for delivery

### Data Flow

```
┌─────────────────────┐
│  APScheduler Cron   │
│   (08:00 UTC)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ReportScheduler    │
│  trigger generation │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ReportGenerator    │
│  collect data       │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌──────────┐
│ Infra   │ │ Network  │
│ Agent   │ │ Agent    │
└─────────┘ └──────────┘
     │           │
     └─────┬─────┘
           ▼
┌─────────────────────┐
│  Format Markdown    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  on_scheduled_report│
│  callback           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  📱 Telegram        │
│  Admin Users        │
└─────────────────────┘
```

---

**Deployment Time Estimate:** 15-20 minutes total
**Difficulty:** Easy (just restart bot, no configuration changes needed)
**Status:** ✅ Ready to Deploy
