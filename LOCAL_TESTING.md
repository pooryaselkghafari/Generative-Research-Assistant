# StatBox Local Testing Guide

## 🚀 Quick Start

Your StatBox application is now ready for local testing! Here's how to get started:

### 1. **Start the Development Server**
```bash
cd /Users/pooryaselkghafari/Desktop/statbox
python manage.py runserver 0.0.0.0:8000
```

### 2. **Access the Application**
- **Main App**: http://localhost:8000
- **Admin Dashboard**: http://localhost:8000/admin/
- **User Registration**: http://localhost:8000/accounts/register/
- **User Login**: http://localhost:8000/accounts/login/
- **Subscription Plans**: http://localhost:8000/accounts/subscription/

### 3. **Default Admin Account**
- **Username**: `admin`
- **Password**: `admin123`
- **Access**: Full admin privileges

## 🔧 Features Available for Testing

### ✅ **User Authentication**
- User registration and login
- Password reset (requires email configuration)
- User profile management
- Session management

### ✅ **Subscription Management**
- 4 subscription tiers (Free, Basic, Pro, Enterprise)
- Stripe integration (test mode)
- Usage limits enforcement
- Subscription upgrade/downgrade

### ✅ **Admin Dashboard**
- User management and monitoring
- Dataset and session tracking
- Payment and subscription oversight
- System analytics

### ✅ **Statistical Analysis**
- All existing regression models
- Bayesian analysis
- BMA (Bayesian Model Averaging)
- File upload and processing

## 🧪 Testing Scenarios

### **1. User Registration Flow**
1. Go to http://localhost:8000/accounts/register/
2. Create a new user account
3. Verify user profile is created
4. Check subscription defaults to "Free"

### **2. Subscription Management**
1. Login as any user
2. Go to Profile → Subscription
3. View available plans
4. Test plan selection (Stripe test mode)

### **3. Admin Dashboard**
1. Login as admin/admin123
2. Go to http://localhost:8000/admin/
3. Explore user management
4. Check subscription and payment tracking

### **4. Statistical Analysis**
1. Upload a dataset
2. Create analysis sessions
3. Test different regression models
4. Verify user-specific data isolation

## 🔍 Database Information

- **Database**: SQLite (local development)
- **Location**: `db.sqlite3`
- **Admin Access**: Django admin interface
- **Data Persistence**: All data saved locally

## 🛠️ Development Tools

### **Django Admin**
- Access: http://localhost:8000/admin/
- Username: `admin`
- Password: `admin123`
- Features: Full CRUD operations on all models

### **Database Browser**
```bash
# View database contents
python manage.py shell
>>> from engine.models import *
>>> User.objects.all()
>>> SubscriptionPlan.objects.all()
```

### **Run Tests**
```bash
# Run the test script
python test_local.py

# Run Django tests
python manage.py test
```

## 🚨 Important Notes

### **Stripe Integration**
- Currently in test mode
- Use test card numbers for payments
- Webhook testing requires ngrok or similar

### **Email Configuration**
- Password reset requires SMTP setup
- Add email settings to `.env` for full functionality

### **File Uploads**
- Files stored in `media/` directory
- Size limits based on subscription tier
- User-specific file isolation

## 🔄 Reset Database

If you need to reset the database:

```bash
# Delete database
rm db.sqlite3

# Recreate migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run setup script
python manage.py shell -c "
from django.contrib.auth.models import User
from engine.models import UserProfile, SubscriptionPlan
# ... (run the setup commands from earlier)
"
```

## 📊 Monitoring

### **Check Application Status**
```bash
# View server logs
python manage.py runserver --verbosity=2

# Check database
python manage.py dbshell
```

### **User Activity**
- Admin dashboard shows user statistics
- Session tracking in Django admin
- File upload monitoring

## 🎯 Next Steps for Production

1. **Configure Environment Variables**
   - Copy `env.example` to `.env`
   - Set production database credentials
   - Configure Stripe live keys

2. **Set Up PostgreSQL**
   - Install PostgreSQL
   - Create production database
   - Update settings for production

3. **Configure Email**
   - Set up SMTP service
   - Configure email templates
   - Test password reset flow

4. **Deploy with Docker**
   - Use `docker-compose.yml`
   - Configure nginx
   - Set up SSL certificates

## 🆘 Troubleshooting

### **Common Issues**

1. **Port Already in Use**
   ```bash
   # Use different port
   python manage.py runserver 8001
   ```

2. **Database Errors**
   ```bash
   # Reset migrations
   rm -rf engine/migrations/__pycache__
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Static Files Not Loading**
   ```bash
   # Collect static files
   python manage.py collectstatic
   ```

4. **Import Errors**
   ```bash
   # Install requirements
   pip install -r requirements-dev.txt
   ```

### **Get Help**
- Check Django logs in terminal
- Use `python manage.py shell` for debugging
- Review `test_local.py` for verification

---

**Happy Testing! 🎉**

Your StatBox application is now fully functional with user authentication, subscription management, and admin dashboard. Test all features locally before deploying to production.
