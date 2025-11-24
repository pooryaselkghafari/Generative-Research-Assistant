"""
API and Integration tests for Agent Template views.

Categories: API Tests, Integration Tests, Security Tests
"""
import json
import pytest
from unittest.mock import patch, Mock
from django.contrib.auth import get_user_model
from django.urls import reverse
from engine.models import AgentTemplate

User = get_user_model()


@pytest.mark.django_db
class TestAgentTemplateViews:
    """Test agent template admin views."""
    
    @pytest.fixture
    def admin_user(self):
        """Create an admin user for testing."""
        return User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True
        )
    
    @pytest.fixture
    def regular_user(self):
        """Create a regular user for testing."""
        return User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123"
        )
    
    @pytest.fixture
    def template(self):
        """Create a test template."""
        return AgentTemplate.objects.create(
            name="Test Template",
            description="Test description",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            status="active",
            visibility="customer_facing"
        )
    
    def test_list_view_requires_staff(self, client, regular_user):
        """Test that list view requires staff access."""
        client.force_login(regular_user)
        response = client.get(reverse('agent_template_list'))
        assert response.status_code == 403  # Forbidden
    
    def test_list_view_allows_staff(self, client, admin_user):
        """Test that staff can access list view."""
        client.force_login(admin_user)
        response = client.get(reverse('agent_template_list'))
        assert response.status_code == 200
    
    def test_create_template(self, client, admin_user):
        """Test creating a new template."""
        client.force_login(admin_user)
        response = client.post(reverse('agent_template_create'), {
            'name': 'New Template',
            'description': 'New description',
            'n8n_webhook_url': 'http://localhost:5678/webhook/new',
            'status': 'active',
            'visibility': 'customer_facing',
            'default_parameters': '{}'
        })
        assert response.status_code == 302  # Redirect after success
        assert AgentTemplate.objects.filter(name='New Template').exists()
    
    def test_create_template_validation(self, client, admin_user):
        """Test template creation validation."""
        client.force_login(admin_user)
        # Missing required fields
        response = client.post(reverse('agent_template_create'), {
            'name': '',  # Empty name
            'n8n_webhook_url': 'http://localhost:5678/webhook/test'
        })
        assert response.status_code == 200  # Form with errors
        assert 'Name is required' in response.content.decode()
    
    def test_update_template(self, client, admin_user, template):
        """Test updating a template."""
        client.force_login(admin_user)
        response = client.post(
            reverse('agent_template_detail', args=[template.id]),
            {
                'name': 'Updated Template',
                'description': template.description,
                'n8n_webhook_url': template.n8n_webhook_url,
                'status': 'inactive',
                'visibility': template.visibility,
                'default_parameters': '{}'
            }
        )
        assert response.status_code == 302
        template.refresh_from_db()
        assert template.name == 'Updated Template'
        assert template.status == 'inactive'
    
    def test_toggle_status(self, client, admin_user, template):
        """Test toggling template status."""
        client.force_login(admin_user)
        assert template.status == 'active'
        
        response = client.post(reverse('agent_template_toggle_status', args=[template.id]))
        assert response.status_code == 302
        template.refresh_from_db()
        assert template.status == 'inactive'
    
    @patch('engine.services.n8n_service.N8nService.call_webhook')
    def test_test_template(self, mock_call_webhook, client, admin_user, template):
        """Test template testing endpoint."""
        mock_call_webhook.return_value = {
            'reply': 'Test response from n8n',
            'metadata': {}
        }
        
        client.force_login(admin_user)
        response = client.post(
            reverse('agent_template_test', args=[template.id]),
            {
                'test_message': 'Hello, test',
                'test_user_id': admin_user.id
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'reply' in data['response']
        mock_call_webhook.assert_called_once()
    
    def test_api_list_endpoint(self, client, admin_user, template):
        """Test API list endpoint."""
        client.force_login(admin_user)
        response = client.get(reverse('agent_template_api_list'))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert 'templates' in data
        assert len(data['templates']) >= 1
    
    def test_api_list_filters(self, client, admin_user):
        """Test API list filtering."""
        AgentTemplate.objects.create(
            name="Active Template",
            n8n_webhook_url="http://localhost:5678/webhook/active",
            status="active"
        )
        AgentTemplate.objects.create(
            name="Inactive Template",
            n8n_webhook_url="http://localhost:5678/webhook/inactive",
            status="inactive"
        )
        
        client.force_login(admin_user)
        response = client.get(reverse('agent_template_api_list') + '?status=active')
        data = json.loads(response.content)
        assert all(t['status'] == 'active' for t in data['templates'])


@pytest.mark.django_db
class TestAgentTemplateSecurity:
    """Security tests for agent template views."""
    
    def test_unauthorized_access_blocked(self, client):
        """Test that unauthorized users cannot access admin views."""
        # Not logged in
        response = client.get(reverse('agent_template_list'))
        assert response.status_code in [302, 403]  # Redirect to login or forbidden
        
        # Regular user (not staff)
        user = User.objects.create_user(username="user", password="pass")
        client.force_login(user)
        response = client.get(reverse('agent_template_list'))
        assert response.status_code == 403
    
    def test_csrf_protection(self, client, admin_user):
        """Test CSRF protection on POST endpoints."""
        client.force_login(admin_user)
        # Try to create template without CSRF token
        response = client.post(
            reverse('agent_template_create'),
            {
                'name': 'CSRF Test',
                'n8n_webhook_url': 'http://localhost:5678/webhook/test'
            },
            enforce_csrf_checks=True
        )
        # Should fail CSRF check (403 or redirect)
        assert response.status_code in [403, 400]
    
    def test_sql_injection_prevention(self, client, admin_user):
        """Test that SQL injection attempts are prevented."""
        client.force_login(admin_user)
        # Attempt SQL injection in name field
        malicious_input = "'; DROP TABLE engine_agenttemplate; --"
        response = client.post(reverse('agent_template_create'), {
            'name': malicious_input,
            'n8n_webhook_url': 'http://localhost:5678/webhook/test',
            'default_parameters': '{}'
        })
        # Should either fail validation or escape the input
        # Template should not be created with malicious name
        assert not AgentTemplate.objects.filter(name__contains="DROP").exists()
    
    def test_xss_prevention(self, client, admin_user):
        """Test that XSS attempts are prevented in template fields."""
        client.force_login(admin_user)
        xss_payload = "<script>alert('XSS')</script>"
        response = client.post(reverse('agent_template_create'), {
            'name': xss_payload,
            'n8n_webhook_url': 'http://localhost:5678/webhook/test',
            'default_parameters': '{}'
        })
        # Check that script tags are escaped in response
        if response.status_code == 200:  # Form with errors
            content = response.content.decode()
            assert '<script>' not in content or content.index('<script>') > content.index('&lt;script&gt;')

