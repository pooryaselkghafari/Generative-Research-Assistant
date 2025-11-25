"""
Chatbot endpoint that integrates with n8n agent templates.
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.urls import reverse
from engine.models import AgentTemplate, UserProfile, SubscriptionTierSettings
from engine.services.n8n_service import N8nService

logger = logging.getLogger(__name__)

def _get_subscription_template(user):
    """Return the agent template mapped to the user's subscription tier, if any."""
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'subscription_type': 'free', 'ai_tier': 'none'}
    )
    tier_settings = (
        SubscriptionTierSettings.objects.select_related('workflow_template')
        .filter(tier=profile.subscription_type, is_active=True)
        .first()
    )
    if tier_settings and tier_settings.workflow_template and tier_settings.workflow_template.is_usable():
        return tier_settings.workflow_template
    return None


@login_required
@require_http_methods(["GET"])
def chatbot_access_check(request):
    """
    Check whether the current user has access to the chatbot based on their subscription tier.
    """
    template = _get_subscription_template(request.user)
    if not template:
        upgrade_url = reverse('subscription')
        return JsonResponse({
            'allowed': False,
            'requires_upgrade': True,
            'message': 'Your current subscription is not connected to the Generative Research Assistant yet. Upgrade to unlock AI workflows.',
            'upgrade_url': upgrade_url,
        })

    return JsonResponse({
        'allowed': True,
        'template': {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'n8n_webhook_url': template.n8n_webhook_url,
            'workflow': template.workflow.workflow_id if template.workflow else None,
        }
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def chatbot_endpoint(request):
    """
    Main chatbot endpoint that routes messages to n8n agent templates.
    
    Expected POST JSON:
    {
        "message": "User's message text",
        "mode_key": "Optional mode key to select specific template",
        "template_id": "Optional template ID to use",
        "conversation_id": "Optional conversation ID for context",
        "chat_history": [Optional list of previous messages]
    }
    
    Returns JSON:
    {
        "success": true/false,
        "reply": "Chatbot response message",
        "metadata": {Optional additional data from n8n},
        "template_used": {Template info},
        "error": "Error message if success=false"
    }
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        # Validate required fields
        message = data.get('message', '').strip()
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message is required'
            }, status=400)
        
        # Sanitize message (basic validation)
        if len(message) > 10000:
            return JsonResponse({
                'success': False,
                'error': 'Message too long (max 10000 characters)'
            }, status=400)
        
        # Get optional parameters
        mode_key = data.get('mode_key')
        template_id = data.get('template_id')
        conversation_id = data.get('conversation_id')
        chat_history = data.get('chat_history', [])
        
        # Validate chat_history
        if not isinstance(chat_history, list):
            chat_history = []
        
        # Select template
        template = None
        if template_id:
            try:
                template = AgentTemplate.objects.get(pk=template_id)
            except AgentTemplate.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Template with ID {template_id} not found'
                }, status=404)
        elif mode_key:
            try:
                template = AgentTemplate.objects.get(mode_key=mode_key)
            except AgentTemplate.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Template with mode_key "{mode_key}" not found'
                }, status=404)
        else:
            template = _get_subscription_template(request.user)
        
        if not template and request.user.is_staff:
            template = AgentTemplate.objects.filter(status='active').first()

        if not template:
            return JsonResponse({
                'success': False,
                'error': 'No workflow is connected to your subscription yet. Please upgrade to unlock AI chat.',
                'requires_upgrade': True,
                'upgrade_url': reverse('subscription')
            }, status=403)
        
        # Check if user can use this template
        if not template.can_be_used_by(request.user):
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to use this template'
            }, status=403)
        
        # Build payload
        payload = N8nService.build_chatbot_payload(
            user_id=request.user.id,
            message=message,
            template_id=template.id,
            mode_key=template.mode_key,
            conversation_id=conversation_id,
            chat_history=chat_history,
            additional_parameters=template.default_parameters
        )
        
        # Call n8n webhook
        try:
            logger.info(
                f"Calling n8n webhook for chatbot: template={template.name} (ID: {template.id}), user={request.user.id}",
                extra={
                    'template_id': template.id,
                    'template_name': template.name,
                    'user_id': request.user.id,
                    'message_length': len(message)
                }
            )
            
            response = N8nService.call_webhook(
                template.n8n_webhook_url,
                payload
            )
            
            # Extract reply from response
            reply = response.get('reply', '')
            metadata = response.get('metadata', {})
            
            logger.info(
                f"Successfully received response from n8n: template={template.name} (ID: {template.id}), user={request.user.id}",
                extra={
                    'template_id': template.id,
                    'template_name': template.name,
                    'user_id': request.user.id,
                    'reply_length': len(reply) if reply else 0
                }
            )
            
            return JsonResponse({
                'success': True,
                'reply': reply,
                'metadata': metadata,
                'template_used': {
                    'id': template.id,
                    'name': template.name,
                    'mode_key': template.mode_key
                }
            })
            
        except ValueError as e:
            # Validation error from n8n service
            logger.error(
                f"Validation error calling n8n webhook: {e}",
                extra={
                    'template_id': template.id,
                    'template_name': template.name,
                    'user_id': request.user.id,
                    'error': str(e)
                }
            )
            return JsonResponse({
                'success': False,
                'error': f'Invalid response from agent: {str(e)}'
            }, status=500)
            
        except Exception as e:
            # Other errors (network, timeout, etc.)
            logger.error(
                f"Error calling n8n webhook: {e}",
                extra={
                    'template_id': template.id,
                    'template_name': template.name,
                    'user_id': request.user.id,
                    'error': str(e)
                },
                exc_info=True
            )
            return JsonResponse({
                'success': False,
                'error': f'Error communicating with agent: {str(e)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in chatbot endpoint: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)

