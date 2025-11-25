""
"Tests for chatbot access control based on subscription workflow mapping."
""
import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from engine.models import AgentTemplate, SubscriptionPlan, UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestChatbotAccess:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username='testuser', password='testpass', email='test@example.com')

    def test_access_requires_login(self, client):
        response = client.get(reverse('chatbot_access_check'))
        assert response.status_code in (302, 401)

    def test_access_denied_when_no_workflow(self, client, user):
        client.force_login(user)
        # Ensure user profile exists with default plan lacking workflow
        free_plan = SubscriptionPlan.objects.create(
            name='Free',
            price_monthly=0,
            max_datasets=5,
            max_sessions=10,
            max_file_size_mb=10
        )
        UserProfile.objects.create(user=user, subscription_plan=free_plan)

        response = client.get(reverse('chatbot_access_check'))
        assert response.status_code == 200
        payload = json.loads(response.content)
        assert payload['allowed'] is False
        assert payload['requires_upgrade'] is True

    def test_access_allowed_when_workflow_mapped(self, client, user):
        client.force_login(user)
        template = AgentTemplate.objects.create(
            name='Chatbot Template',
            description='Test template',
            n8n_webhook_url='http://localhost:5678/webhook/test',
            status='active',
            visibility='customer_facing'
        )
        free_plan = SubscriptionPlan.objects.create(
            name='Free',
            price_monthly=0,
            max_datasets=5,
            max_sessions=10,
            max_file_size_mb=10,
            workflow_template=template
        )
        UserProfile.objects.create(user=user, subscription_plan=free_plan)

        response = client.get(reverse('chatbot_access_check'))
        assert response.status_code == 200
        payload = json.loads(response.content)
        assert payload['allowed'] is True
        assert payload['template']['id'] == template.id

