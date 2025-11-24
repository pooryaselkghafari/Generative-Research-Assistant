"""
Integration tests for agent template system.

Categories: Integration Tests, E2E Tests
"""
import pytest
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from engine.models import AgentTemplate
from engine.services.n8n_service import N8nService

User = get_user_model()


@pytest.mark.django_db
class TestAgentTemplateIntegration:
    """Integration tests for the full agent template flow."""
    
    @pytest.fixture
    def admin_user(self):
        return User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            is_staff=True
        )
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123"
        )
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_full_flow_create_template_and_use(self, mock_call_webhook, client, admin_user, user):
        """Test full flow: create template, then use it via chatbot."""
        mock_call_webhook.return_value = {
            'reply': 'Integration test response',
            'metadata': {}
        }
        
        # Step 1: Admin creates template
        client.force_login(admin_user)
        create_response = client.post(reverse('agent_template_create'), {
            'name': 'Integration Test Template',
            'description': 'Test template',
            'n8n_webhook_url': 'http://localhost:5678/webhook/integration',
            'status': 'active',
            'visibility': 'customer_facing',
            'mode_key': 'integration_test',
            'default_parameters': '{"test": true}'
        })
        assert create_response.status_code == 302
        
        template = AgentTemplate.objects.get(name='Integration Test Template')
        assert template.status == 'active'
        assert template.mode_key == 'integration_test'
        
        # Step 2: User uses chatbot with this template
        client.force_login(user)
        chat_response = client.post(
            reverse('chatbot_endpoint'),
            json.dumps({
                'message': 'Hello from integration test',
                'mode_key': 'integration_test'
            }),
            content_type='application/json'
        )
        assert chat_response.status_code == 200
        data = json.loads(chat_response.content)
        assert data['success'] is True
        assert data['reply'] == 'Integration test response'
        assert data['template_used']['mode_key'] == 'integration_test'
        
        # Verify n8n was called with correct payload
        mock_call_webhook.assert_called_once()
        call_args = mock_call_webhook.call_args
        assert call_args[0][0] == 'http://localhost:5678/webhook/integration'
        payload = call_args[0][1]
        assert payload['message'] == 'Hello from integration test'
        assert payload['mode_key'] == 'integration_test'
        assert payload['test'] is True  # From default_parameters
    
    def test_template_lifecycle(self, client, admin_user):
        """Test template lifecycle: create -> activate -> deactivate -> delete."""
        client.force_login(admin_user)
        
        # Create draft template
        create_response = client.post(reverse('agent_template_create'), {
            'name': 'Lifecycle Test',
            'n8n_webhook_url': 'http://localhost:5678/webhook/lifecycle',
            'status': 'draft',
            'visibility': 'customer_facing',
            'default_parameters': '{}'
        })
        assert create_response.status_code == 302
        
        template = AgentTemplate.objects.get(name='Lifecycle Test')
        assert template.status == 'draft'
        assert not template.is_usable()
        
        # Activate template
        template.status = 'active'
        template.save()
        assert template.is_usable()
        
        # Deactivate template
        toggle_response = client.post(reverse('agent_template_toggle_status', args=[template.id]))
        assert toggle_response.status_code == 302
        template.refresh_from_db()
        assert template.status == 'inactive'
        assert not template.is_usable()
        
        # Reactivate
        toggle_response = client.post(reverse('agent_template_toggle_status', args=[template.id]))
        template.refresh_from_db()
        assert template.status == 'active'

