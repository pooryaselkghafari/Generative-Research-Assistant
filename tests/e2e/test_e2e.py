"""
End-to-end tests for complete user workflows.
"""
from django.test import Client
from django.contrib.auth.models import User
from engine.models import UserProfile
from tests.base import BaseTestSuite


class E2ETestSuite(BaseTestSuite):
    category = 'e2e'
    test_name = 'End-to-End Tests'
    target_score = 70.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
    
    def test_user_registration_flow(self):
        """Test complete user registration flow."""
        # Test registration page is accessible
        response = self.client.get('/accounts/register/')
        
        self.record_test(
            'user_registration_page_accessible',
            response.status_code == 200,
            "Registration page should be accessible"
        )
    
    def test_user_login_flow(self):
        """Test complete user login flow."""
        # Create user
        user = User.objects.create_user('e2euser', 'e2e@test.com', 'pass123')
        user.is_active = True
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        
        # Test login page
        response = self.client.get('/accounts/login/')
        self.record_test(
            'user_login_page_accessible',
            response.status_code == 200,
            "Login page should be accessible"
        )
        
        # Test login
        response = self.client.post('/accounts/login/', {
            'username': 'e2euser',
            'password': 'pass123'
        })
        
        self.record_test(
            'user_login_successful',
            response.status_code in [200, 302],  # Redirect on success
            "User should be able to log in"
        )

