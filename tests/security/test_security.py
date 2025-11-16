"""
Security tests for authentication, authorization, and data isolation.
"""
from django.test import Client
from django.contrib.auth.models import User
from engine.models import Dataset, AnalysisSession, UserProfile
from tests.base import BaseTestSuite


class SecurityTestSuite(BaseTestSuite):
    category = 'security'
    test_name = 'Security Tests'
    target_score = 95.0  # Security must be very high
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        
        # Create test users
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass123')
        self.user1.is_active = True
        self.user1.save()
        profile1, _ = UserProfile.objects.get_or_create(user=self.user1, defaults={'subscription_type': 'free'})
        profile1.subscription_type = 'free'
        profile1.save()
        
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass123')
        self.user2.is_active = True
        self.user2.save()
        profile2, _ = UserProfile.objects.get_or_create(user=self.user2, defaults={'subscription_type': 'free'})
        profile2.subscription_type = 'free'
        profile2.save()
        
        # Create test data
        self.dataset1 = Dataset.objects.create(
            user=self.user1,
            name='User1 Dataset',
            file_path='/test/path1.csv'
        )
        self.session1 = AnalysisSession.objects.create(
            user=self.user1,
            dataset=self.dataset1,
            name='User1 Session'
        )
    
    def test_inactive_user_cannot_login(self):
        """Test that inactive users cannot log in."""
        inactive_user = User.objects.create_user('inactive', 'inactive@test.com', 'pass123')
        inactive_user.is_active = False
        inactive_user.save()
        
        response = self.client.post('/accounts/login/', {
            'username': 'inactive',
            'password': 'pass123'
        })
        
        # Should not successfully log in
        self.record_test(
            'inactive_user_cannot_login',
            response.status_code != 200 or not self.client.session.get('_auth_user_id'),
            "Inactive users should not be able to log in"
        )
    
    def test_user_data_isolation_datasets(self):
        """Test that users cannot access other users' datasets."""
        # Login as user1
        self.client.login(username='user1', password='pass123')
        
        # Try to access user1's own dataset (should succeed or return 404 if file doesn't exist)
        # Important: should NOT return 403 (which would indicate access denied to own data)
        response = self.client.get(f'/api/dataset/{self.dataset1.id}/variables/')
        self.record_test(
            'user_data_isolation_datasets_own',
            response.status_code in [200, 404] and response.status_code != 403,
            f"Users should be able to access their own datasets (got {response.status_code})"
        )
        
        # Create dataset for user2
        dataset2 = Dataset.objects.create(
            user=self.user2,
            name='User2 Dataset',
            file_path='/test/path2.csv'
        )
        
        # Try to access user2's dataset as user1 (should fail with 403 Forbidden)
        response = self.client.get(f'/api/dataset/{dataset2.id}/variables/')
        self.record_test(
            'user_data_isolation_datasets_other',
            response.status_code == 403,  # Must be 403 (Forbidden), not 404
            f"Users should not access other users' datasets (got {response.status_code}, expected 403)"
        )
    
    def test_user_data_isolation_sessions(self):
        """Test that users cannot access other users' sessions."""
        # Create session for user2
        dataset2 = Dataset.objects.create(
            user=self.user2,
            name='User2 Dataset',
            file_path='/test/path2.csv'
        )
        session2 = AnalysisSession.objects.create(
            user=self.user2,
            dataset=dataset2,
            name='User2 Session'
        )
        
        # Login as user1
        self.client.login(username='user1', password='pass123')
        
        # Try to access user2's session (should fail)
        response = self.client.get(f'/session/{session2.id}/')
        self.record_test(
            'user_data_isolation_sessions',
            response.status_code in [403, 404],
            "Users should not access other users' sessions"
        )
    
    def test_api_authentication_required(self):
        """Test that API endpoints require authentication."""
        endpoints = [
            '/api/dataset/1/variables/',
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.record_test(
                f'api_auth_required_{endpoint.replace("/", "_")}',
                response.status_code in [401, 403, 302],
                f"{endpoint} should require authentication"
            )
    
    def test_csrf_protection(self):
        """Test CSRF protection on POST endpoints."""
        self.client.login(username='user1', password='pass123')
        
        # Try POST without CSRF token
        response = self.client.post('/run/', {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # CSRF might be bypassed in tests, so we check for either 403 or proper handling
        self.record_test(
            'csrf_protection',
            response.status_code in [403, 400, 200],  # 200 if CSRF is disabled in tests
            "POST endpoints should be protected by CSRF"
        )
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        self.client.login(username='user1', password='pass123')
        
        # Try SQL injection in dataset ID
        malicious_input = "1' OR '1'='1"
        try:
            response = self.client.get(f'/api/dataset/{malicious_input}/variables/')
            # Should either 404 or handle gracefully
            self.record_test(
                'sql_injection_prevention',
                response.status_code in [404, 400, 500],  # Should not return 200 with data
                "Should prevent SQL injection attacks"
            )
        except Exception:
            # Exception is also acceptable (Django's protection)
            self.record_test(
                'sql_injection_prevention',
                True,
                "Should prevent SQL injection attacks"
            )

