# Admin Security Setup Guide

This guide explains how to configure the multi-layer security system for the Django admin panel.

## Security Layers Implemented

### ✅ 1. Custom Admin URL Path
- **Default**: `/whereadmingoeshere/` (instead of `/admin/`)
- **Configurable**: Set `ADMIN_URL` in `.env` file

### ✅ 2. IP Restriction
- Only whitelisted IPs can access the admin panel
- Most effective security measure
- Configure via `ADMIN_ALLOWED_IPS` in `.env`

### ✅ 3. Server-Level Authentication (Nginx Basic Auth)
- Additional authentication layer before Django admin
- Requires username/password at the web server level
- Configured in `nginx.conf`

### ✅ 4. Token-Based Pre-Authentication (Double Login)
- First layer: Secret token required (URL parameter, header, or cookie)
- Second layer: Django admin login
- Configure via `ADMIN_ACCESS_TOKEN` in `.env`

### ✅ 5. Hide Admin from Unauthorized Visitors
- Returns 404 instead of 403 for unauthorized access
- Prevents attackers from detecting the admin path exists
- Enabled by default

### ✅ 6. Rate Limiting
- Admin: 10 requests per minute per IP
- General: 100 requests per minute per IP
- Configured in `nginx.conf`

### ✅ 7. Disable Directory Indexing
- Prevents directory listing
- Configured globally in `nginx.conf`

### ✅ 8. WAF-like Protection
- Blocks suspicious request patterns
- Prevents common attack vectors
- Configured in `nginx.conf`

## Configuration Steps

### Step 1: Set Environment Variables

Add to your `.env` file:

```bash
# Admin URL path (default: whereadmingoeshere)
ADMIN_URL=whereadmingoeshere

# IP Restriction: Comma-separated list of allowed IPs
# Leave empty to disable IP restriction
ADMIN_ALLOWED_IPS=123.45.67.89,98.76.54.32

# Token for pre-authentication (generate a strong random token)
# Generate with: openssl rand -hex 32
ADMIN_ACCESS_TOKEN=your-very-secure-random-token-here

# Hide admin from unauthorized (default: True)
ADMIN_HIDE_FROM_UNAUTHORIZED=True
```

### Step 2: Generate Admin Access Token

Generate a strong random token:

```bash
# Option 1: Using OpenSSL
openssl rand -hex 32

# Option 2: Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the generated token to `ADMIN_ACCESS_TOKEN` in your `.env` file.

### Step 3: Set Up Nginx Basic Authentication

Create the password file for Nginx basic auth:

**Option 1: Using htpasswd (Recommended)**

```bash
# Install htpasswd if not already installed
sudo apt install apache2-utils  # Debian/Ubuntu
# or
sudo yum install httpd-tools     # CentOS/RHEL

# Create password file (will prompt for password)
sudo htpasswd -c /etc/nginx/.htpasswd admin

# To add more users later (without -c flag):
sudo htpasswd /etc/nginx/.htpasswd another-user

# Set proper permissions
sudo chmod 600 /etc/nginx/.htpasswd
sudo chown www-data:www-data /etc/nginx/.htpasswd
```

**Option 2: Using OpenSSL (No installation needed)**

```bash
# Create password file with OpenSSL (replace 'your-password' with your actual password)
echo "admin:$(openssl passwd -apr1 'your-password')" | sudo tee /etc/nginx/.htpasswd

# Set proper permissions
sudo chmod 600 /etc/nginx/.htpasswd
sudo chown www-data:www-data /etc/nginx/.htpasswd
```

**Option 3: Using Python (Alternative)**

```bash
# Generate password hash with Python
python3 -c "import crypt; print('admin:' + crypt.crypt('your-password', crypt.mksalt(crypt.METHOD_SHA512)))" | sudo tee /etc/nginx/.htpasswd

# Set proper permissions
sudo chmod 600 /etc/nginx/.htpasswd
sudo chown www-data:www-data /etc/nginx/.htpasswd
```

### Step 4: Update Nginx Configuration

The `nginx.conf` file already includes:
- Basic authentication for admin path
- Rate limiting
- Directory indexing disabled
- WAF-like protection

**Important**: If you change `ADMIN_URL` in Django settings, update the location block in `nginx.conf`:

```nginx
location ~ ^/your-custom-path(/.*)?$ {
    # ... security settings ...
}
```

### Step 5: Restart Services

```bash
# Restart Django (if using Docker)
docker-compose restart web

# Restart Nginx
sudo systemctl restart nginx
# or if using Docker
docker-compose restart nginx
```

## Accessing the Admin Panel

### Method 1: URL Token (Easiest)

```
https://yourdomain.com/whereadmingoeshere/?token=YOUR_TOKEN
```

### Method 2: Header Token

Use a browser extension or curl:

```bash
curl -H "X-Admin-Token: YOUR_TOKEN" https://yourdomain.com/whereadmingoeshere/
```

### Method 3: Cookie Token

Set cookie in browser console:

```javascript
document.cookie = "admin_access_token=YOUR_TOKEN; path=/";
```

Then navigate to: `https://yourdomain.com/whereadmingoeshere/`

### After Token Authentication

1. **Nginx Basic Auth**: Enter username/password (configured in `.htpasswd`)
2. **Django Admin Login**: Enter Django superuser credentials

## Security Best Practices

1. **Use IP Restriction**: Most effective - only allow your IP(s)
2. **Strong Token**: Use a long, random token (32+ characters)
3. **Change Default Path**: Use a custom `ADMIN_URL` that's not easily guessed
4. **Regular Updates**: Rotate tokens and passwords periodically
5. **Monitor Logs**: Check Nginx and Django logs for unauthorized access attempts
6. **VPN Access**: If using IP restriction, access via VPN from trusted networks

## Troubleshooting

### Can't Access Admin

1. **Check IP**: Verify your IP is in `ADMIN_ALLOWED_IPS`
2. **Check Token**: Verify token matches `ADMIN_ACCESS_TOKEN`
3. **Check Nginx Auth**: Verify `.htpasswd` file exists and is readable
4. **Check Logs**: 
   ```bash
   # Django logs
   docker-compose logs web | grep -i admin
   
   # Nginx logs
   sudo tail -f /var/log/nginx/error.log
   ```

### Getting 404 Instead of Login

This is expected behavior when `ADMIN_HIDE_FROM_UNAUTHORIZED=True`. The admin path is hidden from unauthorized visitors. Make sure:
- Your IP is whitelisted
- You're using the correct token
- You've passed Nginx basic auth

### Rate Limiting Issues

If you're being rate limited:
- Wait 1 minute for the limit to reset
- Increase rate limits in `nginx.conf` if needed
- Check if you're behind a shared IP (corporate network, VPN)

## Testing Security

Test that unauthorized access is blocked:

```bash
# Should return 404 (not 403)
curl https://yourdomain.com/whereadmingoeshere/

# Should return 404 (wrong token)
curl "https://yourdomain.com/whereadmingoeshere/?token=wrong-token"

# Should return 404 (wrong IP)
# Test from a different IP address
```

## Environment Variables Summary

| Variable | Description | Example |
|----------|-------------|---------|
| `ADMIN_URL` | Admin path (default: whereadmingoeshere) | `whereadmingoeshere` |
| `ADMIN_ALLOWED_IPS` | Comma-separated IP whitelist | `123.45.67.89,98.76.54.32` |
| `ADMIN_ACCESS_TOKEN` | Pre-authentication token | `abc123...` (32+ chars) |
| `ADMIN_HIDE_FROM_UNAUTHORIZED` | Hide admin (404 vs 403) | `True` |

## Additional Security Recommendations

1. **Use Cloudflare**: Enable Cloudflare Access for additional protection
2. **VPN Only**: Restrict admin to VPN-only access
3. **2FA**: Enable two-factor authentication for Django superusers
4. **Fail2Ban**: Set up Fail2Ban to ban IPs after failed login attempts
5. **Regular Audits**: Review access logs regularly

