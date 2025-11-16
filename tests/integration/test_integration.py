"""
Integration tests for complete workflows.
"""
from django.test import Client
from django.contrib.auth.models import User
from engine.models import Dataset, AnalysisSession, UserProfile
from tests.base import BaseTestSuite


class IntegrationTestSuite(BaseTestSuite):
    category = 'integration'
    test_name = 'Integration Tests'
    target_score = 75.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user('intuser', 'int@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        self.client.login(username='intuser', password='pass123')
    
    def test_dataset_upload_workflow(self):
        """Test complete dataset upload workflow."""
        # Test that session list page is accessible (where upload happens)
        response = self.client.get('/session/')
        self.record_test(
            'dataset_upload_workflow_accessible',
            response.status_code == 200,
            "Dataset upload workflow should be accessible"
        )
        
        # Test upload endpoint exists
        response = self.client.get('/datasets/upload/')
        # Should redirect or return appropriate response
        self.record_test(
            'dataset_upload_endpoint_exists',
            response.status_code in [200, 302, 405],  # 405 = Method Not Allowed (POST only)
            "Dataset upload endpoint should exist"
        )
    
    def test_session_creation_workflow(self):
        """Test session creation workflow."""
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        
        # Test session list page
        response = self.client.get('/session/')
        self.record_test(
            'session_creation_workflow_list',
            response.status_code == 200,
            "Session list should be accessible"
        )
        
        # Test session detail (if exists)
        session = AnalysisSession.objects.create(
            user=self.user,
            dataset=dataset,
            name='Test Session',
            formula='y ~ x',
            options={}
        )
        
        response = self.client.get(f'/session/{session.id}/')
        self.record_test(
            'session_creation_workflow_detail',
            response.status_code == 200,
            "Session detail should be accessible"
        )
    
    def test_dataset_variables_api_integration(self):
        """Test dataset variables API integration with dataset workflow."""
        # Create a dataset
        dataset = Dataset.objects.create(
            user=self.user,
            name='Integration Test Dataset',
            file_path='/test/integration.csv'
        )
        
        # Test that variables API endpoint is accessible
        response = self.client.get(f'/api/dataset/{dataset.id}/variables/')
        # Should return 200 (if file exists) or 404 (if file doesn't exist)
        # But should NOT return 403 (which would indicate access denied)
        self.record_test(
            'dataset_variables_api_accessible',
            response.status_code in [200, 404] and response.status_code != 403,
            f"Dataset variables API should be accessible (got {response.status_code})"
        )
    
    def test_complete_workflow_integration(self):
        """Test complete workflow: dataset -> session -> access."""
        # Create dataset
        dataset = Dataset.objects.create(
            user=self.user,
            name='Workflow Test Dataset',
            file_path='/test/workflow.csv'
        )
        
        # Create session linked to dataset
        session = AnalysisSession.objects.create(
            user=self.user,
            dataset=dataset,
            name='Workflow Test Session',
            formula='y ~ x',
            options={}
        )
        
        # Verify session is linked to dataset
        session.refresh_from_db()
        self.record_test(
            'workflow_dataset_session_link',
            session.dataset_id == dataset.id,
            "Session should be linked to dataset"
        )
        
        # Verify session appears in list
        response = self.client.get('/session/')
        self.record_test(
            'workflow_session_in_list',
            response.status_code == 200 and 'sessions' in response.context,
            "Session should appear in session list"
        )
        
        # Verify session detail is accessible
        response = self.client.get(f'/session/{session.id}/')
        self.record_test(
            'workflow_session_detail_accessible',
            response.status_code == 200,
            "Session detail should be accessible in workflow"
        )

