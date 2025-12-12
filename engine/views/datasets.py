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
    try:
        dataset = Dataset.objects.get(pk=dataset_id)
    except Dataset.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Dataset not found'}, status=404)
    except (ValueError, TypeError):
        # Handle invalid dataset_id format
        return JsonResponse({'success': False, 'error': 'Invalid dataset ID'}, status=400)
    
    # Use efficient column-only loading for large datasets
    from engine.dataprep.loader import get_dataset_columns_only
    import os
    
    path = dataset.file_path
    if not path:
        return JsonResponse({
            'success': False,
            'error': f'Dataset has no file path: {dataset.name}'
        }, status=400)
    
    try:
        # Check if file exists before trying to read it
        if not os.path.exists(path):
            return JsonResponse({
                'success': False,
                'error': f'Dataset file not found: {dataset.name}'
            }, status=404)
        
        # Load dataset columns
        variables, column_types = get_dataset_columns_only(path)
        return JsonResponse({
            'success': True,
            'variables': variables,
            'column_types': column_types,
            'dataset_name': dataset.name
        })
    except FileNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': f'Dataset file not found: {dataset.name}'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except RuntimeError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in get_dataset_variables: {error_details}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to read dataset: {str(e)}'
        }, status=500)



def update_sessions_for_variable_rename(request, dataset_id):
    """API endpoint to update all sessions when variables are renamed"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST only'})
    
    try:
        # Get the rename mapping from request
        import json
        rename_map = json.loads(request.POST.get('rename_map', '{}'))
        
        if not rename_map:
            return JsonResponse({'success': False, 'error': 'No rename mapping provided'})
        
        # Find all sessions using this dataset
        sessions = AnalysisSession.objects.filter(dataset_id=dataset_id)
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
    
    f = request.FILES['dataset']
    
    # Hard limit: 10 MB maximum file size
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    if f.size > MAX_FILE_SIZE_BYTES:
        file_size_mb = f.size / (1024 * 1024)
        error_msg = f'File size ({file_size_mb:.2f} MB) exceeds the maximum allowed size of {MAX_FILE_SIZE_MB} MB. Please upload a smaller file.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        from django.contrib import messages
        messages.error(request, error_msg)
        return redirect('index')
    
    # Validate file size
    file_size_mb = f.size / (1024 * 1024)
    
    # Save file
    name = request.POST.get('dataset_name') or f.name
    safe = f.name.replace(' ', '_')
    slug = str(uuid.uuid4())[:8]
    path = os.path.join(DATASET_DIR, f"{slug}_{safe}")
    
    # Save file
    with open(path, 'wb') as dest:
        for chunk in f.chunks():
            dest.write(chunk)
    
    # Create or update dataset record
    dataset, created = _create_or_update_dataset(name, path, file_size_mb, None)
    
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
    ds = get_object_or_404(Dataset, pk=pk)
    # Detach sessions from this dataset
    AnalysisSession.objects.filter(dataset=ds).update(dataset=None)
    try:
        if os.path.exists(ds.file_path):
            os.remove(ds.file_path)
    except Exception:
        pass
    ds.delete()
    return redirect('index')



def preview_drop_rows(request, dataset_id):
    """API endpoint to preview which rows would be dropped"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_id)
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
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_id)
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
    """
    Save filtered dataframe to file.
    """
    import pandas as pd
    import os
    
    from engine.dataprep.views import _infer_dataset_format
    
    file_format = _infer_dataset_format(file_path)
    
    if file_format in ['xlsx', 'xls']:
        df_filtered.to_excel(file_path, index=False)
    elif file_format == 'tsv':
        df_filtered.to_csv(file_path, index=False, sep='\t')
    elif file_format == 'json':
        df_filtered.to_json(file_path, orient='records')
    else:  # default csv
        df_filtered.to_csv(file_path, index=False)




def merge_datasets(request):
    """API endpoint to merge multiple datasets based on common column values"""
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
        datasets, dataframes, error = DatasetMergeService.load_datasets(dataset_ids, None)
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Perform merge using service
        merged_df, error = DatasetMergeService.perform_merge(dataframes, merge_columns, datasets)
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Save merged dataset using service
        try:
            merged_dataset = DatasetMergeService.save_merged_dataset(merged_df, datasets, None)
            
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



