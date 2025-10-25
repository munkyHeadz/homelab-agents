# Tailscale DNS Setup - Complete Step-by-Step Guide

## 🎯 Goal

Transform your Tailscale network from:
- ❌ `grafana.tahr-bass.ts.net` (ugly, hard to remember)
- ❌ `100.64.220.69` (IP addresses)

To:
- ✅ `grafana.fjeld.internal` (clean, memorable)
- ✅ `prometheus.fjeld.internal`
- ✅ `portal.fjeld.internal`

---

## 📋 Prerequisites

- ✅ Tailscale installed and running (you already have this)
- ✅ Access to Tailscale admin console
- ✅ Admin/Owner role in your Tailscale network

---

## 🔧 Step 1: Access Tailscale Admin Console

1. **Open your browser**
2. **Go to:** https://login.tailscale.com/admin
3. **Log in** with your account
4. You should see your "tailnet" (network) dashboard

---

## 🌐 Step 2: Enable MagicDNS (Probably Already Enabled)

MagicDNS is what makes easy hostnames work instead of IP addresses.

### Check if MagicDNS is enabled:

1. In the left sidebar, click **"DNS"**
2. At the top of the page, you'll see a section called **"MagicDNS"**
3. Look for a toggle switch or status indicator

### If MagicDNS is OFF (unlikely for you):

1. Click the **"Enable MagicDNS"** button
2. Confirm when prompted

### If MagicDNS is already ON:

✅ Perfect! You'll see something like:
```
MagicDNS: Enabled
Devices can use hostnames like: hostname.tahr-bass.ts.net
```

---

## 🏷️ Step 3: Add Custom Domain (The Important Part!)

This is what changes `tahr-bass.ts.net` → `fjeld.internal`

### Detailed Instructions:

1. **Stay on the DNS page** (from Step 2)
2. **Scroll down** to find the section called **"Custom nameservers"** or **"Global nameservers"**
3. **Above that**, you should see a section called **"Search domains"** or **"Custom domains"**

   > **Note:** The exact wording varies. Look for something about "custom domains" or "search domains"

4. **Click "Add search domain"** or **"Add custom domain"**

5. **In the text field that appears, type:**
   ```
   fjeld.internal
   ```

6. **Click "Save"** or "Add"

### What This Does:

When you type just `grafana` or `prometheus` on any Tailscale device, it will automatically try:
- `grafana.fjeld.internal`
- `prometheus.fjeld.internal`

When you type the full name `grafana.fjeld.internal`, it resolves directly.

---

## 🔍 Step 4: Understand How DNS Will Work

### Automatic Hostname Creation

Tailscale MagicDNS creates DNS names based on **container hostnames**:

| Container | Hostname | Tailscale IP | Auto DNS Name |
|-----------|----------|--------------|---------------|
| LXC 104 | `prometheus` | 100.x.x.1 | `prometheus.fjeld.internal` |
| LXC 105 | `grafana` | 100.x.x.2 | `grafana.fjeld.internal` |
| LXC 141 | `portfolio` | 100.x.x.3 | `portfolio.fjeld.internal` |
| Host | `fjeld` | 100.64.220.69 | `fjeld.fjeld.internal` |

**Key point:** The hostname of the machine becomes the DNS name!

---

## 🎯 Step 5: Alternative - Use Tailscale Split DNS (Advanced Option)

If you want MORE control over DNS (optional, for later):

### What is Split DNS?

Split DNS lets you define custom DNS records that ONLY work on your Tailscale network.

### How to Add Custom DNS Records:

1. **Go to:** https://login.tailscale.com/admin/dns
2. **Scroll to "Nameservers"** section
3. **Click "Add nameserver"**
4. **Choose "Split DNS"**
5. **Configure:**
   - Domain: `fjeld.internal`
   - Nameserver: `100.x.x.x` (your own DNS server, like AdGuard)
   - OR use Tailscale's built-in DNS

### Why You Might Want This:

- Control DNS records manually
- Point multiple subdomains to same service
- Create aliases (e.g., `grafana.fjeld.internal` and `metrics.fjeld.internal` → same place)

**For now, skip this.** The automatic MagicDNS is simpler!

---

## ✅ Step 6: Verify DNS Setup

### Check from your current machine:

```bash
# Check Tailscale status
tailscale status

# Check DNS configuration
tailscale status --json | jq '.MagicDNSSuffix, .CurrentTailnet.MagicDNSSuffix'

# Should show something like:
# "fjeld.internal"  (if custom domain worked)
# OR
# "tahr-bass.ts.net"  (if still using default)

# Try to resolve your Proxmox host
ping fjeld.fjeld.internal

# Or with nslookup
nslookup fjeld.fjeld.internal
```

### Expected Results:

**If custom domain worked:**
```bash
$ ping fjeld.fjeld.internal
PING fjeld.fjeld.internal (100.64.220.69): 56 data bytes
64 bytes from 100.64.220.69: icmp_seq=0 ttl=64 time=2.3 ms
```

**If custom domain NOT working yet:**
```bash
$ ping fjeld.tahr-bass.ts.net
PING fjeld.tahr-bass.ts.net (100.64.220.69): 56 data bytes
64 bytes from 100.64.220.69: icmp_seq=0 ttl=64 time=2.3 ms
```

---

## 🐛 Troubleshooting: Custom Domain Not Working

### Issue 1: "Search domains" vs "Custom domain"

Different Tailscale versions have different UI.

**Try these locations:**

1. **DNS page → "Search domains"** section
   - Add: `fjeld.internal`

2. **DNS page → "MagicDNS" section → "Customize"**
   - Look for domain customization option

3. **Settings → General → "Tailnet name"**
   - This might show your tailnet name
   - Custom domains are SEPARATE from tailnet name

### Issue 2: Custom Domain Feature Not Available

**Check your Tailscale plan:**
- Custom domains might require a paid plan
- Free tier might be limited to default `.ts.net` domains

**Alternative solution if custom domain doesn't work:**
- Use the default MagicDNS: `hostname.tahr-bass.ts.net`
- Still works! Just longer names
- Examples:
  - `grafana.tahr-bass.ts.net`
  - `prometheus.tahr-bass.ts.net`
  - `portal.tahr-bass.ts.net`

### Issue 3: DNS Not Propagating

**If you added custom domain but it's not working:**

1. **Restart Tailscale on your devices:**
   ```bash
   sudo systemctl restart tailscaled
   # OR
   tailscale down && tailscale up
   ```

2. **Wait 5-10 minutes** - DNS changes can take time

3. **Check DNS servers on your device:**
   ```bash
   resolvectl status
   # OR
   cat /etc/resolv.conf
   ```

   Look for `100.100.100.100` (Tailscale's DNS)

---

## 📝 What To Tell Me After Setup

After you've completed the steps above, let me know:

1. ✅ **Did custom domain work?**
   - Run: `tailscale status --json | jq '.MagicDNSSuffix'`
   - Tell me the output

2. ✅ **What DNS suffix are you using?**
   - `fjeld.internal` (custom domain worked!)
   - OR `tahr-bass.ts.net` (default, still fine!)

3. ✅ **Can you ping the host?**
   - Run: `ping fjeld.fjeld.internal` (or `ping fjeld.tahr-bass.ts.net`)
   - Does it resolve to `100.64.220.69`?

**Once I know this, I'll proceed with installing Tailscale in your LXC containers!**

---

## 🎯 Summary: What This Achieves

### Before:
- Access services by IP: `http://192.168.1.105:3000`
- Only works on local network
- Hard to remember

### After DNS Setup:
- Access services by name: `http://grafana.fjeld.internal`
- Works from anywhere via Tailscale
- Easy to remember
- Works on phone, laptop, anywhere

### Next Steps (After DNS):
1. Install Tailscale in LXC 104 (Prometheus)
2. Install Tailscale in LXC 105 (Grafana)
3. Install Tailscale in LXC 141 (Portfolio)
4. Set proper hostnames
5. Test access: `http://grafana.fjeld.internal`
6. Build control portal
7. Deploy public status page

---

## 🚀 Quick Reference: Tailscale Admin Console URLs

- **Main Dashboard:** https://login.tailscale.com/admin/machines
- **DNS Settings:** https://login.tailscale.com/admin/dns
- **ACLs (Advanced):** https://login.tailscale.com/admin/acls
- **Settings:** https://login.tailscale.com/admin/settings

---

## 📞 Need Help?

**If you're stuck, send me:**

1. Screenshot of your Tailscale DNS page
2. Output of: `tailscale status --json | jq '.MagicDNSSuffix'`
3. Output of: `tailscale status | head -5`

And I'll help diagnose the issue!

---

**Ready? Go to https://login.tailscale.com/admin/dns and let's set this up!** 🚀
