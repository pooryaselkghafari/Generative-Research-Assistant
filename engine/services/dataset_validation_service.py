"""
Service for validating dataset uploads and user limits.

This service encapsulates validation logic for dataset uploads,
including user limit checks and file size validation.
"""
from typing import Tuple, Optional
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect


class DatasetValidationService:
    """Service for dataset validation."""
    
    @staticmethod
    def check_user_limits(user, file_size_mb: float, request) -> Optional[JsonResponse]:
        """
        Check if user has reached dataset or file size limits.
        
        Args:
            user: User object
            file_size_mb: File size in MB
            request: Django request object
            
        Returns:
            JsonResponse with error if limits exceeded, None otherwise
        """
        if not user:
            return None
        
        profile = user.profile
        limits = profile.get_limits()
        
        # Check dataset count limit
        if limits['datasets'] != -1:  # -1 means unlimited
            current_count = user.datasets.count()
            if current_count >= limits['datasets']:
                error_msg = (
                    f"You have reached your dataset limit ({limits['datasets']} datasets). "
                    f"Please delete some datasets or upgrade your plan."
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=403)
                messages.error(request, error_msg)
                return redirect('index')
        
        # Check file size limit
        if limits['file_size'] != -1 and file_size_mb > limits['file_size']:
            error_msg = (
                f"File size ({file_size_mb:.2f} MB) exceeds your plan limit "
                f"({limits['file_size']} MB). Please upgrade your plan."
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=403)
            messages.error(request, error_msg)
            return redirect('index')
        
        return None
    
    @staticmethod
    def check_session_limits(user, request) -> Optional[JsonResponse]:
        """
        Check if user has reached session limits.
        
        Args:
            user: User object
            request: Django request object
            
        Returns:
            JsonResponse with error if limits exceeded, None otherwise
        """
        if not user or not user.is_authenticated:
            return None
        
        profile = user.profile
        limits = profile.get_limits()
        
        # Check session count limit
        if limits['sessions'] != -1:  # -1 means unlimited
            current_count = user.sessions.count()
            if current_count >= limits['sessions']:
                error_msg = (
                    f"You have reached your session limit ({limits['sessions']} sessions). "
                    f"Please delete some sessions or upgrade your plan."
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=403)
                messages.error(request, error_msg)
                return redirect('index')
        
        return None
    
    @staticmethod
    def validate_file_size(file_size_bytes: int) -> Tuple[float, bool]:
        """
        Validate file size and convert to MB.
        
        Args:
            file_size_bytes: File size in bytes
            
        Returns:
            Tuple of (file_size_mb, is_valid)
        """
        file_size_mb = file_size_bytes / (1024 * 1024)
        # No maximum validation here - that's done in check_user_limits
        return file_size_mb, True


