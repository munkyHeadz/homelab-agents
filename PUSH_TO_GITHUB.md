# Push to GitHub - Authentication Setup

Your repository is ready! The remote is already configured:
- **Repository**: https://github.com/munkyHeadz/homelab-agents
- **Remote**: origin (verified ✓)

## Choose Your Authentication Method

### Option 1: Personal Access Token (Recommended)

**Step 1: Create Personal Access Token**
1. Go to: https://github.com/settings/tokens/new
2. **Note**: "Homelab Agents CLI Access"
3. **Expiration**: Choose duration (90 days or no expiration)
4. **Scopes**: Select `repo` (full control of private repositories)
5. Click **"Generate token"**
6. **COPY THE TOKEN** (you won't see it again!)

**Step 2: Push with Token**
```bash
cd /home/munky/homelab-agents

# Push - Git will ask for credentials
git push -u origin main

# When prompted:
# Username: munkyHeadz
# Password: <paste your Personal Access Token>
```

**Step 3: Save Credentials (Optional)**
```bash
# Store credentials so you don't have to enter token every time
git config --global credential.helper store

# Next push will save the credentials
git push
```

### Option 2: SSH Key (More Secure, No Password)

**Step 1: Generate SSH Key (if you don't have one)**
```bash
ssh-keygen -t ed25519 -C "munky@homelab"
# Press Enter for default location
# Enter passphrase (optional but recommended)
```

**Step 2: Copy Public Key**
```bash
cat ~/.ssh/id_ed25519.pub
# Copy the output
```

**Step 3: Add to GitHub**
1. Go to: https://github.com/settings/keys
2. Click **"New SSH key"**
3. **Title**: "Homelab Server"
4. **Key**: Paste your public key
5. Click **"Add SSH key"**

**Step 4: Change Remote to SSH**
```bash
cd /home/munky/homelab-agents

# Change remote from HTTPS to SSH
git remote set-url origin git@github.com:munkyHeadz/homelab-agents.git

# Verify
git remote -v

# Push
git push -u origin main
```

### Option 3: GitHub CLI (gh)

**Step 1: Install GitHub CLI**
```bash
# If not installed
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**Step 2: Authenticate**
```bash
gh auth login
# Choose: GitHub.com
# Choose: HTTPS
# Authenticate with: Login with a web browser
# Follow the prompts
```

**Step 3: Push**
```bash
cd /home/munky/homelab-agents
git push -u origin main
```

## Quick Push (If You Already Have Auth Set Up)

If you've used GitHub from this server before:

```bash
cd /home/munky/homelab-agents
git push -u origin main
```

## After Successful Push

Once pushed, verify at:
https://github.com/munkyHeadz/homelab-agents

You should see:
- ✅ 51 files
- ✅ Initial commit
- ✅ README.md displayed on repo homepage
- ✅ All your agents, MCP servers, and bot code

## Next: Set Up Claude Code on the Web

After pushing:

1. **Go to**: https://claude.ai/code
2. **Connect GitHub**: Click "Connect GitHub" if not already connected
3. **Install Claude GitHub App**:
   - Go to: https://github.com/apps/claude-ai
   - Click "Configure"
   - Select repositories: Choose `homelab-agents`
   - Click "Save"
4. **Start Session**:
   - Select `homelab-agents` repository
   - Configure environment variables (see below)
   - Choose "Full Network Access"
   - Click "Start Session"

### Environment Variables for Claude Code Web

When starting a session, add these:

```
ANTHROPIC_API_KEY=<your-anthropic-key>
PROXMOX_HOST=192.168.1.99
PROXMOX_TOKEN_ID=root@pam!homelab
PROXMOX_TOKEN_SECRET=<your-proxmox-secret>
DOCKER_HOST=tcp://192.168.1.101:2375
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_ADMIN_IDS=500505500
POSTGRES_HOST=192.168.1.200
POSTGRES_USER=homelab
POSTGRES_PASSWORD=<your-db-password>
POSTGRES_DB=homelab_agents
```

## Troubleshooting

### "Authentication failed"
- **For HTTPS**: Use Personal Access Token, not your GitHub password
- **For SSH**: Ensure your public key is added to GitHub
- **For gh CLI**: Run `gh auth login` again

### "Permission denied (publickey)"
- You're using SSH but key isn't added to GitHub
- Run: `cat ~/.ssh/id_ed25519.pub` and add to https://github.com/settings/keys

### "remote: Repository not found"
- Double-check repository name: `munkyHeadz/homelab-agents`
- Verify you're logged in as `munkyHeadz`

### Need to change authentication method?
```bash
# Switch from HTTPS to SSH
git remote set-url origin git@github.com:munkyHeadz/homelab-agents.git

# Switch from SSH to HTTPS
git remote set-url origin https://github.com/munkyHeadz/homelab-agents.git
```

## Current Status

✅ Git repository initialized
✅ Remote configured: https://github.com/munkyHeadz/homelab-agents
✅ Initial commit ready (51 files, 14,773 lines)
⏳ **Authenticate and push** (follow steps above)
⏳ Install Claude GitHub App
⏳ Start coding at claude.ai/code

---

**Once pushed, your entire homelab infrastructure will be manageable through Claude Code on the web!** 🚀
