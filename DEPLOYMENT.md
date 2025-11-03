# StatBox Production Deployment Guide

This guide will help you deploy StatBox to a production server with user authentication, subscription management, and admin dashboard.

> **📘 Platform-Specific Guides:**
> - **DigitalOcean Droplet**: See [DIGITALOCEAN_DEPLOYMENT.md](./DIGITALOCEAN_DEPLOYMENT.md) for a complete step-by-step tutorial
> - **Quick Reference**: See [DEPLOYMENT_QUICK_REFERENCE.md](./DEPLOYMENT_QUICK_REFERENCE.md) for common commands

## 🏗️ Architecture Overview

- **Frontend**: Django Templates with modern CSS/JS
- **Backend**: Django 4.2+ with PostgreSQL
- **Authentication**: Django built-in auth with custom user profiles
- **Payments**: Stripe integration for subscriptions
- **Deployment**: Docker + Nginx + Gunicorn
- **Database**: PostgreSQL with Redis for caching
- **Monitoring**: Sentry integration (optional)

## 📋 Prerequisites

- Docker and Docker Compose
- Domain name with SSL certificate
- Stripe account for payments
- SMTP email service (Gmail, SendGrid, etc.)
- Server with at least 2GB RAM and 20GB storage

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo>
cd statbox
cp env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your production settings:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database Settings
DB_NAME=statbox
DB_USER=postgres
DB_PASSWORD=your-secure-password
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
```

### 3. Deploy

```bash
./deploy.sh
```

## 🔧 Detailed Setup

### Database Setup

The application uses PostgreSQL with the following models:
- **Users**: Django User model with custom profiles
- **UserProfile**: Subscription and limits management
- **Datasets**: User-specific datasets with file size limits
- **AnalysisSessions**: User-specific analysis sessions
- **SubscriptionPlans**: Available subscription tiers
- **Payments**: Stripe payment tracking

### User Authentication

- **Registration**: Users can create accounts with username/password
- **Login/Logout**: Standard Django authentication
- **Profile Management**: Users can view their subscription and limits
- **Password Reset**: Email-based password reset (configure SMTP)

### Subscription Management

#### Subscription Tiers

1. **Free Tier**
   - 5 datasets
   - 10 analysis sessions
   - 10MB max file size

2. **Basic Tier** ($9.99/month)
   - 25 datasets
   - 100 analysis sessions
   - 50MB max file size

3. **Pro Tier** ($29.99/month)
   - 100 datasets
   - 500 analysis sessions
   - 200MB max file size

4. **Enterprise Tier** ($99.99/month)
   - Unlimited datasets
   - Unlimited sessions
   - 1GB max file size

#### Stripe Integration

- **Checkout**: Secure payment processing
- **Webhooks**: Automatic subscription updates
- **Billing**: Monthly/yearly billing cycles
- **Cancellation**: Graceful subscription cancellation

### Admin Dashboard

Access at `/admin/` with features:
- **User Management**: View all users and their subscriptions
- **Dataset Management**: Monitor user datasets and usage
- **Session Management**: Track analysis sessions
- **Payment Tracking**: View all payments and transactions
- **Subscription Plans**: Manage available plans and pricing

## 🔒 Security Features

- **HTTPS Enforcement**: Automatic HTTP to HTTPS redirect
- **Security Headers**: XSS protection, content type sniffing prevention
- **CSRF Protection**: Django CSRF tokens on all forms
- **Rate Limiting**: API rate limiting (configurable)
- **Input Validation**: Comprehensive input sanitization
- **File Upload Security**: File type and size validation

## 📊 Monitoring and Logging

### Sentry Integration (Optional)

Add to your `.env`:
```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Health Checks

- **Application Health**: `/health/` endpoint
- **Database Health**: Automatic connection monitoring
- **Redis Health**: Cache system monitoring

## 🚀 Production Optimizations

### Performance

- **Static Files**: Served by Nginx with caching
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis for session and data caching
- **CDN**: Static assets served via CDN (optional)

### Scalability

- **Horizontal Scaling**: Multiple web containers
- **Load Balancing**: Nginx load balancer
- **Database Scaling**: Read replicas (optional)
- **Background Tasks**: Celery for async processing

## 🔧 Maintenance

### Database Backups

```bash
# Create backup
docker-compose exec db pg_dump -U postgres statbox > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres statbox < backup.sql
```

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate
```

### Logs

```bash
# View application logs
docker-compose logs web

# View database logs
docker-compose logs db

# View nginx logs
docker-compose logs nginx
```

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database credentials in `.env`
   - Ensure database container is running
   - Verify network connectivity

2. **Stripe Webhook Issues**
   - Verify webhook URL: `https://your-domain.com/accounts/webhook/`
   - Check webhook secret in `.env`
   - Monitor webhook logs in Stripe dashboard

3. **Email Not Sending**
   - Verify SMTP credentials
   - Check email service provider settings
   - Test with Django shell

4. **Static Files Not Loading**
   - Run `python manage.py collectstatic`
   - Check Nginx configuration
   - Verify file permissions

### Support

- **Documentation**: Check this file and inline code comments
- **Logs**: Always check application logs first
- **Monitoring**: Use Sentry for error tracking
- **Community**: GitHub issues for bug reports

## 📈 Scaling Considerations

### High Traffic

- **Load Balancer**: Use AWS ALB or similar
- **Multiple Instances**: Scale web containers
- **Database**: Consider read replicas
- **CDN**: Use CloudFlare or AWS CloudFront

### High Storage

- **File Storage**: Move to S3 or similar
- **Database**: Implement data archiving
- **Backups**: Automated daily backups

## 🔐 Security Checklist

- [ ] Change default admin password
- [ ] Configure SSL certificates
- [ ] Set up firewall rules
- [ ] Enable database encryption
- [ ] Configure backup encryption
- [ ] Set up monitoring alerts
- [ ] Regular security updates
- [ ] Penetration testing

## 📞 Support

For deployment support or questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review Django and Docker documentation

---

**Happy Deploying! 🚀**
