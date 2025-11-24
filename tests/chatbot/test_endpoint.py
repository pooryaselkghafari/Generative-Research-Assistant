"""
Tests for chatbot endpoint integration with n8n.

Categories: API Tests, Integration Tests, Security Tests, Performance Tests
"""
import json
import pytest
from unittest.mock import patch, Mock
from django.contrib.auth import get_user_model
from django.urls import reverse
from engine.models import AgentTemplate

User = get_user_model()


@pytest.mark.django_db
class TestChatbotEndpoint:
    """Test chatbot endpoint functionality."""
    
    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    @pytest.fixture
    def active_template(self):
        """Create an active template."""
        return AgentTemplate.objects.create(
            name="Active Chatbot",
            n8n_webhook_url="http://localhost:5678/webhook/chatbot",
            status="active",
            visibility="customer_facing"
        )
    
    @pytest.fixture
    def internal_template(self):
        """Create an internal template."""
        return AgentTemplate.objects.create(
            name="Internal Chatbot",
            n8n_webhook_url="http://localhost:5678/webhook/internal",
            status="active",
            visibility="internal"
        )
    
    @pytest.fixture
    def staff_user(self):
        """Create a staff user."""
        return User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True
        )
    
    def test_chatbot_requires_authentication(self, client):
        """Test that chatbot endpoint requires authentication."""
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({'message': 'Hello'}),
            content_type='application/json'
        )
        assert response.status_code == 302  # Redirect to login
    
    def test_chatbot_requires_message(self, client, user):
        """Test that message field is required."""
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'Message is required' in data['error']
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_chatbot_success(self, mock_call_webhook, client, user, active_template):
        """Test successful chatbot interaction."""
        mock_call_webhook.return_value = {
            'reply': 'Hello! This is a test response.',
            'metadata': {'confidence': 0.95}
        }
        
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello, chatbot!',
                'template_id': active_template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'reply' in data
        assert data['reply'] == 'Hello! This is a test response.'
        assert 'template_used' in data
        mock_call_webhook.assert_called_once()
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_chatbot_with_mode_key(self, mock_call_webhook, client, user, active_template):
        """Test chatbot with mode_key routing."""
        active_template.mode_key = 'test_mode'
        active_template.save()
        
        mock_call_webhook.return_value = {
            'reply': 'Mode-based response',
            'metadata': {}
        }
        
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Test message',
                'mode_key': 'test_mode'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['template_used']['mode_key'] == 'test_mode'
    
    def test_chatbot_no_template_available(self, client, user):
        """Test chatbot when no template is available."""
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({'message': 'Hello'}),
            content_type='application/json'
        )
        assert response.status_code == 404
        data = json.loads(response.content)
        assert 'No active agent template' in data['error']
    
    def test_chatbot_inactive_template(self, client, user):
        """Test chatbot with inactive template."""
        template = AgentTemplate.objects.create(
            name="Inactive",
            n8n_webhook_url="http://localhost:5678/webhook/inactive",
            status="inactive"
        )
        
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello',
                'template_id': template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 404
    
    def test_chatbot_internal_template_regular_user(self, client, user, internal_template):
        """Test that regular users cannot use internal templates."""
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello',
                'template_id': internal_template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 403
        data = json.loads(response.content)
        assert 'permission' in data['error'].lower()
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_chatbot_internal_template_staff(self, mock_call_webhook, client, staff_user, internal_template):
        """Test that staff can use internal templates."""
        mock_call_webhook.return_value = {
            'reply': 'Internal response',
            'metadata': {}
        }
        
        client.force_login(staff_user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello',
                'template_id': internal_template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_chatbot_n8n_timeout(self, mock_call_webhook, client, user, active_template):
        """Test handling of n8n timeout."""
        import requests
        mock_call_webhook.side_effect = requests.exceptions.Timeout("Request timed out")
        
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello',
                'template_id': active_template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'error' in data
    
    def test_chatbot_message_length_validation(self, client, user, active_template):
        """Test message length validation."""
        long_message = 'x' * 10001  # Exceeds 10000 character limit
        
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': long_message,
                'template_id': active_template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'too long' in data['error'].lower()
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_chatbot_invalid_n8n_response(self, mock_call_webhook, client, user, active_template):
        """Test handling of invalid n8n response."""
        # Response missing 'reply' field
        mock_call_webhook.return_value = {
            'metadata': {}
        }
        
        client.force_login(user)
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello',
                'template_id': active_template.id
            }),
            content_type='application/json'
        )
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['success'] is False


@pytest.mark.django_db
class TestChatbotSecurity:
    """Security tests for chatbot endpoint."""
    
    def test_chatbot_sql_injection_prevention(self, client):
        """Test that SQL injection in message is prevented."""
        user = User.objects.create_user(username="user", password="pass")
        template = AgentTemplate.objects.create(
            name="Test",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            status="active"
        )
        
        malicious_message = "'; DROP TABLE engine_agenttemplate; --"
        
        client.force_login(user)
        with patch('engine.services.n8n_service.N8nService.call_webhook') as mock_call:
            mock_call.return_value = {'reply': 'Response'}
            response = client.post(
                reverse('chatbot_endpoint'),
                json.dumps({
                    'message': malicious_message,
                    'template_id': template.id
                }),
                content_type='application/json'
            )
            # Should still work (message is passed to n8n, not used in SQL)
            assert response.status_code == 200
            # Verify template still exists
            assert AgentTemplate.objects.filter(id=template.id).exists()


@pytest.mark.django_db
class TestChatbotPerformance:
    """Performance tests for chatbot endpoint."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="user", password="pass")
    
    @pytest.fixture
    def template(self):
        return AgentTemplate.objects.create(
            name="Test",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            status="active"
        )
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_chatbot_response_time(self, mock_call_webhook, client, user, template):
        """Test that chatbot responds within reasonable time."""
        import time
        mock_call_webhook.return_value = {'reply': 'Response'}
        
        client.force_login(user)
        start_time = time.time()
        response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Test',
                'template_id': template.id
            }),
            content_type='application/json'
        )
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        # Should respond quickly (excluding n8n call time)
        # Actual n8n call is mocked, so this tests Django overhead
        assert elapsed_time < 1.0  # Less than 1 second for Django processing

