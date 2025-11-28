"""
Authentication and authorization decorators for views.

These decorators reduce code duplication by centralizing authentication
and user ownership checks.
"""
from functools import wraps
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def require_authentication(view_func):
    """
    Decorator that requires the user to be authenticated.
    Returns appropriate response based on request type (AJAX vs regular).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_user_ownership(model_class, lookup_field='pk', user_field='user'):
    """
    Decorator factory that ensures the user owns the requested object.
    
    Args:
        model_class: The model class to check ownership for
        lookup_field: The field name to use for lookup (default: 'pk')
        user_field: The field name on the model that stores the user (default: 'user')
    
    Usage:
        @require_user_ownership(Dataset)
        def my_view(request, dataset_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
                return redirect('login')
            
            # Get the object ID from kwargs
            obj_id = kwargs.get(lookup_field)
            if not obj_id:
                return HttpResponse('Object ID not found', status=400)
            
            # Check ownership
            from django.shortcuts import get_object_or_404
            obj = get_object_or_404(model_class, **{lookup_field: obj_id, user_field: request.user})
            
            # Add object to kwargs for use in view
            kwargs['_owned_object'] = obj
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_post_method(view_func):
    """
    Decorator that requires POST method.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method != 'POST':
            return HttpResponse('POST only', status=405)
        return view_func(request, *args, **kwargs)
    return wrapper



