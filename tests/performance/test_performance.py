"""
Performance tests for response times and load handling.
"""
from django.test import Client
from django.contrib.auth.models import User
from engine.models import UserProfile
from tests.base import BaseTestSuite
import time


class PerformanceTestSuite(BaseTestSuite):
    category = 'performance'
    test_name = 'Performance Tests'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user('perfuser', 'perf@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        self.client.login(username='perfuser', password='pass123')
    
    def test_page_load_time(self):
        """Test that pages load within acceptable time."""
        endpoints = [
            ('/', 'Landing Page'),
        ]
        
        for endpoint, name in endpoints:
            start = time.time()
            response = self.client.get(endpoint)
            load_time = time.time() - start
            
            self.record_test(
                f'page_load_{endpoint.replace("/", "_")}',
                load_time < 2.0 and response.status_code == 200,
                f"{name} load time: {load_time:.2f}s (target: <2s)",
                {'load_time': load_time, 'status_code': response.status_code}
            )
    
    def test_api_response_time(self):
        """Test that API endpoints respond quickly."""
        from engine.models import Dataset
        
        # Create a test dataset
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        
        start = time.time()
        response = self.client.get(f'/api/dataset/{dataset.id}/variables/')
        response_time = time.time() - start
        
        self.record_test(
            'api_response_time',
            response_time < 0.5,  # API should be fast
            f"API response time: {response_time:.3f}s (target: <0.5s)",
            {'response_time': response_time}
        )
    
    def test_database_query_efficiency(self):
        """Test database queries are efficient."""
        from engine.models import Dataset, AnalysisSession
        from django.db import connection, reset_queries
        
        # Create test data
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        AnalysisSession.objects.create(
            user=self.user,
            dataset=dataset,
            name='Test Session'
        )
        
        reset_queries()
        
        # Fetch with relationships
        sessions = AnalysisSession.objects.filter(user=self.user).select_related('dataset', 'user')
        list(sessions)  # Force evaluation
        
        query_count = len(connection.queries)
        
        self.record_test(
            'database_query_efficiency',
            query_count < 5,
            f"Query count: {query_count} (should be < 5)",
            {'query_count': query_count}
        )

