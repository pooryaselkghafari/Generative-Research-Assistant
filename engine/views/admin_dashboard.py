"""
Admin dashboard views for AI fine-tuning.

These views handle the admin interface for managing AI fine-tuning
files and commands. All views require staff member authentication.
"""
import json
from typing import Dict, Any
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from engine.models import AIFineTuningFile, AIFineTuningCommand, AIFineTuningTemplate
from engine.services.ai_finetuning_service import AIFineTuningService


@staff_member_required
def ai_finetuning_dashboard(request):
    """
    Render the main AI fine-tuning dashboard.
    
    Args:
        request: Django request object
        
    Returns:
        Rendered template with active files, recent commands, and templates
    """
    active_files = AIFineTuningService.get_active_files()
    recent_commands = AIFineTuningService.get_recent_commands(limit=20)
    templates = AIFineTuningTemplate.objects.filter(is_active=True).order_by('command_type', 'name')
    
    # Serialize template data for JavaScript
    import json
    templates_data = []
    for template in templates:
        # template_data is already a dict from JSONField, serialize it
        templates_data.append({
            'id': template.id,
            'name': template.name,
            'command_type': template.command_type,
            'template_data': template.template_data,  # Already a dict, will be JSON serialized
        })
    
    context = {
        'active_files': active_files,
        'recent_commands': recent_commands,
        'templates': templates,
        'templates_json': json.dumps(templates_data),
    }
    return render(request, 'admin/ai_finetuning_dashboard.html', context)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def upload_finetuning_file(request) -> JsonResponse:
    """
    Handle file upload for fine-tuning.
    
    Args:
        request: Django request object with file in FILES
        
    Returns:
        JsonResponse with success status and file info
    """
    if 'file' not in request.FILES:
        return JsonResponse(
            {'success': False, 'error': 'No file provided'},
            status=400
        )
    
    try:
        file = request.FILES['file']
        name = request.POST.get('name', file.name)
        description = request.POST.get('description', '')
        file_type = request.POST.get('file_type', AIFineTuningFile.FILE_TYPE_TRAINING)
        
        finetuning_file = AIFineTuningFile.objects.create(
            name=name,
            file=file,
            description=description,
            file_type=file_type,
            uploaded_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'file_id': finetuning_file.id,
            'name': finetuning_file.name,
            'file_type': finetuning_file.get_file_type_display(),
        })
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500
        )


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def delete_finetuning_file(request, file_id: int) -> JsonResponse:
    """
    Delete a fine-tuning file.
    
    Args:
        request: Django request object
        file_id: ID of the file to delete
        
    Returns:
        JsonResponse with success status
    """
    try:
        file = AIFineTuningFile.objects.get(id=file_id)
        file.delete()
        return JsonResponse({'success': True})
    except AIFineTuningFile.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'File not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500
        )


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def toggle_file_active(request, file_id: int) -> JsonResponse:
    """
    Toggle file active status.
    
    Args:
        request: Django request object
        file_id: ID of the file to toggle
        
    Returns:
        JsonResponse with success status and new active state
    """
    try:
        file = AIFineTuningFile.objects.get(id=file_id)
        file.is_active = not file.is_active
        file.save()
        return JsonResponse({
            'success': True,
            'is_active': file.is_active
        })
    except AIFineTuningFile.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'File not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500
        )


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def execute_finetuning_command(request) -> JsonResponse:
    """
    Execute a fine-tuning command.
    
    Args:
        request: Django request object with JSON body
        
    Returns:
        JsonResponse with success status and command info
    """
    try:
        data = json.loads(request.body)
        command_type = data.get('command_type', AIFineTuningCommand.COMMAND_TYPE_FINE_TUNE)
        description = data.get('description', '')
        command_data = data.get('command_data', {})
        file_ids = data.get('file_ids', [])
        
        if not description:
            return JsonResponse(
                {'success': False, 'error': 'Description is required'},
                status=400
            )
        
        command = AIFineTuningCommand.objects.create(
            command_type=command_type,
            description=description,
            command_data=command_data,
            created_by=request.user
        )
        
        if file_ids:
            files = AIFineTuningFile.objects.filter(id__in=file_ids)
            command.files.set(files)
        
        result = AIFineTuningService.process_fine_tune_command(command)
        
        return JsonResponse({
            'success': result['success'],
            'command_id': command.id,
            'status': command.status,
            'message': result['message'],
        })
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500
        )
