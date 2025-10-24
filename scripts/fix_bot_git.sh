#!/bin/bash
#
# Fix Git Configuration in LXC 104 for /update Command
#
# This script resolves common git issues that prevent the /update command from working
#

set -e

echo "=== Fixing Git Configuration in LXC 104 ==="
echo ""

# 1. Fix git ownership issue
echo "1. Adding safe directory exception..."
pct exec 104 -- git config --global --add safe.directory /root/homelab-agents

# 2. Check current branch and set up tracking
echo "2. Setting up branch tracking..."
pct exec 104 -- bash -c "cd /root/homelab-agents && git fetch origin"

# Get current branch
CURRENT_BRANCH=$(pct exec 104 -- bash -c "cd /root/homelab-agents && git branch --show-current")
echo "   Current branch: $CURRENT_BRANCH"

# Set up tracking for main branch
if [ "$CURRENT_BRANCH" = "main" ]; then
    echo "   Setting up tracking for main branch..."
    pct exec 104 -- bash -c "cd /root/homelab-agents && git branch --set-upstream-to=origin/main main"
else
    echo "   Warning: Not on main branch, switching to main..."
    pct exec 104 -- bash -c "cd /root/homelab-agents && git checkout main && git branch --set-upstream-to=origin/main main"
fi

# 3. Pull latest changes
echo "3. Pulling latest changes..."
pct exec 104 -- bash -c "cd /root/homelab-agents && git pull"

# 4. Show current status
echo "4. Current git status:"
pct exec 104 -- bash -c "cd /root/homelab-agents && git log -1 --oneline"
echo ""

# 5. Restart bot
echo "5. Restarting Telegram bot..."
pct exec 104 -- systemctl restart homelab-telegram-bot

# 6. Wait and check status
echo "6. Waiting for bot to start..."
sleep 3

echo "7. Bot status:"
pct exec 104 -- systemctl status homelab-telegram-bot --no-pager -l

echo ""
echo "=== Fix Complete! ==="
echo ""
echo "Test in Telegram:"
echo "  /update  - Should now work"
echo "  /help    - Should show all new commands"
echo "  /menu    - Try the interactive menu"
echo "  /health  - View system health"
echo ""
