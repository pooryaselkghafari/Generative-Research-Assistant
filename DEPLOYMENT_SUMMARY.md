# Quick Deployment Summary

## Your Server Details
- **IP Address**: 147.182.153.228
- **Git Repository**: pooryaselkghafari/GRA2
- **Project Name**: StatBox (Django Application)

## Quick Start (3 Steps)

### Step 1: Push Code to GitHub (Local Machine)

```bash
cd /Users/pooryaselkghafari/Desktop/GRA
git add .
git commit -m "Deploy to Digital Ocean"
git push origin main
```

### Step 2: Connect to Server

```bash
ssh root@147.182.153.228
# Or if you have a non-root user:
# ssh deploy@147.182.153.228
```

### Step 3: Deploy on Server

```bash
# Clone repository
cd ~
git clone https://github.com/pooryaselkghafari/GRA2.git statbox
cd statbox

# Configure environment
cp env.example .env
nano .env  # Edit with your settings (see below)

# Deploy
chmod +x deploy.sh
./deploy.sh
```

## Required .env Settings

Edit `.env` file with these minimum settings:

```bash
SECRET_KEY=<generate-with-command-below>
DEBUG=False
ALLOWED_HOSTS=147.182.153.228,your-domain.com

DB_NAME=statbox
DB_USER=postgres
DB_PASSWORD=<strong-password>

# Email (Resend recommended)
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<your-resend-api-key>
DEFAULT_FROM_EMAIL=noreply@your-domain.com
```

**Generate SECRET_KEY**:
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## Access Your Application

After deployment:
- **Application**: http://147.182.153.228
- **Admin Panel**: http://147.182.153.228/whereadmingoeshere
- **Default Login**: admin / admin123 (⚠️ CHANGE IMMEDIATELY!)

## Common Commands

```bash
# View logs
docker-compose logs -f web

# Restart services
docker-compose restart

# Update application
git pull
docker-compose down
docker-compose build
docker-compose up -d
docker-compose exec web python manage.py migrate
```

## Full Documentation

- **Quick Guide**: `DEPLOY_TO_DIGITALOCEAN.md`
- **Complete Guide**: `DIGITALOCEAN_DEPLOYMENT.md`
- **Command Reference**: `DEPLOYMENT_QUICK_REFERENCE.md`

## Need Help?

1. Check logs: `docker-compose logs web`
2. Check containers: `docker-compose ps`
3. Check firewall: `ufw status`
4. See troubleshooting in `DIGITALOCEAN_DEPLOYMENT.md`
