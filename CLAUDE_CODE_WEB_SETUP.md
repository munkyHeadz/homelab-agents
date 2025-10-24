# Claude Code on the Web - Setup Guide

## Overview

Claude Code on the web allows you to code collaboratively with Claude through your browser at **claude.ai/code**. The repository has been prepared and is ready to be pushed to GitHub.

## Step-by-Step Setup

### 1. Create GitHub Repository

1. Go to [github.com](https://github.com) and log in
2. Click the **"+"** icon → **"New repository"**
3. Repository settings:
   - **Name**: `homelab-agents`
   - **Description**: "Autonomous agent system for homelab management"
   - **Visibility**: Choose **Private** (recommended for homelab configs)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
4. Click **"Create repository"**

### 2. Push Code to GitHub

GitHub will show you setup commands. Use these:

```bash
cd /home/munky/homelab-agents

# Add GitHub remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/homelab-agents.git

# Push code to GitHub
git push -u origin main
```

**Example:**
```bash
git remote add origin https://github.com/munky/homelab-agents.git
git push -u origin main
```

You may be prompted for credentials:
- **Username**: Your GitHub username
- **Password**: Use a Personal Access Token (not your password)
  - Create token at: https://github.com/settings/tokens
  - Select scopes: `repo` (full control of private repositories)

### 3. Install Claude GitHub App

1. Go to **claude.ai/code**
2. Click **"Connect GitHub"** or **"Settings"**
3. Click **"Install Claude GitHub App"**
4. You'll be redirected to GitHub
5. Choose where to install:
   - **"Only select repositories"** → Select `homelab-agents`
   - Or **"All repositories"** (if you want Claude access to all)
6. Click **"Install & Authorize"**

### 4. Configure Environment in Claude Code Web

When you start a session at claude.ai/code:

1. **Select Repository**: Choose `homelab-agents`
2. **Configure Environment Variables**:
   Click "Environment Settings" and add:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
PROXMOX_HOST=192.168.1.99
PROXMOX_TOKEN_ID=root@pam!homelab
PROXMOX_TOKEN_SECRET=your-secret-here
DOCKER_HOST=tcp://192.168.1.101:2375
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ADMIN_IDS=500505500
POSTGRES_HOST=192.168.1.200
POSTGRES_USER=homelab
POSTGRES_PASSWORD=your-db-password
POSTGRES_DB=homelab_agents
```

**Note:** These environment variables are only stored in your Claude Code session, not in the repository.

3. **Select Network Access**: Choose appropriate level
   - **Full Network Access** - Recommended for this project (needs to access Proxmox, Docker, etc.)
   - **Limited Network Access** - Restricts outbound connections
   - **No Network Access** - Blocks all network

4. **Automatic Setup**: The `.claude/settings.json` will automatically:
   - Create Python virtual environment
   - Install dependencies from `requirements.txt`
   - Set up the environment

### 5. Start Coding with Claude

1. Click **"Start Session"**
2. Give Claude a task, for example:
   - "Add a new command to the Telegram bot to restart containers"
   - "Improve the VM status parsing in infrastructure_agent.py"
   - "Add tests for the monitoring agent"
3. Claude will:
   - Read relevant files
   - Make changes
   - Test the code
   - Create a pull request when done

### 6. Review and Merge Changes

1. Claude creates a **Pull Request** on GitHub
2. Review the changes in the PR
3. Test locally if needed:
   ```bash
   # Fetch PR branch
   gh pr checkout <PR_NUMBER>
   
   # Or manually
   git fetch origin pull/<PR_NUMBER>/head:pr-<PR_NUMBER>
   git checkout pr-<PR_NUMBER>
   ```
4. Merge the PR when ready
5. Pull changes to your homelab:
   ```bash
   cd /home/munky/homelab-agents
   git pull
   ```

## Repository Structure

The repository is now set up with:

### Configuration Files
- **`.gitignore`** - Excludes sensitive files (.env, venv/, logs/, etc.)
- **`.claude/settings.json`** - Claude Code web configuration
  - Auto-setup Python venv on session start
  - Environment variable templates
  - Default shell settings

### Documentation
- **`README.md`** - Complete project documentation
- **`BOT_IMPROVEMENTS.md`** - Telegram bot features
- **`TELEGRAM_BOT_TESTING.md`** - Testing guide
- **`TEST_REPORT.md`** - Integration test results

### Code
- **`agents/`** - Autonomous agents
- **`interfaces/`** - User interfaces (Telegram bot)
- **`mcp_servers/`** - MCP server implementations
- **`shared/`** - Shared utilities
- **`scripts/`** - Deployment scripts
- **`tests/`** - Test suite

## Using Claude Code Web Features

### Session Start Hooks

The `.claude/settings.json` includes a SessionStart hook that automatically:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

This ensures every session has a fresh Python environment ready.

### Environment Variables

Environment variables are configured with templates:
```json
"environmentVariables": {
  "ANTHROPIC_API_KEY": "{{ env.ANTHROPIC_API_KEY }}"
}
```

When you start a session, provide actual values in the Claude Code web UI.

### Default Shell

Set to `bash` for consistency with deployment scripts.

## Security Best Practices

### What's Excluded from Git
The `.gitignore` excludes:
- ✅ `.env` files (all environment files)
- ✅ `secrets/` and `credentials/` directories
- ✅ Python virtual environments
- ✅ Log files
- ✅ Database files
- ✅ Monitoring data (Prometheus/Grafana data)

### What to Keep Private
**Never commit:**
- API keys (Anthropic, Proxmox, etc.)
- Bot tokens
- Database passwords
- Private IP addresses (if you want to keep network layout private)

**Safe to commit:**
- Code files (agents, MCP servers, bot)
- Configuration templates
- Documentation
- Deployment scripts
- Test files

## Syncing Between Local and Cloud

### Local → GitHub → Claude Code Web
```bash
# On homelab
cd /home/munky/homelab-agents
git add .
git commit -m "Add new feature"
git push

# Then in Claude Code web, the changes are available
```

### Claude Code Web → GitHub → Local
```bash
# Claude creates PR on GitHub
# You merge the PR
# Then on homelab:
git pull
```

### Using the Bot's /update Command

The Telegram bot's `/update` command automatically:
1. Runs `git pull` from within LXC 104
2. Restarts the bot service
3. New code is live immediately

## Workflow Example

### Adding a New Feature

**Option 1: Using Claude Code Web**
1. Go to claude.ai/code
2. Open homelab-agents repository
3. Ask: "Add a /backup command to show backup status"
4. Claude implements the feature
5. Review PR on GitHub
6. Merge PR
7. In Telegram, send `/update` to pull changes

**Option 2: Local Development**
1. Work locally on homelab
2. Test changes
3. Push to GitHub
4. In Telegram, send `/update` to deploy

## Troubleshooting

### "Repository not found" in Claude Code Web
- Ensure Claude GitHub App is installed on the repository
- Check repository permissions in GitHub settings

### "Environment variables not set"
- Configure them in the session settings before starting
- They're session-specific, not stored in the repo

### SessionStart hook failing
- Check `requirements.txt` is valid
- Ensure Python 3.10+ is available
- Review session logs in Claude Code web

### Can't push to GitHub
- Check you're using a Personal Access Token, not password
- Ensure token has `repo` scope
- Verify remote URL is correct: `git remote -v`

## Next Steps

1. ✅ Repository initialized with git
2. ✅ `.gitignore` created (excludes sensitive files)
3. ✅ `.claude/settings.json` configured
4. ✅ README.md created with full documentation
5. ✅ Initial commit made (51 files, 14,773 lines)
6. ⏳ **Create GitHub repository**
7. ⏳ **Push code to GitHub**
8. ⏳ **Install Claude GitHub App**
9. ⏳ **Start coding at claude.ai/code**

## Quick Reference

### Git Commands
```bash
# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Description"

# Push to GitHub
git push

# Pull from GitHub
git pull

# Check remotes
git remote -v
```

### Claude Code Web
- **URL**: https://claude.ai/code
- **Docs**: https://docs.claude.com/en/docs/claude-code/claude-code-on-the-web

### Telegram Bot Update
```
/update  # In Telegram - pulls latest code and restarts
```

---

**Ready to go!** Follow steps 1-4 above to complete the setup.
