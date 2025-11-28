"""
Coverage tests for AI chat and other API endpoints.
"""
from django.test import Client
from django.contrib.auth.models import User
from django.http import JsonResponse
from engine.models import UserProfile
from engine.views.analysis import ai_chat
from tests.base import BaseTestSuite
import json


class CoverageAIChatTestSuite(BaseTestSuite):
    category = 'coverage'
    test_name = 'Coverage - AI Chat & API'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user('aichatuser', 'aichat@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        self.client.login(username='aichatuser', password='pass123')
    
    def test_ai_chat_valid_request(self):
        """Test ai_chat with valid JSON request."""
        response = self.client.post(
            '/api/ai-chat/',
            json.dumps({'message': 'Hello'}),
            content_type='application/json'
        )
        self.record_test(
            'ai_chat_valid_request',
            response.status_code == 200,
            f"Should return 200 for valid request (got {response.status_code})"
        )
    
    def test_ai_chat_no_message(self):
        """Test ai_chat without message."""
        response = self.client.post(
            '/api/ai-chat/',
            json.dumps({}),
            content_type='application/json'
        )
        self.record_test(
            'ai_chat_no_message',
            response.status_code == 400,
            f"Should return 400 when message missing (got {response.status_code})"
        )
    
    def test_ai_chat_invalid_json(self):
        """Test ai_chat with invalid JSON."""
        response = self.client.post(
            '/api/ai-chat/',
            'invalid json',
            content_type='application/json'
        )
        self.record_test(
            'ai_chat_invalid_json',
            response.status_code == 400,
            f"Should return 400 for invalid JSON (got {response.status_code})"
        )
    
    def test_ai_chat_unauthenticated(self):
        """Test ai_chat without authentication."""
        self.client.logout()
        response = self.client.post(
            '/api/ai-chat/',
            json.dumps({'message': 'Hello'}),
            content_type='application/json'
        )
        self.record_test(
            'ai_chat_unauthenticated',
            response.status_code == 401,
            f"Should return 401 for unauthenticated request (got {response.status_code})"
        )
    
    def test_ai_chat_with_context(self):
        """Test ai_chat with context."""
        response = self.client.post(
            '/api/ai-chat/',
            json.dumps({
                'message': 'Hello',
                'context': 'Some context'
            }),
            content_type='application/json'
        )
        self.record_test(
            'ai_chat_with_context',
            response.status_code == 200,
            f"Should handle context parameter (got {response.status_code})"
        )



