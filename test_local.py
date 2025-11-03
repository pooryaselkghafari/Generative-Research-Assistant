#!/usr/bin/env python3
"""
Test script to verify StatBox is working locally
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'statbox.settings')
django.setup()

from django.contrib.auth.models import User
from engine.models import UserProfile, SubscriptionPlan, Dataset, AnalysisSession

def test_database():
    print("🔍 Testing database connections...")
    
    # Test User model
    users = User.objects.all()
    print(f"✅ Users in database: {users.count()}")
    
    # Test UserProfile model
    profiles = UserProfile.objects.all()
    print(f"✅ User profiles: {profiles.count()}")
    
    # Test SubscriptionPlan model
    plans = SubscriptionPlan.objects.all()
    print(f"✅ Subscription plans: {plans.count()}")
    for plan in plans:
        print(f"   - {plan.name}: ${plan.price_monthly}/month")
    
    # Test Dataset model
    datasets = Dataset.objects.all()
    print(f"✅ Datasets: {datasets.count()}")
    
    # Test AnalysisSession model
    sessions = AnalysisSession.objects.all()
    print(f"✅ Analysis sessions: {sessions.count()}")
    
    return True

def test_admin_user():
    print("\n👤 Testing admin user...")
    
    try:
        admin = User.objects.get(username='admin')
        print(f"✅ Admin user exists: {admin.username}")
        print(f"✅ Admin email: {admin.email}")
        print(f"✅ Admin is staff: {admin.is_staff}")
        print(f"✅ Admin is superuser: {admin.is_superuser}")
        
        # Test password
        if admin.check_password('admin123'):
            print("✅ Admin password is correct")
        else:
            print("❌ Admin password is incorrect")
            
        return True
    except User.DoesNotExist:
        print("❌ Admin user not found")
        return False

def test_subscription_plans():
    print("\n💳 Testing subscription plans...")
    
    plans = SubscriptionPlan.objects.all()
    expected_plans = ['Free', 'Basic', 'Pro', 'Enterprise']
    
    for expected in expected_plans:
        try:
            plan = SubscriptionPlan.objects.get(name=expected)
            print(f"✅ {plan.name}: ${plan.price_monthly}/month, {plan.max_datasets} datasets")
        except SubscriptionPlan.DoesNotExist:
            print(f"❌ Plan '{expected}' not found")
            return False
    
    return True

def main():
    print("🚀 StatBox Local Testing")
    print("=" * 50)
    
    try:
        # Test database
        if not test_database():
            print("❌ Database test failed")
            return False
        
        # Test admin user
        if not test_admin_user():
            print("❌ Admin user test failed")
            return False
        
        # Test subscription plans
        if not test_subscription_plans():
            print("❌ Subscription plans test failed")
            return False
        
        print("\n🎉 All tests passed! StatBox is ready for local testing.")
        print("\n📋 Next steps:")
        print("1. Visit http://localhost:8000 to see the application")
        print("2. Login with admin/admin123 to access admin dashboard")
        print("3. Visit http://localhost:8000/admin/ for Django admin")
        print("4. Visit http://localhost:8000/accounts/register/ to create new users")
        print("5. Visit http://localhost:8000/accounts/subscription/ to see subscription plans")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
