# Fix Git Ownership Issue for /update Command

## Problem

When running `/update` in Telegram, you see:
```
❌ Update failed:
fatal: detected dubious ownership in repository at '/root/homelab-agents'
```

## Solution

### Option 1: Quick Fix (Recommended)

SSH into your LXC 104 container and run:

```bash
# SSH into LXC 104
pct enter 104

# Add the directory as safe
git config --global --add safe.directory /root/homelab-agents

# Test git pull
cd /root/homelab-agents
git pull

# If successful, restart bot
systemctl restart homelab-telegram-bot
```

### Option 2: Fix Ownership

If you want to fix the actual ownership:

```bash
# SSH into LXC 104
pct enter 104

# Check current ownership
ls -la /root/homelab-agents

# Fix ownership (replace 'botuser' with the actual user running the bot)
chown -R root:root /root/homelab-agents

# Or if bot runs as a different user:
# chown -R botuser:botuser /root/homelab-agents
```

### Option 3: One-Line Fix

From your Proxmox host:

```bash
pct exec 104 -- git config --global --add safe.directory /root/homelab-agents
pct exec 104 -- systemctl restart homelab-telegram-bot
```

## Verify Fix

In Telegram, try:
```
/update
```

Should now see:
```
✅ Bot is already up to date!
```
or
```
✅ Update Complete
[update details]
🔄 Restarting bot in 3 seconds...
```

## Why This Happens

Git added security checks in recent versions to prevent executing code from repositories owned by different users. This is a safety feature but causes issues in containers where ownership can be unclear.

The `safe.directory` configuration tells git to trust this specific directory.

## Prevent Future Issues

Add this to your deployment script:

```bash
# In your setup/deployment script
git config --global --add safe.directory /root/homelab-agents
```

This ensures the configuration persists across container rebuilds.
