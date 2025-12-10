# Deploy to Digital Ocean Server - Quick Guide

## Server Information
- **IP Address**: 147.182.153.228
- **Git Repository**: pooryaselkghafari/GRA2

## Prerequisites
Before starting, ensure you have:
- SSH access to the server (147.182.153.228)
- Docker and Docker Compose installed on the server
- Git installed on the server

## Step 1: Push Your Code to GitHub

On your local machine:

```bash
cd /Users/pooryaselkghafari/Desktop/GRA

# Check current status
git status

# Add all changes
git add .

# Commit changes
git commit -m "Prepare for deployment to Digital Ocean"

# Push to GitHub
git push origin main
# or if your branch is named differently:
# git push origin master
```

## Step 2: Connect to Your Digital Ocean Server

```bash
# Connect to your server (replace with your actual SSH key/user)
ssh root@147.182.153.228
# OR if you have a non-root user:
# ssh deploy@147.182.153.228
```

## Step 3: Initial Server Setup (First Time Only)

If this is the first time setting up the server, run these commands:

```bash
# Update system packages
apt update && apt upgrade -y

# Install required packages
apt install -y git curl wget

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose (if not already installed)
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Set up firewall (if needed)
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

## Step 4: Clone Your Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone https://github.com/pooryaselkghafari/GRA2.git statbox
cd GRA
```

**Note**: If your repository is private, you'll need to set up authentication:
- **Option A**: Use SSH keys (recommended)
- **Option B**: Use a GitHub Personal Access Token

## Step 5: Configure Environment Variables

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file
nano .env
```

Update the following critical variables in `.env`:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-here-generate-a-long-random-string
DEBUG=False
ALLOWED_HOSTS=147.182.153.228,your-domain.com,www.your-domain.com

# Database Settings
DB_NAME=statbox
DB_USER=postgres
DB_PASSWORD=your-strong-database-password-here
DB_HOST=localhost
DB_PORT=5432

# Stripe Settings (if using Stripe)
STRIPE_PUBLIC_KEY=pk_live_your_stripe_public_key
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Email Settings
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=your-resend-api-key-here
DEFAULT_FROM_EMAIL=noreply@your-domain.com

# Redis Settings
REDIS_URL=redis://localhost:6379/0
```

**Generate SECRET_KEY**:
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

## Step 6: Update Nginx Configuration

```bash
# Edit nginx configuration
nano nginx.conf
```

Update the `server_name` directives to include your IP address:

```nginx
# Around line 61 and 70, update:
server_name 147.182.153.228 your-domain.com www.your-domain.com;
```

**Note**: If you don't have a domain yet, you can use just the IP address:
```nginx
server_name 147.182.153.228 _;
```

## Step 7: Deploy the Application

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

This will:
- Build Docker containers
- Start database and Redis
- Run migrations
- Create a superuser (admin/admin123)
- Collect static files
- Start all services

## Step 8: Set Up SSL (Optional but Recommended)

If you have a domain name:

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Stop nginx temporarily
docker-compose stop nginx

# Check if port 80 is free (if not, see troubleshooting below)
sudo lsof -i :80
# Or: sudo ss -tulpn | grep :80

# If port 80 is in use, stop the conflicting service:
# - Apache: sudo systemctl stop apache2 && sudo systemctl disable apache2
# - Nginx (host): sudo systemctl stop nginx && sudo systemctl disable nginx
# - Docker container: docker ps then docker stop <container-name>
# Or use the fix script: ./fix-port-80.sh

# Generate SSL certificates
sudo certbot certonly --standalone -d generativera.com -d www.generativera.com

# Copy certificates
mkdir -p ssl
sudo cp /etc/letsencrypt/live/generativera.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/generativera.com/privkey.pem ssl/key.pem
sudo chown -R $USER:$USER ssl/
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

# Restart nginx
docker-compose up -d nginx
```

If you don't have a domain yet, you can skip SSL for now and access via HTTP.

## Step 9: Verify Deployment

```bash
# Check running containers
docker-compose ps

# Check logs
docker-compose logs web
docker-compose logs nginx

# Test the application
curl http://localhost/health/
```

## Step 10: Access Your Application

- **HTTP**: http://147.182.153.228
- **HTTPS** (if SSL configured): https://147.182.153.228
- **Admin Panel**: http://147.182.153.228/whereadmingoeshere
  - Username: `admin`
  - Password: `admin123` (change this immediately!)

## Common Commands

### View Logs
```bash
docker-compose logs -f web
docker-compose logs -f nginx
docker-compose logs -f db
```

### Restart Services
```bash
docker-compose restart
docker-compose restart web
```

### Update Application
```bash
cd ~/statbox
git pull
docker-compose down
docker-compose build
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
```

### Stop Services
```bash
docker-compose down
```

### Start Services
```bash
docker-compose up -d
```

## Troubleshooting

### Port 80 Already in Use (Certbot Error)

**Error**: `Could not bind TCP port 80 because it is already in use`

**Quick Fix**:

```bash
# Option 1: Use the fix script (recommended)
chmod +x fix-port-80.sh
./fix-port-80.sh

# Option 2: Manual fix - identify what's using port 80
sudo lsof -i :80
# Or: sudo ss -tulpn | grep :80
# Or: sudo netstat -tulpn | grep :80

# Stop common services:
# Apache
sudo systemctl stop apache2
sudo systemctl disable apache2

# Nginx (host service, not Docker)
sudo systemctl stop nginx
sudo systemctl disable nginx

# Docker nginx container
docker-compose stop nginx
# Or: docker stop nginx

# Verify port is free
sudo lsof -i :80
# Should show nothing

# Now run certbot
sudo certbot certonly --standalone -d generativera.com -d www.generativera.com
```

### 502 Bad Gateway Error

**Error**: `502 Bad Gateway` from nginx

This means nginx is running but can't connect to your Django application.

**Quick Fix**:

```bash
# Option 1: Use the fix script (recommended)
chmod +x fix-502-error.sh
./fix-502-error.sh

# Option 2: Manual diagnosis
# 1. Check if web container is running
docker-compose ps web

# 2. If not running, check logs for errors
docker-compose logs --tail=50 web

# 3. Common fixes:
# Fix logs directory permissions
mkdir -p logs && chmod 755 logs && touch logs/django.log && chmod 644 logs/django.log

# Restart all services
docker-compose restart

# Test Django directly
curl http://localhost:8000/health/
```

**Common Causes**:
- Web container crashed (check: `docker-compose logs web`)
- Logs directory permission issues (run: `./fix-logs-permission.sh`)
- Database not ready (wait 10-15 seconds after starting)
- Missing environment variables in `.env` file

### Can't Access Application
1. Check firewall: `ufw status`
2. Check containers: `docker-compose ps`
3. Check logs: `docker-compose logs web`

### Database Connection Errors
1. Check database is running: `docker-compose ps db`
2. Verify `.env` file has correct DB credentials
3. Check database logs: `docker-compose logs db`

### Port 80 Already in Use (Certbot Error)

**Error**: `Could not bind TCP port 80 because it is already in use`

**Quick Fix**:

```bash
# Option 1: Use the fix script (recommended)
chmod +x fix-port-80.sh
./fix-port-80.sh

# Option 2: Manual fix - identify what's using port 80
sudo lsof -i :80
# Or: sudo ss -tulpn | grep :80
# Or: sudo netstat -tulpn | grep :80

# Stop common services:
# Apache
sudo systemctl stop apache2
sudo systemctl disable apache2

# Nginx (host service, not Docker)
sudo systemctl stop nginx
sudo systemctl disable nginx

# Docker nginx container
docker-compose stop nginx
# Or: docker stop nginx

# Verify port is free
sudo lsof -i :80
# Should show nothing

# Now run certbot
sudo certbot certonly --standalone -d generativera.com -d www.generativera.com
```

## Security Checklist

- [ ] Changed default admin password
- [ ] Set strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configured firewall (UFW)
- [ ] Set up SSL certificates (if using domain)
- [ ] Set strong database password
- [ ] Configured email service
- [ ] Set up backups

## Next Steps

1. **Change Admin Password**:
   ```bash
   docker-compose exec web python manage.py changepassword admin
   ```

2. **Set Up Backups** (see DEPLOYMENT_QUICK_REFERENCE.md)

3. **Configure Domain** (if you have one):
   - Point DNS A record to 147.182.153.228
   - Update nginx.conf with your domain
   - Set up SSL certificates

4. **Set Up Monitoring**:
   - Enable DigitalOcean monitoring
   - Set up log rotation
   - Configure alerts

## Support

For detailed deployment instructions, see:
- `DIGITALOCEAN_DEPLOYMENT.md` - Complete step-by-step guide
- `DEPLOYMENT_QUICK_REFERENCE.md` - Quick command reference
- `DEPLOYMENT.md` - General deployment guide
