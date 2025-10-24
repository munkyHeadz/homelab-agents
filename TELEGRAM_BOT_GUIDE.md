# Telegram Bot Quick Reference

## ✅ Bot Status: DEPLOYED & RUNNING

**Service**: `homelab-telegram-bot.service`
**Status**: Active (running)
**PID**: 4035166
**Memory**: ~100MB

---

## 📱 How to Use

### 1. Find Your Bot
- Open Telegram on your phone
- Search for your bot using the bot username (check @BotFather for the username)
- Or use the token to find it: `8163435865`

### 2. Start the Bot
Send: `/start`

You should receive a welcome message with available commands.

### 3. Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and overview |
| `/status` | Complete system status (Proxmox + Docker) |
| `/vms` | List all VMs and containers |
| `/docker` | Docker system information |
| `/monitor` | Resource monitoring |
| `/help` | Show command reference |

### 4. Natural Language
You can also send plain text messages:
- "Check the status of all VMs"
- "Show me Docker containers"
- "Monitor system resources"
- "List running containers"

---

## 🔧 Bot Management

### Check Status
```bash
sudo systemctl status homelab-telegram-bot
```

### View Live Logs
```bash
sudo journalctl -u homelab-telegram-bot -f
```

### Restart Bot
```bash
sudo systemctl restart homelab-telegram-bot
```

### Stop Bot
```bash
sudo systemctl stop homelab-telegram-bot
```

### Start Bot
```bash
sudo systemctl start homelab-telegram-bot
```

### Disable Auto-Start
```bash
sudo systemctl disable homelab-telegram-bot
```

---

## 🔐 Security

**Authorized User ID**: `500505500`

Only this Telegram user ID can interact with the bot. Unauthorized users will receive an "Unauthorized" message.

To add more authorized users:
1. Edit `/home/munky/homelab-agents/.env`
2. Update `TELEGRAM_ADMIN_IDS=500505500,OTHER_USER_ID`
3. Restart the bot: `sudo systemctl restart homelab-telegram-bot`

---

## 📊 What the Bot Can Do

### Infrastructure Management
- ✅ Check Proxmox node status (CPU, memory, disk, uptime)
- ✅ List all VMs and LXC containers
- ✅ Get VM/container details
- ✅ Docker system information
- ✅ List Docker containers

### Monitoring
- ✅ Real-time resource monitoring
- ✅ System health checks
- ✅ Container status updates

### Coming Soon
- 🔄 Start/stop VMs and containers
- 🔄 Create new containers
- 🔄 Resource alerts and notifications
- 🔄 Automated responses to system events

---

## 🐛 Troubleshooting

### Bot Not Responding
1. Check if service is running:
   ```bash
   sudo systemctl status homelab-telegram-bot
   ```

2. Check logs for errors:
   ```bash
   sudo journalctl -u homelab-telegram-bot -n 100
   ```

3. Restart the bot:
   ```bash
   sudo systemctl restart homelab-telegram-bot
   ```

### "Unauthorized" Message
- Your Telegram user ID is not in the allowed list
- Check your user ID: Send a message to @userinfobot
- Add your ID to `.env` file: `TELEGRAM_ADMIN_IDS=YOUR_ID`
- Restart bot

### Bot Commands Not Working
- Make sure Infrastructure Agent is working:
  ```bash
  cd /home/munky/homelab-agents
  source venv/bin/activate
  export PYTHONPATH=/home/munky/homelab-agents
  python agents/infrastructure_agent.py
  ```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `/home/munky/homelab-agents/interfaces/telegram_bot.py` | Bot implementation |
| `/etc/systemd/system/homelab-telegram-bot.service` | Systemd service file |
| `/home/munky/homelab-agents/.env` | Configuration (bot token, user IDs) |
| `/home/munky/homelab-agents/scripts/deploy_telegram_bot.sh` | Deployment script |

---

## 🎯 Example Usage

### Check System Status
```
You: /status
Bot: 📊 System Status Report
     🕐 2025-10-23 20:34:15

     Proxmox Node:
     CPU: 0.0%
     Memory: 40.5 GB / 62.7 GB
     ...
```

### List VMs
```
You: /vms
Bot: 🔄 Fetching VM list...
     ✅ Task completed
     Found 7 containers: arr, docker, rustdeskserver, ...
```

### Natural Language
```
You: Show me all Docker containers
Bot: 🤔 Processing your request...
     ✅ Task completed successfully

     📋 Results:
     Containers: 0 (Running: 0)
     Images: 0
     Server Version: 28.5.1
```

---

## 🚀 Next Steps

Your Telegram bot is fully operational! Here's what to do next:

1. **Test the Bot**: Open Telegram and send `/start` to your bot
2. **Try Commands**: Test `/status`, `/vms`, `/docker`
3. **Natural Language**: Send "Check system status"
4. **Monitor Logs**: `sudo journalctl -u homelab-telegram-bot -f`
5. **Customize**: Add more commands in `interfaces/telegram_bot.py`

Enjoy managing your homelab from your phone! 📱🤖
