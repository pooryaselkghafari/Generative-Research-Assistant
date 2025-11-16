"""
Coverage tests for exception paths and error handling.
"""
from django.test import Client
from django.contrib.auth.models import User
from django.http import JsonResponse
from engine.models import Dataset, AnalysisSession, UserProfile
from engine.views.analysis import run_analysis, add_model_errors_to_dataset
from engine.views.datasets import upload_dataset, get_dataset_variables
from tests.base import BaseTestSuite
import json


class CoverageExceptionsTestSuite(BaseTestSuite):
    category = 'coverage'
    test_name = 'Coverage - Exception Paths'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user('excuser', 'exc@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        self.client.login(username='excuser', password='pass123')
    
    def test_run_analysis_no_dataset_id(self):
        """Test run_analysis with missing dataset_id."""
        response = self.client.post('/run/', {
            'action': 'new',
            'formula': 'y ~ x',
            'module': 'regression'
        })
        self.record_test(
            'run_analysis_no_dataset_id',
            response.status_code == 400,
            f"Should return 400 when dataset_id is missing (got {response.status_code})"
        )
    
    def test_run_analysis_invalid_dataset(self):
        """Test run_analysis with invalid dataset_id."""
        response = self.client.post('/run/', {
            'action': 'new',
            'dataset_id': 99999,
            'formula': 'y ~ x',
            'module': 'regression'
        })
        self.record_test(
            'run_analysis_invalid_dataset',
            response.status_code in [404, 403],
            f"Should return 404/403 for invalid dataset (got {response.status_code})"
        )
    
    def test_run_analysis_get_method(self):
        """Test run_analysis with GET method (should fail)."""
        response = self.client.get('/run/')
        self.record_test(
            'run_analysis_get_method',
            response.status_code == 405,
            f"Should return 405 for GET method (got {response.status_code})"
        )
    
    def test_run_analysis_unauthenticated(self):
        """Test run_analysis without authentication."""
        self.client.logout()
        response = self.client.post('/run/', {
            'dataset_id': 1,
            'formula': 'y ~ x'
        })
        self.record_test(
            'run_analysis_unauthenticated',
            response.status_code in [401, 302],  # 302 for redirect to login
            f"Should require authentication (got {response.status_code})"
        )
    
    def test_get_dataset_variables_invalid_id(self):
        """Test get_dataset_variables with invalid dataset_id."""
        response = self.client.get('/api/dataset/invalid_id/variables/')
        self.record_test(
            'get_dataset_variables_invalid_id',
            response.status_code in [400, 404],
            f"Should return 400/404 for invalid ID (got {response.status_code})"
        )
    
    def test_get_dataset_variables_unauthenticated(self):
        """Test get_dataset_variables without authentication."""
        self.client.logout()
        response = self.client.get('/api/dataset/1/variables/')
        self.record_test(
            'get_dataset_variables_unauthenticated',
            response.status_code == 401,
            f"Should return 401 for unauthenticated request (got {response.status_code})"
        )
    
    def test_add_model_errors_no_session(self):
        """Test add_model_errors_to_dataset with invalid session_id."""
        response = self.client.post(
            '/session/99999/add-model-errors/',
            json.dumps({'dataset_id': 1}),
            content_type='application/json'
        )
        self.record_test(
            'add_model_errors_no_session',
            response.status_code in [404, 403],
            f"Should return 404/403 for invalid session (got {response.status_code})"
        )
    
    def test_add_model_errors_no_dataset_id(self):
        """Test add_model_errors_to_dataset without dataset_id."""
        session = AnalysisSession.objects.create(
            user=self.user,
            name='Test Session',
            formula='y ~ x',
            options={}
        )
        response = self.client.post(
            f'/session/{session.id}/add-model-errors/',
            json.dumps({}),
            content_type='application/json'
        )
        self.record_test(
            'add_model_errors_no_dataset_id',
            response.status_code == 400,
            f"Should return 400 when dataset_id is missing (got {response.status_code})"
        )
    
    def test_add_model_errors_invalid_json(self):
        """Test add_model_errors_to_dataset with invalid JSON."""
        session = AnalysisSession.objects.create(
            user=self.user,
            name='Test Session',
            formula='y ~ x',
            options={}
        )
        response = self.client.post(
            f'/session/{session.id}/add-model-errors/',
            'invalid json',
            content_type='application/json'
        )
        self.record_test(
            'add_model_errors_invalid_json',
            response.status_code == 400,
            f"Should return 400 for invalid JSON (got {response.status_code})"
        )
    
    def test_add_model_errors_get_method(self):
        """Test add_model_errors_to_dataset with GET method."""
        session = AnalysisSession.objects.create(
            user=self.user,
            name='Test Session',
            formula='y ~ x',
            options={}
        )
        response = self.client.get(f'/session/{session.id}/add-model-errors/')
        self.record_test(
            'add_model_errors_get_method',
            response.status_code == 405,
            f"Should return 405 for GET method (got {response.status_code})"
        )
    
    def test_upload_dataset_no_file(self):
        """Test upload_dataset without file."""
        response = self.client.post('/datasets/upload/', {
            'dataset_name': 'Test Dataset'
        })
        self.record_test(
            'upload_dataset_no_file',
            response.status_code == 400,
            f"Should return 400 when no file provided (got {response.status_code})"
        )
    
    def test_upload_dataset_get_method(self):
        """Test upload_dataset with GET method."""
        response = self.client.get('/datasets/upload/')
        self.record_test(
            'upload_dataset_get_method',
            response.status_code in [405, 302],
            f"Should return 405 or redirect for GET method (got {response.status_code})"
        )


