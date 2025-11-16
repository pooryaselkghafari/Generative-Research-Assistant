"""
Admin-only URLs for AI fine-tuning dashboard.

These URLs are restricted to staff members only and provide
the interface for managing AI fine-tuning operations.
"""
from django.urls import path
from engine.views.admin_dashboard import (
    ai_finetuning_dashboard,
    upload_finetuning_file,
    delete_finetuning_file,
    toggle_file_active,
    execute_finetuning_command,
)

urlpatterns = [
    path('', ai_finetuning_dashboard, name='ai_finetuning_dashboard'),
    path('upload-file/', upload_finetuning_file, name='upload_finetuning_file'),
    path('delete-file/<int:file_id>/', delete_finetuning_file, name='delete_finetuning_file'),
    path('toggle-file/<int:file_id>/', toggle_file_active, name='toggle_file_active'),
    path('execute-command/', execute_finetuning_command, name='execute_finetuning_command'),
]
