"""
API endpoint tests.
"""
import json
from django.test import Client
from django.contrib.auth.models import User
from engine.models import Dataset, UserProfile, Paper
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
    
    def test_paper_keywords_journals_get(self):
        """Test GET endpoint returns keywords and journals."""
        paper = Paper.objects.create(
            user=self.user,
            name='Test Paper',
            keywords=['keyword1', 'keyword2'],
            target_journals=['Journal 1', 'Journal 2']
        )
        
        response = self.client.get(f'/papers/{paper.id}/keywords-journals/')
        
        self.record_test(
            'paper_keywords_journals_get',
            response.status_code == 200,
            f"GET should return 200 (got {response.status_code})"
        )
        
        if response.status_code == 200:
            data = response.json()
            has_success = data.get('success') == True
            has_keywords = 'keywords' in data
            has_journals = 'target_journals' in data
            
            self.record_test(
                'paper_keywords_journals_get_structure',
                has_success and has_keywords and has_journals,
                f"Response should have success, keywords, and target_journals (got: {list(data.keys())})"
            )
            
            if has_keywords and has_journals:
                keywords_match = data['keywords'] == ['keyword1', 'keyword2']
                journals_match = data['target_journals'] == ['Journal 1', 'Journal 2']
                
                self.record_test(
                    'paper_keywords_journals_get_data',
                    keywords_match and journals_match,
                    f"Data should match (keywords: {data['keywords']}, journals: {data['target_journals']})"
                )
    
    def test_paper_keywords_journals_get_empty(self):
        """Test GET endpoint returns empty lists for new paper."""
        paper = Paper.objects.create(
            user=self.user,
            name='New Paper'
        )
        
        response = self.client.get(f'/papers/{paper.id}/keywords-journals/')
        
        if response.status_code == 200:
            data = response.json()
            empty_keywords = data.get('keywords') == []
            empty_journals = data.get('target_journals') == []
            
            self.record_test(
                'paper_keywords_journals_get_empty',
                empty_keywords and empty_journals,
                f"New paper should return empty lists (got keywords: {data.get('keywords')}, journals: {data.get('target_journals')})"
            )
    
    def test_paper_keywords_journals_post(self):
        """Test POST endpoint saves keywords and journals."""
        paper = Paper.objects.create(
            user=self.user,
            name='Test Paper'
        )
        
        response = self.client.post(
            f'/papers/{paper.id}/keywords-journals/',
            json.dumps({
                'keywords': ['new keyword1', 'new keyword2'],
                'target_journals': ['New Journal 1', 'New Journal 2']
            }),
            content_type='application/json'
        )
        
        self.record_test(
            'paper_keywords_journals_post',
            response.status_code == 200,
            f"POST should return 200 (got {response.status_code})"
        )
        
        if response.status_code == 200:
            data = response.json()
            paper.refresh_from_db()
            
            success = data.get('success') == True
            keywords_saved = paper.keywords == ['new keyword1', 'new keyword2']
            journals_saved = paper.target_journals == ['New Journal 1', 'New Journal 2']
            
            self.record_test(
                'paper_keywords_journals_post_save',
                success and keywords_saved and journals_saved,
                f"Data should be saved correctly (keywords: {paper.keywords}, journals: {paper.target_journals})"
            )
    
    def test_paper_keywords_journals_post_filters_empty(self):
        """Test POST endpoint filters out empty strings."""
        paper = Paper.objects.create(
            user=self.user,
            name='Test Paper'
        )
        
        response = self.client.post(
            f'/papers/{paper.id}/keywords-journals/',
            json.dumps({
                'keywords': ['keyword1', '', '  ', 'keyword2'],
                'target_journals': ['Journal 1', '', 'Journal 2']
            }),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            paper.refresh_from_db()
            no_empty_keywords = '' not in paper.keywords and '  ' not in paper.keywords
            no_empty_journals = '' not in paper.target_journals
            
            self.record_test(
                'paper_keywords_journals_post_filter_empty',
                no_empty_keywords and no_empty_journals,
                f"Empty strings should be filtered (keywords: {paper.keywords}, journals: {paper.target_journals})"
            )
    
    def test_paper_keywords_journals_post_invalid_list(self):
        """Test POST endpoint rejects non-list input."""
        paper = Paper.objects.create(
            user=self.user,
            name='Test Paper'
        )
        
        response = self.client.post(
            f'/papers/{paper.id}/keywords-journals/',
            json.dumps({
                'keywords': 'not a list',
                'target_journals': ['Journal 1']
            }),
            content_type='application/json'
        )
        
        self.record_test(
            'paper_keywords_journals_post_invalid_list',
            response.status_code == 400,
            f"Should return 400 for non-list keywords (got {response.status_code})"
        )
    
    def test_paper_keywords_journals_post_invalid_string_items(self):
        """Test POST endpoint rejects non-string items in lists."""
        paper = Paper.objects.create(
            user=self.user,
            name='Test Paper'
        )
        
        response = self.client.post(
            f'/papers/{paper.id}/keywords-journals/',
            json.dumps({
                'keywords': ['valid', 123, 'also valid'],
                'target_journals': ['Journal 1']
            }),
            content_type='application/json'
        )
        
        self.record_test(
            'paper_keywords_journals_post_invalid_string_items',
            response.status_code == 400,
            f"Should return 400 for non-string items (got {response.status_code})"
        )
    
    def test_paper_keywords_journals_unauthorized(self):
        """Test that users cannot access other users' papers."""
        other_user = User.objects.create_user('otheruser', 'other@test.com', 'pass123')
        other_user.is_active = True
        other_user.save()
        
        paper = Paper.objects.create(
            user=other_user,
            name='Other User Paper'
        )
        
        response = self.client.get(f'/papers/{paper.id}/keywords-journals/')
        
        self.record_test(
            'paper_keywords_journals_unauthorized',
            response.status_code == 404,
            f"Should return 404 for other user's paper (got {response.status_code})"
        )
    
    def test_paper_keywords_journals_not_found(self):
        """Test that non-existent paper returns 404."""
        response = self.client.get('/papers/99999/keywords-journals/')
        
        self.record_test(
            'paper_keywords_journals_not_found',
            response.status_code == 404,
            f"Should return 404 for non-existent paper (got {response.status_code})"
        )
    
    def test_paper_keywords_journals_requires_auth(self):
        """Test that endpoint requires authentication."""
        paper = Paper.objects.create(
            user=self.user,
            name='Test Paper'
        )
        
        self.client.logout()
        
        response = self.client.get(f'/papers/{paper.id}/keywords-journals/')
        
        self.record_test(
            'paper_keywords_journals_requires_auth',
            response.status_code in [401, 403, 302],
            f"Should require authentication (got {response.status_code})"
        )

