# Tailscale OAuth API Setup

## 🔑 Current Status

**OAuth Client Created:** ✅
- Client ID: `kGUUdKHkUG11CNTRL`
- Client Secret: `tskey-client-kGUUdKHkUG11CNTRL-DVN6LY546JdspG4wNTRPHdtaSY8HbMnpL`

**Issue:** OAuth client has no permissions ❌
- Error: "calling actor does not have enough permissions to perform this function"

---

## 🛠️ How to Grant Permissions

### Step 1: Go to OAuth Clients Settings

1. Open: https://login.tailscale.com/admin/settings/oauth
2. Find your OAuth client (ID: `kGUUdKHkUG11CNTRL`)
3. Click **"Edit"** or **"Manage Permissions"**

### Step 2: Grant Required Permissions

**For full API access, enable these scopes:**

#### Device Management:
- ✅ **`devices:read`** - List and view devices
- ✅ **`devices:write`** - Modify device settings

#### DNS Management:
- ✅ **`dns:read`** - Read DNS configuration
- ✅ **`dns:write`** - Modify DNS records

#### Auth Keys:
- ✅ **`keys:read`** - List auth keys
- ✅ **`keys:write`** - Create/revoke auth keys

#### Routes:
- ✅ **`routes:read`** - View subnet routes
- ✅ **`routes:write`** - Manage routes

#### ACLs (Optional):
- ✅ **`acl:read`** - Read ACL configuration
- ✅ **`acl:write`** - Modify ACLs

### Step 3: Save Changes

Click **"Save"** or **"Update"**

---

## 🧪 Testing After Granting Permissions

Once you've granted permissions, I can test these API endpoints:

### List All Devices
```bash
curl -H "Authorization: Bearer tskey-client-..." \
  https://api.tailscale.com/api/v2/tailnet/-/devices
```

**What I can do:**
- See all devices on your network
- Check device status (online/offline)
- View device IPs and hostnames
- Monitor last seen times

### Manage DNS
```bash
# Get DNS configuration
curl -H "Authorization: Bearer tskey-client-..." \
  https://api.tailscale.com/api/v2/tailnet/-/dns/nameservers

# Add DNS record
curl -X POST -H "Authorization: Bearer tskey-client-..." \
  -d '{"hostname": "service.fjeld.internal", "ip": "100.x.x.x"}' \
  https://api.tailscale.com/api/v2/tailnet/-/dns/names
```

**What I can do:**
- Programmatically add DNS records
- Update MagicDNS configuration
- Manage split DNS

### Create Auth Keys
```bash
curl -X POST -H "Authorization: Bearer tskey-client-..." \
  -d '{"reusable": true, "ephemeral": false}' \
  https://api.tailscale.com/api/v2/tailnet/-/keys
```

**What I can do:**
- Generate reusable auth keys for new containers
- Create ephemeral keys for temporary access
- Automate device onboarding

### Manage Devices
```bash
# Update device hostname
curl -X POST -H "Authorization: Bearer tskey-client-..." \
  -d '{"hostname": "new-name"}' \
  https://api.tailscale.com/api/v2/device/{deviceId}

# Delete device
curl -X DELETE -H "Authorization: Bearer tskey-client-..." \
  https://api.tailscale.com/api/v2/device/{deviceId}
```

**What I can do:**
- Rename devices remotely
- Remove offline devices
- Update device tags

---

## 🎯 What This Enables

### Automation Possibilities:

1. **Automatic Device Onboarding**
   - Generate reusable auth keys
   - Install Tailscale in new containers with single command
   - No manual authorization needed

2. **Dynamic DNS Management**
   - Automatically create DNS records when containers start
   - Update records when IPs change
   - Remove records when containers are deleted

3. **Monitoring & Alerting**
   - Check device status programmatically
   - Alert when devices go offline
   - Monitor network health

4. **Control Portal Integration**
   - Show all Tailscale devices in portal
   - One-click device management
   - Real-time network topology

5. **GitOps-Style Management**
   - Define infrastructure in code
   - Automatically sync Tailscale state
   - Version control your network config

---

## 📋 Recommended Minimal Permissions

If you don't want full access, grant at minimum:

- ✅ `devices:read` - To list and monitor devices
- ✅ `dns:read` - To view DNS configuration
- ✅ `keys:write` - To generate auth keys for automation

This allows me to:
- Monitor your network
- Generate auth keys for new containers
- View DNS configuration

But prevents me from:
- Modifying/deleting devices
- Changing DNS records
- Altering ACLs

---

## 🔐 Security Considerations

**OAuth client secrets are sensitive!**

✅ **Good:**
- Stored in `.env` file (gitignored)
- Only accessible on your Proxmox host
- Can be revoked anytime in Tailscale console

⚠️ **Be Aware:**
- Anyone with the secret can use the API
- Grant only permissions you need
- Rotate secrets periodically
- Monitor API usage in Tailscale admin

---

## 🚀 After Granting Permissions

Let me know when you've granted permissions, and I'll:

1. **Test the API** - Verify all endpoints work
2. **Create a Tailscale management module** - Python wrapper for the API
3. **Integrate with the control portal** - Show devices in dashboard
4. **Automate future deployments** - Generate auth keys automatically

---

## 📝 Quick Setup Checklist

- [x] OAuth client created
- [ ] Grant `devices:read` permission
- [ ] Grant `devices:write` permission
- [ ] Grant `dns:read` permission
- [ ] Grant `keys:write` permission
- [ ] Save changes
- [ ] Test API access

**Once done, tell me and I'll verify everything works!** 🎉
