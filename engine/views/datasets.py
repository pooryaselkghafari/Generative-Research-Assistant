"""
Views for dataset management (upload, delete, variables, merge).
"""
import os
import uuid
import json
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from engine.models import Dataset, AnalysisSession
from engine.services.dataset_validation_service import DatasetValidationService
from engine.services.row_filtering_service import RowFilteringService
from engine.services.dataset_merge_service import DatasetMergeService
from data_prep.file_handling import _read_dataset_file

# Create media directories lazily (not at import time)
# This prevents permission errors during management commands
try:
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    DATASET_DIR = os.path.join(settings.MEDIA_ROOT, 'datasets')
    os.makedirs(DATASET_DIR, exist_ok=True)
except (PermissionError, OSError):
    # If we can't create directories at import time, create them when needed
    DATASET_DIR = os.path.join(settings.MEDIA_ROOT, 'datasets')

def get_dataset_variables(request, dataset_id):
    """API endpoint to get variables from a dataset"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    # Security: Only allow access to user's own datasets
    # First check if dataset exists and belongs to user
    try:
        dataset = Dataset.objects.get(pk=dataset_id, user=request.user)
    except Dataset.DoesNotExist:
        # Return 403 (Forbidden) instead of 404 to indicate access denied
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    except (ValueError, TypeError):
        # Handle invalid dataset_id format
        return JsonResponse({'success': False, 'error': 'Invalid dataset ID'}, status=400)
    
    # Use efficient column-only loading for large datasets
    from engine.dataprep.loader import get_dataset_columns_only
    from engine.encrypted_storage import is_encrypted_file, get_decrypted_path
    import os
    
    path = dataset.file_path
    decrypted_path = None
    
    # Check if file is encrypted and handle accordingly
    if is_encrypted_file(path):
        decrypted_path = get_decrypted_path(path, user_id=request.user.id)
        working_path = decrypted_path
    else:
        working_path = path
    
    try:
        # Check if file exists before trying to read it
        if not os.path.exists(working_path):
            return JsonResponse({
                'success': False,
                'error': f'Dataset file not found: {dataset.name}'
            }, status=404)
        
        variables, column_types = get_dataset_columns_only(working_path, user_id=request.user.id)
        return JsonResponse({
            'success': True,
            'variables': variables,
            'column_types': column_types,
            'dataset_name': dataset.name
        })
    except FileNotFoundError:
        return JsonResponse({
            'success': False,
            'error': f'Dataset file not found: {dataset.name}'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    finally:
        # Clean up temporary decrypted file if it was created
        if decrypted_path and os.path.exists(decrypted_path):
            try:
                os.unlink(decrypted_path)
            except:
                pass



def update_sessions_for_variable_rename(request, dataset_id):
    """API endpoint to update all sessions when variables are renamed"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST only'})
    
    try:
        # Get the rename mapping from request
        import json
        rename_map = json.loads(request.POST.get('rename_map', '{}'))
        
        if not rename_map:
            return JsonResponse({'success': False, 'error': 'No rename mapping provided'})
        
        # Find all sessions using this dataset
        # Security: Only update user's own sessions
        sessions = AnalysisSession.objects.filter(dataset_id=dataset_id, user=request.user)
        updated_count = 0
        
        for session in sessions:
            # Update the formula with new variable names
            old_formula = session.formula
            new_formula = old_formula
            
            # Replace each old variable name with new name
            for old_name, new_name in rename_map.items():
                if old_name != new_name:  # Only replace if actually changed
                    # Use word boundaries to avoid partial matches
                    import re
                    pattern = r'\b' + re.escape(old_name) + r'\b'
                    new_formula = re.sub(pattern, new_name, new_formula)
            
            # Only update if formula actually changed
            if new_formula != old_formula:
                session.formula = new_formula
                session.save()
                updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_sessions': updated_count,
            'message': f'Updated {updated_count} analysis sessions'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })



def upload_dataset(request):
    """Upload a dataset file."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    if 'dataset' not in request.FILES:
        return HttpResponse('No dataset file provided', status=400)
    
    # Ensure directories exist (create if needed)
    try:
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        os.makedirs(DATASET_DIR, exist_ok=True)
    except (PermissionError, OSError) as e:
        return JsonResponse({'success': False, 'error': f'Cannot create media directory: {str(e)}'}, status=500)
    
    user = request.user
    f = request.FILES['dataset']
    
    # Check user limits using service
    file_size_mb, _ = DatasetValidationService.validate_file_size(f.size)
    limit_error = DatasetValidationService.check_user_limits(user, file_size_mb, request)
    if limit_error:
        return limit_error
    
    # Save file (with encryption if enabled)
    name = request.POST.get('dataset_name') or f.name
    safe = f.name.replace(' ', '_')
    slug = str(uuid.uuid4())[:8]
    path = os.path.join(DATASET_DIR, f"{slug}_{safe}")
    
    # Check if encryption is enabled
    if getattr(settings, 'ENCRYPT_DATASETS', False):
        # Use encrypted storage
        from engine.encrypted_storage import store_encrypted_file
        path = store_encrypted_file(f, user_id=user.id)
    else:
        # Save unencrypted
        with open(path, 'wb') as dest:
            for chunk in f.chunks():
                dest.write(chunk)
    
    # Create or update dataset record
    dataset, created = _create_or_update_dataset(name, path, file_size_mb, user)
    
    # Return response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'dataset_id': dataset.id,
            'dataset_name': dataset.name,
            'message': 'Dataset uploaded successfully'
        })
    
    if created:
        return redirect(f'/app/?dataset_id={dataset.id}')
    return redirect('index')


def _create_or_update_dataset(name, path, file_size_mb, user):
    """Create or update a dataset record."""
    if user:
        dataset, created = Dataset.objects.get_or_create(
            name=name,
            user=user,
            defaults={
                'file_path': path,
                'file_size_mb': file_size_mb
            }
        )
        if not created:
            dataset.file_path = path
            dataset.file_size_mb = file_size_mb
            dataset.save()
    else:
        dataset, created = Dataset.objects.update_or_create(
            name=name,
            user=None,
            defaults={
                'file_path': path,
                'file_size_mb': file_size_mb
            }
        )
    return dataset, created



def delete_dataset(request, pk: int):
    # Require authentication
    if not request.user.is_authenticated:
        return redirect('login')
    # Security: Only allow deletion of user's own datasets
    ds = get_object_or_404(Dataset, pk=pk, user=request.user)
    # Detach sessions from this dataset (only user's own sessions)
    AnalysisSession.objects.filter(dataset=ds, user=request.user).update(dataset=None)
    try:
        if os.path.exists(ds.file_path):
            os.remove(ds.file_path)
    except Exception:
        pass
    ds.delete()
    return redirect('index')



def preview_drop_rows(request, dataset_id):
    """API endpoint to preview which rows would be dropped"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        # Security: Only allow access to user's own datasets
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        data = json.loads(request.body)
        conditions = data.get('conditions', [])
        
        if not conditions:
            return JsonResponse({'error': 'No conditions provided'}, status=400)
        
        # Use service to preview drop rows
        result = RowFilteringService.preview_drop_rows(df, conditions)
        
        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=400)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




def apply_drop_rows(request, dataset_id):
    """API endpoint to apply row dropping"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        # Security: Only allow access to user's own datasets
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        data = json.loads(request.body)
        conditions = data.get('conditions', [])
        
        if not conditions:
            return JsonResponse({'error': 'No conditions provided'}, status=400)
        
        # Use service to apply drop rows
        df_filtered, rows_dropped, error = RowFilteringService.apply_drop_rows(df, conditions)
        
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Save the filtered dataset back to the file
        _save_filtered_dataset(df_filtered, dataset.file_path)
        
        return JsonResponse({
            'success': True,
            'rows_dropped': rows_dropped,
            'rows_remaining': len(df_filtered)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _save_filtered_dataset(df_filtered, file_path):
    """Save filtered dataframe to file."""
    import pandas as pd
    file_extension = file_path.lower().split('.')[-1]
    if file_extension in ['xlsx', 'xls']:
        df_filtered.to_excel(file_path, index=False)
    else:  # CSV
        df_filtered.to_csv(file_path, index=False)




def merge_datasets(request):
    """API endpoint to merge multiple datasets based on common column values"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        data = json.loads(request.body)
        dataset_ids = data.get('datasets', [])
        merge_columns = data.get('merge_columns', [])
        
        # Validate input
        if len(dataset_ids) < 2:
            return JsonResponse({'error': 'At least 2 datasets required for merge'}, status=400)
        
        if len(merge_columns) != len(dataset_ids):
            return JsonResponse({'error': 'Must specify merge column for each dataset'}, status=400)
        
        # Load datasets using service
        datasets, dataframes, error = DatasetMergeService.load_datasets(dataset_ids, request.user)
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Perform merge using service
        merged_df, error = DatasetMergeService.perform_merge(dataframes, merge_columns, datasets)
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Save merged dataset using service
        try:
            merged_dataset = DatasetMergeService.save_merged_dataset(merged_df, datasets, request.user)
            
            return JsonResponse({
                'success': True,
                'dataset_id': merged_dataset.id,
                'dataset_name': merged_dataset.name,
                'rows': len(merged_df),
                'columns': len(merged_df.columns)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error saving merged dataset: {str(e)}'}, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)



