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
- [ ] Your code pushed to GitHub (see `GITHUB_SETUP.md` for instructions)
  - **If repository is private**: You'll need to set up SSH keys or use a personal access token (see Step 4.2)

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

#### Option A: Public Repository (Simple)

If your repository is public, you can clone directly:

```bash
# Navigate to home directory
cd ~

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git statbox
cd statbox
```

#### Option B: Private Repository - Using SSH Keys (Recommended)

For private repositories, SSH keys are the most secure and convenient method:

**Step 1: Generate SSH Key on Your Server**

```bash
# Generate a new SSH key
ssh-keygen -t ed25519 -C "deploy@statbox"

# Press Enter to accept default location (~/.ssh/id_ed25519)
# Optionally set a passphrase for extra security, or press Enter for no passphrase

# Start SSH agent
eval "$(ssh-agent -s)"

# Add your SSH key to the agent
ssh-add ~/.ssh/id_ed25519
```

**Step 2: Display Public Key**

```bash
# Display your public key - copy this entire output
cat ~/.ssh/id_ed25519.pub
```

**Step 3: Add SSH Key to GitHub**

1. Go to GitHub: https://github.com/settings/keys
2. Click "New SSH key"
3. Title: `statbox-server` (or any descriptive name)
4. Key: Paste the public key you copied
5. Click "Add SSH key"

**Step 4: Test SSH Connection**

```bash
# Test connection to GitHub
ssh -T git@github.com

# You should see: "Hi USERNAME! You've successfully authenticated..."
# If you see "Permission denied", the SSH key isn't properly added to GitHub
```

**⚠️ Important**: If SSH test fails, verify:
- SSH key was copied correctly (no extra spaces/line breaks)
- Key was added to GitHub account (Settings → SSH and GPG keys)
- You're using the correct GitHub account

**Step 5: Verify Git is Using SSH**

Before cloning, make sure you're using the correct SSH URL format:

```bash
# The URL MUST start with "git@github.com:" NOT "https://github.com/"
# Correct format: git@github.com:USERNAME/REPO.git
# Wrong format: https://github.com/USERNAME/REPO.git (this will ask for password)
```

**Step 6: Clone Repository**

```bash
# Navigate to home directory
cd ~

# Clone using SSH (replace YOUR_USERNAME and YOUR_REPO)
# IMPORTANT: Make sure the URL starts with "git@github.com:"
git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git statbox

# If it still asks for username/password, check:
# 1. Is the URL correct? (should be git@github.com:... not https://...)
# 2. Did SSH test pass? (run ssh -T git@github.com again)
# 3. Check what URL git is trying to use:
#    git clone --verbose git@github.com:YOUR_USERNAME/YOUR_REPO.git statbox

cd statbox
```

**Troubleshooting: If Git Still Asks for Password**

If Git is still asking for username/password after setting up SSH:

```bash
# 1. Check if you're accidentally using HTTPS URL
#    Make sure the clone command uses: git@github.com:... 
#    NOT: https://github.com/...

# 2. Verify SSH is working
ssh -T git@github.com
# Should show: "Hi USERNAME! You've successfully authenticated..."

# 3. Check SSH config (optional - create if needed)
nano ~/.ssh/config
```

Add this to `~/.ssh/config` if it doesn't exist:

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
```

Save and try cloning again.

**4. If you already cloned with HTTPS, change the remote URL:**

```bash
# Check current remote URL
git remote -v

# If it shows https://, change it to SSH:
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git

# Verify change
git remote -v
# Should now show git@github.com:...
```

#### Option C: Private Repository - Using Personal Access Token

If you prefer HTTPS with a token instead of SSH:

**Step 1: Create Personal Access Token on GitHub**

1. Go to GitHub: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: `statbox-deployment`
4. Select scopes: Check `repo` (this gives full repository access)
5. Click "Generate token"
6. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

**Step 2: Clone Using Token**

```bash
# Navigate to home directory
cd ~

# Clone using HTTPS with token (replace YOUR_USERNAME, YOUR_REPO, and YOUR_TOKEN)
git clone https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git statbox
cd statbox
```

**Alternative**: You can also clone without the token in the URL and enter it when prompted:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git statbox
# When prompted:
# Username: YOUR_USERNAME
# Password: YOUR_TOKEN (paste your token here, not your GitHub password)
```

**Note**: For security, you might want to store the token in a password manager or use Git credential helper:

```bash
# Store credentials (one-time setup)
git config --global credential.helper store

# Next time you clone/pull, it will remember your credentials
```

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
# See STRIPE_SETUP.md for detailed instructions on finding these keys
# Test mode keys start with pk_test_/sk_test_ (for development)
# Live mode keys start with pk_live_/sk_live_ (for production)
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
- **For Stripe keys**: See `STRIPE_SETUP.md` for detailed instructions on finding your keys
  - Test mode: Start with `pk_test_` and `sk_test_` (for development)
  - Live mode: Start with `pk_live_` and `sk_live_` (for production)

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

# Check if port 80 is free (should show nothing or only docker processes)
sudo lsof -i :80
# Or: sudo netstat -tulpn | grep :80
# Or: sudo ss -tulpn | grep :80

# If port 80 is in use, stop the service using it (see troubleshooting below)
# Then generate certificates
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Certificates will be saved to:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

**⚠️ Troubleshooting: Port 80 Already in Use**

If you get an error: `Could not bind TCP port 80 because it is already in use`:

**Step 1: Identify what's using port 80**

```bash
# Check what's using port 80
sudo lsof -i :80
# Or use:
sudo netstat -tulpn | grep :80
# Or:
sudo ss -tulpn | grep :80
```

Common culprits:
- Apache (`apache2` service)
- Nginx running directly on host (not in Docker)
- Another Docker container
- Systemd service

**Step 2: Stop the conflicting service**

```bash
# If it's Apache:
sudo systemctl stop apache2
sudo systemctl disable apache2  # Prevent auto-start

# If it's nginx running on host (not Docker):
sudo systemctl stop nginx
sudo systemctl disable nginx

# If it's another Docker container:
docker ps
docker stop <container-id-or-name>

# If you can't identify it, kill the process directly:
# Find the PID from lsof/netstat/ss output, then:
sudo kill <PID>
```

**Step 3: Verify port is free**

```bash
# Should show nothing (port is free)
sudo lsof -i :80
```

**Step 4: Continue with certbot**

```bash
# Now certbot should work
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com
```

**Alternative: Use nginx plugin instead of standalone**

If you keep having issues with port 80, you can use certbot's nginx plugin:

```bash
# Start nginx container first
docker-compose up -d nginx

# Use nginx plugin (certbot modifies nginx config automatically)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

However, this requires nginx to be running and accessible, which may need certificates first (chicken-and-egg problem). The standalone method is usually better for initial setup.

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

**See `STRIPE_SETUP.md` for detailed step-by-step instructions.**

Quick steps:
1. Log into Stripe Dashboard: https://dashboard.stripe.com
2. Go to Developers → Webhooks
3. Add endpoint:
   - URL: `https://your-domain.com/accounts/webhook/`
   - Events to send: Select all payment/subscription events (see STRIPE_SETUP.md for specific events)
4. Copy the webhook signing secret (starts with `whsec_...`)
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
# If using SSH (already configured): Just run git pull
git pull

# If using HTTPS with token and credentials aren't saved:
# git pull https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git

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

### Web Service Not Running

**Problem**: Service "web" is not running or keeps crashing

**Solution**:

1. **Check container status**:
   ```bash
   docker-compose ps
   # See which services are running/stopped
   ```

2. **Check web service logs**:
   ```bash
   # View recent logs
   docker-compose logs web
   
   # Follow logs in real-time
   docker-compose logs -f web
   
   # View last 50 lines
   docker-compose logs --tail=50 web
   ```

3. **Common issues and fixes**:

   **Issue: Missing environment variables**
   ```bash
   # Verify .env file exists and has all required variables
   cat .env
   
   # Check if variables are set correctly
   # Make sure SECRET_KEY, DB_PASSWORD, etc. are set
   ```

   **Issue: Database not ready**
   ```bash
   # Check database is running
   docker-compose ps db
   
   # Wait for database to be ready
   docker-compose up -d db
   sleep 10
   
   # Then start web service
   docker-compose up -d web
   ```

   **Issue: Build errors**
   ```bash
   # Rebuild the web container
   docker-compose build web
   
   # Start it
   docker-compose up -d web
   ```

   **Issue: Import/module errors**
   ```bash
   # Check logs for Python import errors
   docker-compose logs web | grep -i "import\|module\|error"
   
   # Try rebuilding
   docker-compose build --no-cache web
   docker-compose up -d web
   ```

4. **Start services in order**:
   ```bash
   # Start database first
   docker-compose up -d db redis
   
   # Wait for database
   sleep 10
   
   # Start web service
   docker-compose up -d web
   
   # Check status
   docker-compose ps
   ```

5. **If web service still won't start**:
   ```bash
   # Try running web service interactively to see errors
   docker-compose run --rm web python manage.py check
   
   # Or try starting it without detaching to see output
   docker-compose up web
   # (Press Ctrl+C to stop, then fix issues)
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

### Port 80 Already in Use

**Problem**: `Could not bind TCP port 80 because it is already in use` when running certbot or starting Docker containers

**Solution**:

1. **Identify what's using port 80**:
   ```bash
   sudo lsof -i :80
   # Or: sudo netstat -tulpn | grep :80
   # Or: sudo ss -tulpn | grep :80
   ```

2. **Stop the conflicting service**:
   ```bash
   # If Apache:
   sudo systemctl stop apache2
   sudo systemctl disable apache2
   
   # If nginx (running on host, not Docker):
   sudo systemctl stop nginx
   sudo systemctl disable nginx
   
   # If another Docker container:
   docker ps
   docker stop <container-name>
   
   # Kill process directly (use PID from step 1):
   sudo kill <PID>
   ```

3. **Verify port is free**:
   ```bash
   sudo lsof -i :80  # Should show nothing
   ```

4. **Continue with your operation** (certbot or docker-compose)

**For Docker port binding issues**:
```bash
# Check if Docker container is trying to bind to port 80
docker-compose ps

# If nginx container is running and causing conflict:
docker-compose stop nginx

# Then start services one by one:
docker-compose up -d db redis web
# Start nginx later after SSL is set up
```

### Git Authentication Issues (Private Repositories)

**Problem**: `Permission denied` or `Repository not found` when cloning/pulling

1. **For SSH method**:
   ```bash
   # Verify SSH key is added
   cat ~/.ssh/id_ed25519.pub
   
   # Test GitHub connection
   ssh -T git@github.com
   
   # If it fails, check:
   # - SSH key is added to GitHub account
   # - You have access to the repository
   # - Repository URL is correct
   ```

2. **For HTTPS/Token method**:
   ```bash
   # Check if credentials are stored
   cat ~/.git-credentials
   
   # If token isn't working:
   # - Generate a new token in GitHub settings
   # - Make sure token has 'repo' scope
   # - Use token as password (not your GitHub password)
   
   # Update remote URL with new token
   git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git
   ```

3. **Switching from HTTPS to SSH**:
   ```bash
   # Change remote URL to SSH
   git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
   
   # Test
   git pull
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

