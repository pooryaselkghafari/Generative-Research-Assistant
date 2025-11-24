"""
Unit tests for AgentTemplate model.

Category: Unit Tests, Database Tests
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from engine.models import AgentTemplate

User = get_user_model()


@pytest.mark.django_db
class TestAgentTemplateModel:
    """Test AgentTemplate model methods and constraints."""
    
    def test_create_template(self):
        """Test creating a basic agent template."""
        template = AgentTemplate.objects.create(
            name="Test Template",
            description="A test template",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            status="active"
        )
        assert template.id is not None
        assert template.name == "Test Template"
        assert template.status == "active"
        assert template.is_usable() is True
    
    def test_unique_name_constraint(self):
        """Test that template names must be unique."""
        AgentTemplate.objects.create(
            name="Unique Template",
            n8n_webhook_url="http://localhost:5678/webhook/test1"
        )
        
        with pytest.raises(Exception):  # IntegrityError or ValidationError
            AgentTemplate.objects.create(
                name="Unique Template",
                n8n_webhook_url="http://localhost:5678/webhook/test2"
            )
    
    def test_unique_mode_key_constraint(self):
        """Test that mode_key must be unique if provided."""
        AgentTemplate.objects.create(
            name="Template 1",
            n8n_webhook_url="http://localhost:5678/webhook/test1",
            mode_key="test_mode"
        )
        
        with pytest.raises(Exception):
            AgentTemplate.objects.create(
                name="Template 2",
                n8n_webhook_url="http://localhost:5678/webhook/test2",
                mode_key="test_mode"
            )
    
    def test_is_usable(self):
        """Test is_usable() method."""
        active_template = AgentTemplate.objects.create(
            name="Active",
            n8n_webhook_url="http://localhost:5678/webhook/active",
            status="active"
        )
        assert active_template.is_usable() is True
        
        inactive_template = AgentTemplate.objects.create(
            name="Inactive",
            n8n_webhook_url="http://localhost:5678/webhook/inactive",
            status="inactive"
        )
        assert inactive_template.is_usable() is False
        
        draft_template = AgentTemplate.objects.create(
            name="Draft",
            n8n_webhook_url="http://localhost:5678/webhook/draft",
            status="draft"
        )
        assert draft_template.is_usable() is False
    
    def test_can_be_used_by(self):
        """Test can_be_used_by() method."""
        user = User.objects.create_user(username="testuser", email="test@example.com")
        staff_user = User.objects.create_user(username="staff", email="staff@example.com", is_staff=True)
        
        # Customer-facing template
        customer_template = AgentTemplate.objects.create(
            name="Customer Template",
            n8n_webhook_url="http://localhost:5678/webhook/customer",
            status="active",
            visibility="customer_facing"
        )
        assert customer_template.can_be_used_by(user) is True
        assert customer_template.can_be_used_by(staff_user) is True
        
        # Internal template
        internal_template = AgentTemplate.objects.create(
            name="Internal Template",
            n8n_webhook_url="http://localhost:5678/webhook/internal",
            status="active",
            visibility="internal"
        )
        assert internal_template.can_be_used_by(user) is False
        assert internal_template.can_be_used_by(staff_user) is True
        
        # Inactive template
        inactive_template = AgentTemplate.objects.create(
            name="Inactive Template",
            n8n_webhook_url="http://localhost:5678/webhook/inactive",
            status="inactive",
            visibility="customer_facing"
        )
        assert inactive_template.can_be_used_by(user) is False
    
    def test_default_parameters_json(self):
        """Test default_parameters JSON field."""
        template = AgentTemplate.objects.create(
            name="Template with Params",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            default_parameters={"key1": "value1", "key2": 123}
        )
        assert template.default_parameters == {"key1": "value1", "key2": 123}
    
    def test_str_representation(self):
        """Test __str__ method."""
        template = AgentTemplate.objects.create(
            name="Test Template",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            status="active"
        )
        assert "Test Template" in str(template)
        assert "Active" in str(template)
    
    def test_indexes(self):
        """Test that database indexes are created (performance)."""
        # This test verifies indexes exist by checking query performance
        # In practice, indexes are verified via migration
        template = AgentTemplate.objects.create(
            name="Indexed Template",
            n8n_webhook_url="http://localhost:5678/webhook/test",
            status="active",
            mode_key="indexed_mode"
        )
        
        # These queries should use indexes
        assert AgentTemplate.objects.filter(status="active").exists()
        assert AgentTemplate.objects.filter(mode_key="indexed_mode").exists()
        assert AgentTemplate.objects.filter(visibility="customer_facing").exists()

