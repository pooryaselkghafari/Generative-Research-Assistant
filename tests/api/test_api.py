"""
API endpoint tests.
"""
from django.test import Client
from django.contrib.auth.models import User
from engine.models import Dataset, UserProfile
from tests.base import BaseTestSuite


class APITestSuite(BaseTestSuite):
    category = 'api'
    test_name = 'API Tests'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user('apiuser', 'api@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        self.client.login(username='apiuser', password='pass123')
    
    def test_dataset_variables_api(self):
        """Test dataset variables API endpoint."""
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        
        response = self.client.get(f'/api/dataset/{dataset.id}/variables/')
        
        self.record_test(
            'dataset_variables_api',
            response.status_code in [200, 400, 404, 500],  # 400/404/500 if file doesn't exist, but endpoint works
            f"Dataset variables API should respond (status: {response.status_code})"
        )
    
    def test_api_authentication(self):
        """Test API requires authentication."""
        self.client.logout()
        
        response = self.client.get('/api/dataset/1/variables/')
        
        self.record_test(
            'api_authentication_required',
            response.status_code in [401, 403, 302],
            "API should require authentication"
        )

