# StatBox Deployment Quick Reference

## 🚀 Initial Deployment

```bash
# On your local machine - prepare files
# Then on server:

# 1. Connect to server
ssh deploy@YOUR_IP_ADDRESS

# 2. Clone repository
cd ~
git clone <your-repo-url> statbox
cd statbox

# 3. Configure environment
cp env.example .env
nano .env  # Edit with your values

# 4. Update nginx.conf with your domain
nano nginx.conf

# 5. Deploy
chmod +x deploy.sh
./deploy.sh
```

## 🔄 Common Commands

### Container Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart web
docker-compose restart nginx

# View logs
docker-compose logs -f web
docker-compose logs -f nginx
docker-compose logs -f db

# Check status
docker-compose ps
```

### Database Operations

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access database shell
docker-compose exec db psql -U postgres -d statbox

# Backup database
docker-compose exec -T db pg_dump -U postgres statbox > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres statbox < backup.sql
```

### Django Management

```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Django shell
docker-compose exec web python manage.py shell

# Change password
docker-compose exec web python manage.py changepassword admin

# Show migrations
docker-compose exec web python manage.py showmigrations
```

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static
docker-compose exec web python manage.py collectstatic --noinput
```

### SSL Certificates

```bash
# Check certificates
sudo certbot certificates

# Renew certificates
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run

# Restart nginx after renewal
docker-compose restart nginx
```

### Monitoring

```bash
# View resource usage
htop

# Check disk space
df -h

# Check memory
free -h

# View Docker resource usage
docker stats
```

### Cleanup

```bash
# Remove unused Docker resources
docker system prune -a

# Remove unused volumes
docker volume prune

# View disk usage by Docker
docker system df
```

## 🔐 Important Files

- `.env` - Environment variables (keep secret!)
- `nginx.conf` - Web server configuration
- `docker-compose.yml` - Service configuration
- `requirements-prod.txt` - Python dependencies

## 🌐 URLs

- Application: `https://your-domain.com`
- Admin Panel: `https://your-domain.com/admin`
- Health Check: `https://your-domain.com/health/`

## 📝 Environment Variables Checklist

- [ ] `SECRET_KEY` - Django secret key
- [ ] `DEBUG=False` - Production mode
- [ ] `ALLOWED_HOSTS` - Your domain/IP
- [ ] `DB_PASSWORD` - Strong database password
- [ ] `STRIPE_PUBLIC_KEY` - Stripe public key
- [ ] `STRIPE_SECRET_KEY` - Stripe secret key
- [ ] `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret
- [ ] `EMAIL_HOST_USER` - SMTP username
- [ ] `EMAIL_HOST_PASSWORD` - SMTP password

## 🆘 Quick Troubleshooting

### Can't access application
```bash
# Check containers are running
docker-compose ps

# Check firewall
sudo ufw status

# Check logs
docker-compose logs web
docker-compose logs nginx
```

### Database errors
```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db psql -U postgres -d statbox
```

### SSL errors
```bash
# Check certificate status
sudo certbot certificates

# Renew if needed
sudo certbot renew
docker-compose restart nginx
```

### Out of memory
```bash
# Check memory usage
free -h

# Restart containers
docker-compose restart

# Consider upgrading droplet
```

## 💾 Backup Script

Save this as `~/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

cd ~/statbox

# Backup database
docker-compose exec -T db pg_dump -U postgres statbox > $BACKUP_DIR/db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make executable: `chmod +x ~/backup.sh`

## 📅 Automated Tasks (Crontab)

Edit crontab: `crontab -e`

```bash
# Daily backup at 2 AM
0 2 * * * /home/deploy/backup.sh

# SSL renewal check (twice daily)
0 0,12 * * * certbot renew --quiet && cd /home/deploy/statbox && docker-compose restart nginx
```

## 🔗 Useful Links

- DigitalOcean Dashboard: https://cloud.digitalocean.com
- Stripe Dashboard: https://dashboard.stripe.com
- Let's Encrypt: https://letsencrypt.org
- Docker Docs: https://docs.docker.com
- Django Docs: https://docs.djangoproject.com

