# SSL Certificate Setup Guide

This guide will help you activate SSL/HTTPS for your StatBox application using Let's Encrypt certificates.

## Prerequisites

- Your domain (`generativera.com` and `www.generativera.com`) must point to your server's IP address
- Port 80 must be accessible from the internet (for Let's Encrypt validation)
- You should be logged into your server as the `deploy` user

## Step-by-Step SSL Activation

### Step 1: Verify DNS Configuration

First, make sure your domain points to your server:

```bash
# Check DNS (replace with your actual domain)
dig generativera.com +short
dig www.generativera.com +short

# Both should return your server's IP address (e.g., 143.198.44.97)
```

If DNS is not configured yet, add A records in your domain registrar:
- `@` (or root) → Your server IP
- `www` → Your server IP

Wait a few minutes for DNS propagation, then verify again.

### Step 2: Install Certbot (if not already installed)

```bash
# Check if certbot is installed
which certbot

# If not installed, install it:
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

### Step 3: Stop Nginx Container

We need to temporarily stop nginx so certbot can use port 80:

```bash
cd ~/GRA1

# Stop nginx
docker-compose stop nginx

# Verify port 80 is free
sudo lsof -i :80
# Should show nothing (or only certbot if it's running)
```

**If port 80 is still in use**, check what's using it:

```bash
# Check what's using port 80
sudo lsof -i :80
# Or:
sudo netstat -tulpn | grep :80
# Or:
sudo ss -tulpn | grep :80
```

Common issues:
- Apache running: `sudo systemctl stop apache2 && sudo systemctl disable apache2`
- Nginx on host: `sudo systemctl stop nginx && sudo systemctl disable nginx`
- Another Docker container: `docker ps` then `docker stop <container-name>`

### Step 4: Generate SSL Certificates

```bash
# Generate certificates for both domains
sudo certbot certonly --standalone \
  -d generativera.com \
  -d www.generativera.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive

# Replace your-email@example.com with your actual email address
```

**Important**: Replace `your-email@example.com` with your real email. This email will be used for renewal reminders.

If successful, you'll see:
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/generativera.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/generativera.com/privkey.pem
```

### Step 5: Copy Certificates to Project Directory

```bash
cd ~/GRA1

# Create SSL directory if it doesn't exist
mkdir -p ssl

# Copy certificates
sudo cp /etc/letsencrypt/live/generativera.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/generativera.com/privkey.pem ssl/key.pem

# Set proper permissions
sudo chown -R $USER:$USER ssl/
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

# Verify files exist
ls -la ssl/
```

### Step 6: Update Environment Variables

Enable SSL in Django settings:

```bash
cd ~/GRA1

# Edit .env file
nano .env
```

Add or update this line:
```bash
USE_SSL=True
```

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

### Step 7: Pull Updated nginx.conf (if needed)

The nginx.conf file has been updated to enable SSL. If you need to pull the latest version:

```bash
cd ~/GRA1

# If using git, pull latest changes
git pull

# Or manually verify nginx.conf has the HTTPS server block enabled
# (it should already be updated if you're following this guide)
```

### Step 8: Restart Services

```bash
cd ~/GRA1

# Restart web service to pick up USE_SSL setting
docker-compose restart web

# Start nginx with SSL configuration
docker-compose up -d nginx

# Check that all services are running
docker-compose ps

# Check nginx logs for any errors
docker-compose logs nginx --tail=50
```

### Step 9: Verify SSL is Working

```bash
# Test HTTPS locally
curl -I https://localhost

# Test from your local machine (replace with your domain)
curl -I https://generativera.com

# Check SSL certificate details
openssl s_client -connect generativera.com:443 -servername generativera.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

### Step 10: Set Up Auto-Renewal

Let's Encrypt certificates expire every 90 days. Set up automatic renewal:

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# If successful, add to crontab
sudo crontab -e

# Add this line (checks twice daily at midnight and noon):
0 0,12 * * * certbot renew --quiet && cd /home/deploy/GRA1 && docker-compose restart nginx
```

**Note**: The renewal process will automatically renew certificates and restart nginx to load the new certificates.

## Troubleshooting

### Error: "Could not bind TCP port 80"

Port 80 is already in use. See Step 3 above to identify and stop the conflicting service.

### Error: "Failed to connect to generativera.com"

1. **Check DNS**: Make sure your domain points to your server IP
   ```bash
   dig generativera.com +short
   ```

2. **Check firewall**: Make sure port 80 is open
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Check domain accessibility**: Try accessing `http://generativera.com` in a browser first

### Error: "nginx: [emerg] cannot load certificate"

1. **Check certificate files exist**:
   ```bash
   ls -la ~/GRA1/ssl/
   ```

2. **Check file permissions**:
   ```bash
   chmod 600 ~/GRA1/ssl/key.pem
   chmod 644 ~/GRA1/ssl/cert.pem
   ```

3. **Verify certificate paths in nginx.conf**:
   ```bash
   grep ssl_certificate ~/GRA1/nginx.conf
   ```

### Certificate Expired or About to Expire

```bash
# Manually renew
sudo certbot renew

# Copy renewed certificates
sudo cp /etc/letsencrypt/live/generativera.com/fullchain.pem ~/GRA1/ssl/cert.pem
sudo cp /etc/letsencrypt/live/generativera.com/privkey.pem ~/GRA1/ssl/key.pem

# Restart nginx
cd ~/GRA1
docker-compose restart nginx
```

### Site Still Shows HTTP Instead of HTTPS

1. **Check USE_SSL in .env**:
   ```bash
   grep USE_SSL ~/GRA1/.env
   ```
   Should show: `USE_SSL=True`

2. **Restart web service**:
   ```bash
   cd ~/GRA1
   docker-compose restart web
   ```

3. **Clear browser cache** or try incognito mode

## Verification Checklist

After completing all steps, verify:

- [ ] DNS records point to your server IP
- [ ] Certificates generated successfully
- [ ] Certificates copied to `~/GRA1/ssl/`
- [ ] `USE_SSL=True` in `.env` file
- [ ] All Docker services running (`docker-compose ps`)
- [ ] HTTPS accessible: `https://generativera.com`
- [ ] HTTP redirects to HTTPS
- [ ] SSL certificate valid (check browser padlock icon)
- [ ] Auto-renewal configured in crontab

## Next Steps

Once SSL is working:

1. **Update Stripe webhook URL** to use HTTPS:
   - Go to Stripe Dashboard → Webhooks
   - Update endpoint URL to: `https://generativera.com/accounts/webhook/`

2. **Test your application** thoroughly with HTTPS enabled

3. **Monitor certificate renewal** (certbot will email you before expiration)

## Additional Resources

- Let's Encrypt Documentation: https://letsencrypt.org/docs/
- Certbot Documentation: https://certbot.eff.org/docs/
- Nginx SSL Configuration: https://nginx.org/en/docs/http/configuring_https_servers.html

