# 🚀 Quick Start: AI Automation Implementation

**Goal:** Get your first AI-powered automation running in < 1 hour

---

## ⚡ Fast Track: Ollama + First Workflow

### Step 1: Deploy Ollama (15 minutes)

```bash
# Create LXC container for AI
pct create 115 local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname ai-brain \
  --cores 4 \
  --memory 8192 \
  --rootfs local-lvm:40 \
  --swap 512 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.115/24,gw=192.168.1.1 \
  --features nesting=1,keyctl=1 \
  --unprivileged 1

# Start container
pct start 115
pct enter 115

# Install Docker (for Open WebUI)
apt update && apt install -y curl
curl -fsSL https://get.docker.com | sh

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
systemctl enable ollama
systemctl start ollama

# Pull your first model (this will take a few minutes)
ollama pull llama3.2:latest

# Install Open WebUI
docker run -d \
  --name open-webui \
  -p 8080:8080 \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main

# Exit container
exit
```

**Test it:** Visit `http://192.168.1.115:8080`
- Create admin account
- Try: "Explain what a homelab is and suggest improvements"

### Step 2: Deploy n8n (10 minutes)

```bash
# On docker-gateway (LXC 101)
pct exec 101 -- bash -c 'cd /opt && mkdir -p n8n/data'

# Create n8n container
pct exec 101 -- docker run -d \
  --name n8n \
  --restart unless-stopped \
  -p 5678:5678 \
  -e N8N_HOST=n8n.fjeld.tech \
  -e WEBHOOK_URL=https://n8n.fjeld.tech/ \
  -v /opt/n8n/data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

**Add Traefik route:**

```bash
pct exec 101 -- bash -c 'cat >> /opt/traefik/docker-compose.yml' <<'EOF'

  n8n:
    image: docker.n8n.io/n8nio/n8n
    container_name: n8n
    restart: unless-stopped
    networks:
      - traefik
    environment:
      - N8N_HOST=n8n.fjeld.tech
      - WEBHOOK_URL=https://n8n.fjeld.tech/
      - GENERIC_TIMEZONE=UTC
    volumes:
      - /opt/n8n/data:/home/node/.n8n
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.n8n.rule=Host(`n8n.fjeld.tech`)"
      - "traefik.http.routers.n8n.entrypoints=websecure"
      - "traefik.http.routers.n8n.tls.certresolver=cloudflare"
      - "traefik.http.services.n8n.loadbalancer.server.port=5678"
EOF

# Restart Traefik stack
pct exec 101 -- bash -c 'cd /opt/traefik && docker compose up -d'
```

**Test it:** Visit `https://n8n.fjeld.tech`
- Set up owner account
- Complete the tutorial

### Step 3: First AI Workflow - Smart Alert Handler (30 minutes)

**In n8n web UI:**

1. **Create new workflow** called "AI Alert Responder"

2. **Add Webhook node:**
   - Method: POST
   - Path: `alert-webhook`
   - Note the webhook URL

3. **Add HTTP Request node (to Ollama):**
   - Method: POST
   - URL: `http://192.168.1.115:11434/api/generate`
   - Body:
   ```json
   {
     "model": "llama3.2",
     "prompt": "Analyze this Prometheus alert and provide: 1) Plain English summary, 2) Likely root cause, 3) Recommended fix. Alert: {{ $json.body }}",
     "stream": false
   }
   ```

4. **Add Telegram node:**
   - Operation: Send Message
   - Chat ID: `500505500`
   - Text:
   ```
   🤖 *AI Alert Analysis*

   {{ $json.response }}
   ```

5. **Save and activate workflow**

6. **Update Alertmanager config:**

```bash
pct exec 101 -- bash -c 'cat > /opt/monitoring/alertmanager/config/alertmanager.yml' <<'EOF'
global:
  resolve_timeout: 5m

route:
  group_by: ["alertname", "cluster", "service"]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: "ai-handler"

receivers:
  - name: "ai-handler"
    webhook_configs:
      - url: "https://n8n.fjeld.tech/webhook/alert-webhook"
        send_resolved: true

  - name: "telegram"
    webhook_configs:
      - url: "http://172.19.0.5:8080/alert"
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: "critical"
    target_match:
      severity: "warning"
    equal: ["alertname", "instance"]
EOF

# Reload Alertmanager
pct exec 101 -- docker restart alertmanager
```

7. **Test it:**

```bash
# Trigger a test alert
curl -X POST http://100.67.169.111:9093/api/v2/alerts -H "Content-Type: application/json" -d '[{
  "labels": {
    "alertname": "TestAIAlert",
    "severity": "warning",
    "instance": "test-system"
  },
  "annotations": {
    "summary": "High CPU usage detected",
    "description": "CPU usage has been above 90% for 5 minutes on test-system"
  }
}]'
```

**Expected Result:** Within seconds, you should receive a Telegram message with AI-generated analysis!

---

## 🎯 Next Quick Wins

### Workflow 2: Auto-Documentation Generator (15 min)

```
Schedule Trigger (Daily 3 AM)
  └─→ Proxmox API (list all containers)
       └─→ HTTP Request to Ollama
            Prompt: "Generate markdown documentation for this infrastructure"
       └─→ HTTP Request (GitHub API)
            └─→ Commit updated INFRASTRUCTURE.md
```

### Workflow 3: Log Pattern Detector (20 min)

```
Webhook from Loki/Promtail (errors only)
  └─→ Batch errors (every 5 min)
       └─→ Ollama: "Find patterns in these errors"
            └─→ If pattern found:
                 ├─→ Create GitHub issue
                 └─→ Send Telegram alert
```

### Workflow 4: Backup Health Check (10 min)

```
Schedule Trigger (After backup runs - 3 AM)
  └─→ SSH into docker-gateway
       └─→ Check `/var/log/restic-backup.log`
            └─→ Ollama: "Did backup succeed? Any warnings?"
                 └─→ Send summary to Telegram
```

---

## 🔧 Useful Ollama API Endpoints

```bash
# List loaded models
curl http://192.168.1.115:11434/api/tags

# Generate completion
curl http://192.168.1.115:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'

# Chat (maintains context)
curl http://192.168.1.115:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}'
```

---

## 📱 Enhanced Telegram Bot Integration

### Upgrade your existing bot to use AI:

```python
# /home/munky/homelab-agents/agents/telegram_bot.py

import requests

OLLAMA_URL = "http://192.168.1.115:11434/api/generate"

def ask_ai(question):
    """Send question to local LLM"""
    response = requests.post(OLLAMA_URL, json={
        "model": "llama3.2",
        "prompt": f"You are a homelab assistant. Answer this question: {question}",
        "stream": False
    })
    return response.json()["response"]

# Add new command
@bot.message_handler(commands=['ask'])
def handle_ask(message):
    """Ask AI anything about the homelab"""
    question = message.text.replace('/ask', '').strip()

    if not question:
        bot.reply_to(message, "Usage: /ask <your question>")
        return

    bot.reply_to(message, "🤔 Thinking...")
    answer = ask_ai(question)
    bot.reply_to(message, f"🤖 {answer}")
```

**Test it:**
```
/ask How much RAM is the postgres container using?
/ask What's the best way to backup Docker volumes?
/ask Explain what Traefik does in simple terms
```

---

## 🎓 Learning Resources

### n8n Templates to Import
- [Community Library](https://n8n.io/workflows)
- Search for: "Prometheus", "monitoring", "DevOps"

### Ollama Models to Try
```bash
# Coding assistant (better for infrastructure code)
ollama pull deepseek-coder:6.7b

# Fast responses (good for simple queries)
ollama pull mistral:7b

# Reasoning (complex problem solving)
ollama pull llama3.2:70b  # Needs 16GB+ RAM
```

### n8n + AI Tutorials
- [n8n AI Agents Guide](https://blog.n8n.io/ai-agents/)
- [Workflow Automation with LLMs](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatopenai/)

---

## 🐛 Troubleshooting

### Ollama not responding
```bash
pct exec 115 -- systemctl status ollama
pct exec 115 -- journalctl -u ollama -n 50
```

### n8n webhook not working
```bash
# Check n8n logs
pct exec 101 -- docker logs n8n -f

# Test webhook directly
curl -X POST https://n8n.fjeld.tech/webhook/alert-webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Model taking too long
```bash
# Use smaller model for faster responses
ollama pull llama3.2:1b  # Lightweight version
```

---

## 📊 What You've Built

After completing these quick starts, you have:

✅ Local AI brain (Ollama) running 24/7
✅ Visual automation platform (n8n)
✅ AI-powered alert analysis
✅ Foundation for all future automation
✅ Zero external API costs
✅ Complete data privacy

**Time invested:** ~1 hour
**Value unlocked:** Infinite automation possibilities

---

## 🚀 What's Next?

Choose your path:

**🤖 Path 1: More AI Workflows**
- Go to `AI_AUTOMATION_ROADMAP.md` Phase 2
- Build log analysis, auto-documentation, etc.

**🔧 Path 2: CrewAI Agents**
- Skip to `AI_AUTOMATION_ROADMAP.md` Phase 3
- Deploy autonomous agent teams

**📊 Path 3: Enhanced Monitoring**
- Jump to `AI_AUTOMATION_ROADMAP.md` Phase 4
- Add ML to Grafana, deploy Loki

**Pick one and go deep. Don't try to do everything at once.**

---

*Remember: The goal isn't to automate everything immediately.*
*The goal is to build a system that learns and improves itself over time.*

**Start small. Think big. Automate everything. 🚀**
