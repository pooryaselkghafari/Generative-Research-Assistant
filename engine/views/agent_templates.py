"""
Views for Agent Template Manager (admin interface for managing n8n workflow templates).
"""
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from engine.models import AgentTemplate
from engine.services.n8n_service import N8nService

logger = logging.getLogger(__name__)


@staff_member_required
@require_http_methods(["GET"])
def agent_template_list(request):
    """
    List all agent templates with pagination and filtering.
    
    Query parameters:
    - page: Page number (default: 1)
    - status: Filter by status (active, inactive, draft)
    - search: Search in name and description
    """
    templates = AgentTemplate.objects.all()
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter in ['active', 'inactive', 'draft']:
        templates = templates.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        templates = templates.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'templates': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': templates.count(),
        'active_count': AgentTemplate.objects.filter(status='active').count(),
    }
    
    return render(request, 'admin/agent_template/list.html', context)


@staff_member_required
@require_http_methods(["GET", "POST"])
def agent_template_create(request):
    """Create a new agent template."""
    if request.method == 'POST':
        try:
            # Parse form data
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            n8n_webhook_url = request.POST.get('n8n_webhook_url', '').strip()
            status = request.POST.get('status', 'draft')
            visibility = request.POST.get('visibility', 'customer_facing')
            mode_key = request.POST.get('mode_key', '').strip() or None
            default_parameters_str = request.POST.get('default_parameters', '{}')
            
            # Validation
            if not name:
                messages.error(request, 'Name is required')
                return render(request, 'admin/agent_template/create.html', {
                    'form_data': request.POST
                })
            
            if not n8n_webhook_url:
                messages.error(request, 'n8n Webhook URL is required')
                return render(request, 'admin/agent_template/create.html', {
                    'form_data': request.POST
                })
            
            # Parse default_parameters JSON
            try:
                default_parameters = json.loads(default_parameters_str) if default_parameters_str else {}
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON in default parameters')
                return render(request, 'admin/agent_template/create.html', {
                    'form_data': request.POST
                })
            
            # Check for duplicate name
            if AgentTemplate.objects.filter(name=name).exists():
                messages.error(request, f'Template with name "{name}" already exists')
                return render(request, 'admin/agent_template/create.html', {
                    'form_data': request.POST
                })
            
            # Check for duplicate mode_key if provided
            if mode_key and AgentTemplate.objects.filter(mode_key=mode_key).exists():
                messages.error(request, f'Template with mode_key "{mode_key}" already exists')
                return render(request, 'admin/agent_template/create.html', {
                    'form_data': request.POST
                })
            
            # Create template
            template = AgentTemplate.objects.create(
                name=name,
                description=description,
                n8n_webhook_url=n8n_webhook_url,
                status=status,
                visibility=visibility,
                mode_key=mode_key,
                default_parameters=default_parameters,
                created_by=request.user
            )
            
            logger.info(
                f"Agent template created: {template.name} (ID: {template.id})",
                extra={'template_id': template.id, 'user_id': request.user.id}
            )
            
            messages.success(request, f'Agent template "{template.name}" created successfully')
            return redirect('agent_template_detail', template_id=template.id)
            
        except Exception as e:
            logger.error(f"Error creating agent template: {e}", exc_info=True)
            messages.error(request, f'Error creating template: {str(e)}')
            return render(request, 'admin/agent_template/create.html', {
                'form_data': request.POST
            })
    
    return render(request, 'admin/agent_template/create.html')


@staff_member_required
@require_http_methods(["GET", "POST"])
def agent_template_detail(request, template_id):
    """View and edit an agent template."""
    template = get_object_or_404(AgentTemplate, pk=template_id)
    
    if request.method == 'POST':
        try:
            # Parse form data
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            n8n_webhook_url = request.POST.get('n8n_webhook_url', '').strip()
            status = request.POST.get('status', 'draft')
            visibility = request.POST.get('visibility', 'customer_facing')
            mode_key = request.POST.get('mode_key', '').strip() or None
            default_parameters_str = request.POST.get('default_parameters', '{}')
            
            # Validation
            if not name:
                messages.error(request, 'Name is required')
                return render(request, 'admin/agent_template/detail.html', {
                    'template': template,
                    'form_data': request.POST
                })
            
            if not n8n_webhook_url:
                messages.error(request, 'n8n Webhook URL is required')
                return render(request, 'admin/agent_template/detail.html', {
                    'template': template,
                    'form_data': request.POST
                })
            
            # Parse default_parameters JSON
            try:
                default_parameters = json.loads(default_parameters_str) if default_parameters_str else {}
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON in default parameters')
                return render(request, 'admin/agent_template/detail.html', {
                    'template': template,
                    'form_data': request.POST
                })
            
            # Check for duplicate name (excluding current template)
            if AgentTemplate.objects.filter(name=name).exclude(pk=template_id).exists():
                messages.error(request, f'Template with name "{name}" already exists')
                return render(request, 'admin/agent_template/detail.html', {
                    'template': template,
                    'form_data': request.POST
                })
            
            # Check for duplicate mode_key (excluding current template)
            if mode_key and AgentTemplate.objects.filter(mode_key=mode_key).exclude(pk=template_id).exists():
                messages.error(request, f'Template with mode_key "{mode_key}" already exists')
                return render(request, 'admin/agent_template/detail.html', {
                    'template': template,
                    'form_data': request.POST
                })
            
            # Update template
            template.name = name
            template.description = description
            template.n8n_webhook_url = n8n_webhook_url
            template.status = status
            template.visibility = visibility
            template.mode_key = mode_key
            template.default_parameters = default_parameters
            template.save()
            
            logger.info(
                f"Agent template updated: {template.name} (ID: {template.id})",
                extra={'template_id': template.id, 'user_id': request.user.id}
            )
            
            messages.success(request, f'Agent template "{template.name}" updated successfully')
            return redirect('agent_template_detail', template_id=template.id)
            
        except Exception as e:
            logger.error(f"Error updating agent template: {e}", exc_info=True)
            messages.error(request, f'Error updating template: {str(e)}')
            return render(request, 'admin/agent_template/detail.html', {
                'template': template,
                'form_data': request.POST
            })
    
    return render(request, 'admin/agent_template/detail.html', {
        'template': template
    })


@staff_member_required
@require_http_methods(["POST"])
def agent_template_toggle_status(request, template_id):
    """Toggle template status between active and inactive."""
    template = get_object_or_404(AgentTemplate, pk=template_id)
    
    if template.status == 'active':
        template.status = 'inactive'
        action = 'deactivated'
    else:
        template.status = 'active'
        action = 'activated'
    
    template.save()
    
    logger.info(
        f"Agent template {action}: {template.name} (ID: {template.id})",
        extra={'template_id': template.id, 'user_id': request.user.id, 'new_status': template.status}
    )
    
    messages.success(request, f'Template "{template.name}" {action}')
    return redirect('agent_template_detail', template_id=template.id)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt  # For AJAX requests
def agent_template_test(request, template_id):
    """
    Test an agent template by sending a sample payload to the n8n webhook.
    
    Expected POST data:
    - test_message: Sample message to send
    - test_user_id: Optional user ID (defaults to request.user.id)
    """
    template = get_object_or_404(AgentTemplate, pk=template_id)
    
    if not template.is_usable():
        return JsonResponse({
            'success': False,
            'error': f'Template is not active (status: {template.status})'
        }, status=400)
    
    try:
        # Get test data
        test_message = request.POST.get('test_message') or request.json().get('test_message') if hasattr(request, 'json') else None
        if not test_message:
            test_message = "Hello, this is a test message from the Agent Template Manager."
        
        test_user_id = request.POST.get('test_user_id') or (request.json().get('test_user_id') if hasattr(request, 'json') else None)
        if not test_user_id:
            test_user_id = request.user.id
        
        # Build payload
        payload = N8nService.build_chatbot_payload(
            user_id=int(test_user_id),
            message=test_message,
            template_id=template.id,
            mode_key=template.mode_key,
            additional_parameters=template.default_parameters
        )
        
        # Call webhook
        try:
            response = N8nService.call_webhook(
                template.n8n_webhook_url,
                payload,
                timeout=10  # Shorter timeout for testing
            )
            
            logger.info(
                f"Test webhook call successful: {template.name} (ID: {template.id})",
                extra={'template_id': template.id, 'user_id': request.user.id}
            )
            
            return JsonResponse({
                'success': True,
                'response': response,
                'payload_sent': payload
            })
            
        except Exception as e:
            logger.error(
                f"Test webhook call failed: {template.name} (ID: {template.id}): {e}",
                extra={'template_id': template.id, 'user_id': request.user.id, 'error': str(e)}
            )
            
            return JsonResponse({
                'success': False,
                'error': str(e),
                'payload_sent': payload
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error testing agent template: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error testing template: {str(e)}'
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
@csrf_exempt  # For AJAX requests
def agent_template_api_list(request):
    """API endpoint to list all templates (JSON)."""
    templates = AgentTemplate.objects.all()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter in ['active', 'inactive', 'draft']:
        templates = templates.filter(status=status_filter)
    
    # Filter by visibility if provided
    visibility_filter = request.GET.get('visibility')
    if visibility_filter in ['internal', 'customer_facing']:
        templates = templates.filter(visibility=visibility_filter)
    
    # Return only active templates for non-staff users
    if not request.user.is_staff:
        templates = templates.filter(status='active', visibility='customer_facing')
    
    data = [{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'status': t.status,
        'visibility': t.visibility,
        'mode_key': t.mode_key,
        'n8n_webhook_url': t.n8n_webhook_url,  # Only for staff
        'created_at': t.created_at.isoformat(),
        'updated_at': t.updated_at.isoformat(),
    } for t in templates]
    
    return JsonResponse({'templates': data})

