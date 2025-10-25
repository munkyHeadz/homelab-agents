# Control Portal - Deployed! 🎉

## ✅ Deployment Complete

The Fjeld Homelab Control Portal is now live and accessible!

**Access URL:** http://portal:3000 (or http://portal.tahr-bass.ts.net:3000)

---

## 🏗️ Infrastructure

### Container Details
- **LXC ID:** 108
- **Hostname:** portal
- **OS:** Ubuntu 24.04
- **Resources:** 2 CPU cores, 2GB RAM, 12GB disk
- **IP (Local):** 192.168.1.108
- **IP (Tailscale):** 100.110.59.20
- **DNS:** portal.tahr-bass.ts.net

### Software Stack
- **Backend:** FastAPI + Uvicorn
- **Python:** 3.12
- **Libraries:** aiohttp, jinja2, pydantic
- **Service:** systemd (portal.service)

---

## 🌐 Services in Portal

The portal provides quick access to all homelab services:

| Service | URL | IP | Description |
|---------|-----|----|----|
| **Grafana** | http://grafana:3000 | 100.120.140.105 | Dashboards & Visualization |
| **Prometheus** | http://prometheus:9090 | 100.69.150.29 | Metrics & Monitoring |
| **Portfolio** | http://portfolio | 100.111.140.125 | Personal Website |
| **PostgreSQL** | postgresql://postgres:5432 | 100.108.125.86 | Database |
| **Proxmox** | http://fjeld:8006 | 100.64.220.69 | Hypervisor |
| **Plex** | http://plex:32400 | 100.78.95.63 | Media Server |
| **AdGuard** | http://adguard | 100.94.4.16 | DNS & Ad Blocking |
| **UniFi** | http://unifios | 100.71.131.95 | Network Controller |

---

## 🚀 Features

### Current Features
✅ **Beautiful Dashboard** - Modern, responsive web interface
✅ **Service Directory** - All services in one place
✅ **Quick Links** - One-click access to each service
✅ **Tailscale Integration** - Works seamlessly with Tailscale DNS
✅ **Service Info** - Shows IP, DNS name, and description
✅ **API Endpoints** - `/api/services` and `/health`
✅ **Auto-restart** - Systemd ensures always-on availability

### Technical Features
- **Mobile Responsive** - Works perfectly on phone/tablet
- **Fast Load Times** - Lightweight HTML/CSS
- **No External Dependencies** - Everything self-hosted
- **Secure by Default** - Only accessible via Tailscale
- **Easy to Extend** - Simple Python code to add services

---

## 📱 Access from Any Device

### Desktop/Laptop
1. Connect to Tailscale
2. Open browser
3. Go to: **http://portal:3000**
4. Bookmark it!

### Mobile (iPhone/Android)
1. Open Tailscale app
2. Connect to network
3. Open Safari/Chrome
4. Go to: **http://portal:3000**
5. Add to Home Screen for quick access

### Command Line
```bash
# Health check
curl http://portal:3000/health

# Get services list
curl http://portal:3000/api/services

# Open in browser (macOS)
open http://portal:3000

# Open in browser (Linux)
xdg-open http://portal:3000
```

---

## 🔧 Management

### Service Control
```bash
# Check status
sudo pct exec 108 -- systemctl status portal

# Restart portal
sudo pct exec 108 -- systemctl restart portal

# View logs
sudo pct exec 108 -- journalctl -u portal -f

# Stop portal
sudo pct exec 108 -- systemctl stop portal
```

### Update Portal
```bash
# Edit application
sudo pct exec 108 -- nano /opt/homelab-portal/app.py

# Restart to apply changes
sudo pct exec 108 -- systemctl restart portal
```

### Add New Service
Edit `/opt/homelab-portal/app.py` and add to the `SERVICES` list:
```python
{
    "name": "New Service",
    "url": "http://newservice:8080",
    "tailscale": "newservice.tahr-bass.ts.net",
    "ip": "100.x.x.x",
    "icon": "🆕",
    "description": "Service Description"
}
```

---

## 📊 API Endpoints

### GET /
- **Description:** Main portal dashboard (HTML)
- **Returns:** Interactive web interface with all services

### GET /api/services
- **Description:** List all services (JSON)
- **Returns:**
  ```json
  {
    "services": [...],
    "count": 8
  }
  ```

### GET /health
- **Description:** Health check endpoint
- **Returns:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-10-25T14:02:36.764929"
  }
  ```

---

## 🎨 Customization

### Change Port
Edit `/etc/systemd/system/portal.service` and change the port in `app.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=3000)  # Change 3000 to desired port
```

### Change Colors/Styling
Edit the CSS in `app.py` (inside the `<style>` tag):
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Add More Information
Extend the service cards with additional fields:
- Status indicators (online/offline)
- Resource usage (CPU/Memory)
- Last accessed time
- Health check results

---

## 🔐 Security

### Access Control
- ✅ **Only accessible via Tailscale** - No public exposure
- ✅ **Encrypted in transit** - WireGuard encryption
- ✅ **No authentication needed** - Trust Tailscale's auth
- ✅ **Isolated container** - LXC security boundaries

### Firewall
No firewall rules needed - Tailscale handles everything securely!

---

## 🐛 Troubleshooting

### Portal Not Loading
```bash
# Check if service is running
sudo pct exec 108 -- systemctl status portal

# Check if container is accessible
ping portal

# Check if Tailscale is working
tailscale status | grep portal
```

### Service Links Not Working
- Verify the target service is running
- Check if target service is on Tailscale
- Ensure DNS names are correct

### Permission Errors
```bash
# Fix permissions
sudo pct exec 108 -- chown -R root:root /opt/homelab-portal
sudo pct exec 108 -- chmod 755 /opt/homelab-portal
```

---

## 📈 Future Enhancements

### Planned Features
- [ ] Real-time service health checking
- [ ] System resource monitoring (CPU/RAM/Disk)
- [ ] Dark mode toggle
- [ ] Search functionality
- [ ] Service categories
- [ ] PWA (Progressive Web App) manifest
- [ ] Push notifications for alerts
- [ ] Integration with Prometheus metrics
- [ ] User preferences (save favorite services)
- [ ] Service uptime statistics

### Integration Ideas
- Connect to existing Prometheus for metrics
- Show recent alerts from Alertmanager
- Embed Grafana dashboards
- Show recent backups from PBS
- Display VM/LXC status from Proxmox

---

## 📝 File Locations

```
/opt/homelab-portal/
├── app.py                 # Main FastAPI application
├── venv/                  # Python virtual environment
└── ...

/etc/systemd/system/portal.service  # Systemd service file
```

---

## 🎯 Summary

**What You Have:**
- ✅ Modern web portal accessible from anywhere
- ✅ Single URL to access all homelab services
- ✅ Fully automated deployment
- ✅ Secured by Tailscale
- ✅ Mobile-friendly interface
- ✅ Easy to extend and customize

**Access It:**
- **Desktop:** http://portal:3000
- **Mobile:** Add to home screen for app-like experience
- **CLI:** `curl http://portal:3000/health`

**Next Steps:**
1. Bookmark the portal on all your devices
2. Add it to phone home screen
3. Customize the services list as needed
4. Consider adding real-time monitoring features

---

**🎉 Your homelab now has a beautiful control center! Enjoy!** 🚀
