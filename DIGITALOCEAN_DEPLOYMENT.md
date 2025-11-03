# DigitalOcean Deployment Guide for StatBox

This comprehensive guide will help you deploy StatBox on a DigitalOcean droplet.

## 💰 Recommended Droplet Configuration

### Budget-Friendly Option (Recommended for Start)
- **Plan**: Regular Intel (Shared CPU)
- **Size**: $12/month
  - 2 GB RAM
  - 1 vCPU
  - 50 GB SSD
  - 3 TB Transfer
- **Why**: Meets the minimum 2GB RAM requirement and provides enough storage for initial deployment

### Optimal Option (For Production with More Users)
- **Plan**: Regular Intel (Shared CPU)
- **Size**: $18/month
  - 4 GB RAM
  - 2 vCPU
  - 80 GB SSD
  - 4 TB Transfer
- **Why**: Better performance, more headroom for concurrent users and processing

### Recommended Operating System
- **Ubuntu 22.04 (LTS)** - Most stable and well-documented

---

## 📋 Prerequisites

Before you begin, make sure you have:
- [ ] A DigitalOcean account (sign up at https://www.digitalocean.com)
- [ ] A domain name (you can use the droplet IP temporarily, but a domain is recommended)
- [ ] SSH access to your computer
- [ ] A Stripe account (for payment processing)
- [ ] An email service (Gmail, SendGrid, etc.) for sending emails

---

## 🚀 Step 1: Create Your Droplet

1. **Log in to DigitalOcean Dashboard**
   - Go to https://cloud.digitalocean.com
   - Sign in or create an account

2. **Create a New Droplet**
   - Click "Create" → "Droplets"
   - Choose an image:
     - Select **Ubuntu 22.04 (LTS)**
   - Choose a plan:
     - Select **Regular with Shared CPU**
     - Choose **$12/month** (2GB RAM) or **$18/month** (4GB RAM)
   - Choose a datacenter region:
     - Select the region closest to your users
   - Authentication:
     - **Recommended**: SSH keys (more secure)
     - **Alternative**: Password (easier setup)
   - Finalize:
     - Give your droplet a hostname (e.g., `statbox-prod`)
     - Click "Create Droplet"

3. **Note Your Server IP**
   - After creation, copy your droplet's IP address (you'll need it)

---

## 🔐 Step 2: Initial Server Setup

### 2.1 Connect to Your Server

```bash
# Replace YOUR_IP_ADDRESS with your droplet's IP
ssh root@YOUR_IP_ADDRESS

# If you used password authentication, you'll be prompted for the root password
```

### 2.2 Update System Packages

```bash
apt update && apt upgrade -y
```

**Note**: During `apt upgrade`, you may see a prompt asking about SSH configuration file conflicts:
- **Recommended**: Choose **"keep the local version currently installed"**
- This is safe because SSH access is critical - you don't want to accidentally break it
- If you want to see what changed, you can choose "show the differences" first
- If you haven't modified SSH config manually, you can also safely keep the local version

### 2.3 Create a Non-Root User (Security Best Practice)

```bash
# Create a new user
adduser deploy
usermod -aG sudo deploy

# Switch to the new user
su - deploy
```

### 2.4 Set Up Firewall

```bash
# Allow OpenSSH (port 22)
sudo ufw allow OpenSSH

# Allow HTTP (port 80) for Let's Encrypt
sudo ufw allow 80

# Allow HTTPS (port 443)
sudo ufw allow 443

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## 🐳 Step 3: Install Docker and Docker Compose

### 3.1 Install Docker

```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
sudo apt update

# Install Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group (so you don't need sudo for docker commands)
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect
exit
```

Reconnect to your server:

```bash
ssh deploy@YOUR_IP_ADDRESS
```

### 3.2 Install Docker Compose

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### 3.3 Verify Docker Installation

```bash
# Test Docker
docker run hello-world
```

---

## 📦 Step 4: Clone and Configure Your Application

### 4.1 Install Git

```bash
sudo apt install -y git
```

### 4.2 Clone Your Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git statbox
cd statbox

# If you're using SSH for git:
# git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git statbox
```

**Note**: If your repository is private, you'll need to set up SSH keys or use a personal access token.

### 4.3 Configure Environment Variables

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your production settings
nano .env
```

Update the `.env` file with your actual values:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-here-generate-a-long-random-string
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,YOUR_IP_ADDRESS

# Database Settings
DB_NAME=statbox
DB_USER=postgres
DB_PASSWORD=your-strong-database-password-here
DB_HOST=db
DB_PORT=5432

# Stripe Settings
STRIPE_PUBLIC_KEY=pk_live_your_stripe_public_key
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Email Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com

# Redis Settings
REDIS_URL=redis://redis:6379/0
```

**Generate SECRET_KEY**:

```bash
# Generate a secure secret key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**Important Notes**:
- Replace `your-domain.com` with your actual domain name
- Generate a strong `SECRET_KEY` (use the command above)
- Create a strong `DB_PASSWORD` (use a password manager)
- For Gmail, you'll need to generate an "App Password" in your Google Account settings
- For Stripe keys, use your production keys (starting with `pk_live_` and `sk_live_`)

Save and exit nano: `Ctrl+X`, then `Y`, then `Enter`

### 4.4 Update Nginx Configuration

```bash
# Edit nginx.conf
nano nginx.conf
```

Update the `server_name` directives (lines 45 and 53) with your domain:

```nginx
server_name your-domain.com www.your-domain.com;
```

If you don't have a domain yet, you can temporarily use your IP address or skip SSL setup for now.

---

## 🌐 Step 5: Configure Your Domain (Optional but Recommended)

### 5.1 DNS Configuration

If you have a domain name:

1. Log into your domain registrar
2. Go to DNS settings
3. Add/Update A records:
   ```
   Type: A
   Name: @
   Value: YOUR_IP_ADDRESS
   TTL: 3600
   
   Type: A
   Name: www
   Value: YOUR_IP_ADDRESS
   TTL: 3600
   ```

4. Wait for DNS propagation (can take a few minutes to 48 hours)
5. Verify DNS: `dig your-domain.com` or use https://www.whatsmydns.net

---

## 🔒 Step 6: Set Up SSL Certificate (Let's Encrypt)

### 6.1 Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 6.2 Temporarily Update Nginx for Certificate Generation

Before generating certificates, we need to modify nginx.conf to not require SSL certificates (since we don't have them yet):

```bash
# Create a temporary nginx config for initial setup
cp nginx.conf nginx.conf.backup
```

Edit `nginx.conf` to comment out the HTTPS redirect temporarily:

```bash
nano nginx.conf
```

Comment out the HTTP to HTTPS redirect block (lines 43-49):

```nginx
#    server {
#        listen 80;
#        server_name your-domain.com www.your-domain.com;
#        
#        # Redirect HTTP to HTTPS
#        return 301 https://$server_name$request_uri;
#    }
```

Update the HTTPS server block to also listen on port 80 initially (we'll update this after getting certificates).

### 6.3 Start Containers (Without SSL First)

```bash
# Start services (nginx will fail without SSL, but that's OK for now)
docker-compose up -d db redis web
```

### 6.4 Get SSL Certificates

**If you have a domain:**

```bash
# Stop nginx temporarily
docker-compose stop nginx

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Certificates will be saved to:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

**If you don't have a domain yet:**
- Skip SSL setup for now
- You can access your app via HTTP at `http://YOUR_IP_ADDRESS`
- Add SSL later when you have a domain

### 6.5 Update Nginx Configuration with SSL

If you got certificates, update the nginx.conf:

```bash
nano nginx.conf
```

Uncomment the HTTP redirect block and update SSL paths. Then create an SSL directory and copy certificates:

```bash
# Create SSL directory
mkdir -p ssl

# Copy certificates (replace your-domain.com with your actual domain)
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem

# Set proper permissions
sudo chown -R $USER:$USER ssl/
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

**Alternative**: If you want to mount the certificates directly, update docker-compose.yml to mount `/etc/letsencrypt`.

### 6.6 Update docker-compose.yml (Optional - Mount SSL Directly)

You can mount Let's Encrypt certificates directly to avoid copying:

```bash
nano docker-compose.yml
```

Add to nginx volumes section:

```yaml
  nginx:
    # ... existing config ...
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - /etc/letsencrypt:/etc/letsencrypt:ro  # Add this line
```

Then update nginx.conf SSL paths:

```nginx
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

---

## 🚀 Step 7: Deploy the Application

### 7.1 Run the Deployment Script

```bash
# Make deploy.sh executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

This script will:
- Build Docker containers
- Start database and Redis
- Run migrations
- Create a superuser
- Collect static files
- Start all services

### 7.2 Manual Deployment (If Script Fails)

If you encounter issues, deploy manually:

```bash
# Build containers
docker-compose build

# Start database and Redis
docker-compose up -d db redis

# Wait for database (10 seconds)
sleep 10

# Run migrations
docker-compose run --rm web python manage.py migrate

# Create superuser (you'll be prompted)
docker-compose run --rm web python manage.py createsuperuser

# Collect static files
docker-compose run --rm web python manage.py collectstatic --noinput

# Start all services
docker-compose up -d
```

### 7.3 Verify Deployment

```bash
# Check running containers
docker-compose ps

# Check logs
docker-compose logs web
docker-compose logs nginx
```

---

## ✅ Step 8: Post-Deployment Configuration

### 8.1 Set Up Auto-Renewal for SSL Certificates

```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab for automatic renewal
sudo crontab -e

# Add this line (checks twice daily and renews if needed):
0 0,12 * * * certbot renew --quiet && docker-compose -f /home/deploy/statbox/docker-compose.yml restart nginx
```

### 8.2 Configure Stripe Webhooks

1. Log into Stripe Dashboard
2. Go to Developers → Webhooks
3. Add endpoint:
   - URL: `https://your-domain.com/accounts/webhook/`
   - Events to send: Select all payment/subscription events
4. Copy the webhook signing secret
5. Update your `.env` file with `STRIPE_WEBHOOK_SECRET`
6. Restart services: `docker-compose restart web`

### 8.3 Change Default Admin Password

```bash
# Access Django shell
docker-compose exec web python manage.py changepassword admin
```

### 8.4 Set Up Automatic Backups (Important!)

Create a backup script:

```bash
nano ~/backup.sh
```

Add this content:

```bash
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T db pg_dump -U postgres statbox > $BACKUP_DIR/db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make it executable and schedule it:

```bash
chmod +x ~/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/deploy/backup.sh
```

### 8.5 Set Up Monitoring (Optional)

You can set up basic monitoring:

```bash
# Install htop for monitoring
sudo apt install -y htop

# Monitor resources
htop
```

Or use DigitalOcean's built-in monitoring (enable in droplet settings).

---

## 🔧 Step 9: Common Operations

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs web
docker-compose logs nginx
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f web
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart web
```

### Update Application

```bash
# Navigate to project directory
cd ~/statbox

# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations if needed
docker-compose exec web python manage.py migrate

# Collect static files
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

---

## 🆘 Troubleshooting

### Application Not Accessible

1. **Check firewall**:
   ```bash
   sudo ufw status
   ```

2. **Check containers**:
   ```bash
   docker-compose ps
   ```

3. **Check logs**:
   ```bash
   docker-compose logs web
   docker-compose logs nginx
   ```

### Database Connection Errors

1. **Check database container**:
   ```bash
   docker-compose ps db
   docker-compose logs db
   ```

2. **Verify database credentials in .env**

3. **Test connection**:
   ```bash
   docker-compose exec db psql -U postgres -d statbox
   ```

### SSL Certificate Issues

1. **Check certificate expiration**:
   ```bash
   sudo certbot certificates
   ```

2. **Renew manually**:
   ```bash
   sudo certbot renew
   docker-compose restart nginx
   ```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a

# Clean up unused volumes
docker volume prune
```

### High Memory Usage

If you're on the $12/month plan and experiencing issues:

1. Monitor memory:
   ```bash
   free -h
   ```

2. Consider upgrading to $18/month (4GB RAM)

3. Optimize Gunicorn workers (edit docker-compose.yml):
   ```yaml
   command: gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 statbox.wsgi:application
   ```

---

## 💰 Cost Breakdown

### Monthly Costs

- **Droplet**: $12/month (or $18/month)
- **Domain**: ~$10-15/year (~$1/month)
- **SSL**: Free (Let's Encrypt)
- **Total**: ~$13-19/month

### Optional Costs

- **Managed Database**: +$15/month (if you want DigitalOcean to manage PostgreSQL)
- **Spaces (File Storage)**: +$5/month for 250GB (if you need more storage)
- **Monitoring**: Free (basic) or +$5/month (advanced)

---

## 📊 Performance Tips

1. **Enable Swap** (if running low on memory):
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

2. **Optimize PostgreSQL** (in docker-compose.yml):
   ```yaml
   environment:
     POSTGRES_SHARED_BUFFERS: 512MB
     POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
   ```

3. **Use a CDN** (Cloudflare free tier) for static assets

4. **Monitor Resources**: Use `htop` or DigitalOcean monitoring

---

## 🔐 Security Checklist

- [ ] Changed default admin password
- [ ] Configured firewall (UFW)
- [ ] Set up SSL certificates
- [ ] Using strong database passwords
- [ ] SECRET_KEY is random and secure
- [ ] DEBUG=False in production
- [ ] Regular backups configured
- [ ] SSL auto-renewal configured
- [ ] Keep system packages updated

---

## 📞 Support Resources

- **DigitalOcean Documentation**: https://docs.digitalocean.com
- **Docker Documentation**: https://docs.docker.com
- **Django Deployment**: https://docs.djangoproject.com/en/stable/howto/deployment/
- **Let's Encrypt**: https://letsencrypt.org/docs/

---

## 🎉 Next Steps

1. Test your application thoroughly
2. Set up monitoring and alerts
3. Configure automated backups
4. Set up a staging environment (optional)
5. Document your deployment process
6. Consider setting up CI/CD for easier deployments

---

**Congratulations! Your StatBox application should now be running on DigitalOcean! 🚀**

Access your application at:
- Production URL: `https://your-domain.com` (or `http://YOUR_IP_ADDRESS`)
- Admin Panel: `https://your-domain.com/admin`

