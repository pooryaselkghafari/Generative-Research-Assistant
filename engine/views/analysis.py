"""
Views for analysis execution (run_analysis, BMA, ANOVA, VARX, etc.).
"""
import os
import uuid
import json
import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from engine.models import Dataset, AnalysisSession
from engine.modules import get_module
from data_prep.file_handling import _read_dataset_file
from engine.helpers.analysis_helpers import (
    _validate_equation,
    _prepare_options,
    _execute_analysis,
    _build_table_data,
    _save_results,
    _prepare_template_context,
    _determine_template,
)
from engine.services.analysis_execution_service import AnalysisExecutionService
from engine.services.irf_service import IRFService
from engine.services.dataset_validation_service import DatasetValidationService
from engine.views.sessions import _list_context


def run_analysis(request):
    """Main analysis execution view - refactored to use helper functions."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)

    action = request.POST.get('action', 'new')  # 'new' or 'update'
    session_id = request.POST.get('session_id')
    print(f"DEBUG: run_analysis - action: {action}, session_id: {session_id}")
    print(f"DEBUG: run_analysis - POST data: {dict(request.POST)}")

    dataset_id = request.POST.get('dataset_id')
    if not dataset_id:
        return HttpResponse('Please select a dataset from the dropdown', status=400)
    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)

    try:
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Check if dataset is very large and warn user
        if len(df) > 100000:  # More than 100k rows
            # For very large datasets, suggest sampling
            sample_size = min(50000, len(df))  # Sample up to 50k rows
            if request.POST.get('use_sample', 'false').lower() == 'true':
                df = df.sample(n=sample_size, random_state=42)
                print(f"Using sample of {sample_size} rows from dataset with {len(df)} total rows")
            else:
                # Return a warning response suggesting to use sampling
                return JsonResponse({
                    'success': False,
                    'error': f'Dataset is very large ({len(df):,} rows). This may cause performance issues.',
                    'suggestion': 'Consider using a sample of the data for analysis.',
                    'sample_size': sample_size,
                    'total_rows': len(df)
                })
    except Exception as e:
        return HttpResponse(f'Failed to read dataset: {e}', status=400)

    analysis_type = request.POST.get('analysis_type', 'frequentist')
    template_override = request.POST.get('template_override', '')
    
    # Force module selection based on analysis type
    if analysis_type == 'bayesian':
        module_name = 'bayesian'
        print(f"DEBUG: Analysis type is Bayesian, forcing module_name to 'bayesian'")
    else:
        module_name = request.POST.get('module', 'regression')
        print(f"DEBUG: Analysis type is {analysis_type}, using module_name: {module_name}")
    formula = request.POST.get('formula', '')
    
    # Validate equation format matches selected model
    validation_error = _validate_equation(request, formula, module_name, df, _list_context)
    if validation_error:
        return validation_error

    # Prepare options
    options = _prepare_options(request, formula, df)

    session_name = request.POST.get('session_name') or f"Session {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Check session limits for new sessions (not updates)
    if action == 'new':
        limit_error = DatasetValidationService.check_session_limits(request.user, request)
        if limit_error:
            return limit_error

    # Special handling for BMA analysis
    if module_name == 'bma':
        return run_bma_analysis(request)
    
    # Special handling for ANOVA analysis
    if module_name == 'anova':
        return run_anova_analysis(request)
    
    # Special handling for VARX analysis
    if module_name == 'varx':
        return run_varx_analysis(request)
    
    # Execute analysis
    job_id = str(uuid.uuid4())[:8]
    outdir = os.path.join(settings.MEDIA_ROOT, job_id)
    os.makedirs(outdir, exist_ok=True)
    
    results = _execute_analysis(module_name, df, formula, analysis_type, options, column_types, schema_orders, outdir)
    
    # Build table data
    cols, model_table_matrix, estimate_col_index = _build_table_data(results)
    
    # Save results to session
    sess = _save_results(request, action, session_id, session_name, module_name, formula, 
                         analysis_type, options, dataset, results, cols, model_table_matrix)
    
    # Prepare template context
    ctx = _prepare_template_context(sess, dataset, results, cols, model_table_matrix, estimate_col_index, options)
    
    # Determine template
    template_name = _determine_template(results, template_override, analysis_type)
    
    return render(request, template_name, ctx)


def calculate_summary_stats(request, session_id):
    """Calculate summary statistics for selected variables."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Security: Only allow access to user's own sessions
        session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)
        dataset = session.dataset
        
        # Get selected variables from request
        selected_vars = request.POST.getlist('variables[]')
        if not selected_vars:
            return JsonResponse({'error': 'No variables selected'}, status=400)
        
        # Load dataset
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Calculate summary statistics for selected variables
        summary_stats = {}
        for var in selected_vars:
            if var in df.columns and pd.api.types.is_numeric_dtype(df[var]):
                series = df[var].dropna()
                if len(series) > 0:
                    summary_stats[var] = {
                        'min': float(series.min()),
                        'max': float(series.max()),
                        'range': float(series.max() - series.min()),
                        'variance': float(series.var(ddof=1)),
                        'vif': float('nan')  # VIF not calculated for non-formula variables
                    }
        
        return JsonResponse({'summary_stats': summary_stats})
        
    except AnalysisSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cancel_bayesian_analysis(request):
    """Cancel a running Bayesian analysis"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            # Cancel specific session
            # Security: Only allow access to user's own sessions
            session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
            
            # Instead of marking as cancelled, we'll just return success
            # The frontend will reload to show the previous state
            return JsonResponse({
                'success': True,
                'message': 'Analysis cancellation requested'
            })
        else:
            return JsonResponse({'error': 'Session ID required'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error cancelling analysis: {str(e)}'}, status=500)


def run_bma_analysis(request):
    """Handle BMA analysis requests"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        # Get parameters from request
        action = request.POST.get('action', 'new')
        session_id = request.POST.get('session_id')
        dataset_id = request.POST.get('dataset_id')
        formula = request.POST.get('formula', '')
        categorical_vars = request.POST.get('categorical_vars', '')
        
        # Execute BMA analysis using service
        return AnalysisExecutionService.execute_bma_analysis(
            request, action, session_id, dataset_id, formula, categorical_vars
        )
        
    except Exception as e:
        return render(request, 'engine/index.html', {
            **_list_context(user=request.user),
            'error_message': f'Error running BMA analysis: {str(e)}'
        })


def run_anova_analysis(request):
    """Handle ANOVA analysis requests"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        # Get parameters from request
        action = request.POST.get('action', 'new')
        session_id = request.POST.get('session_id')
        dataset_id = request.POST.get('dataset_id')
        formula = request.POST.get('formula', '')
        
        # Execute ANOVA analysis using service
        return AnalysisExecutionService.execute_anova_analysis(
            request, action, session_id, dataset_id, formula
        )
        
    except Exception as e:
        import traceback
        error_msg = f'Error running ANOVA analysis: {str(e)}'
        print(f"ANOVA ERROR: {error_msg}")
        print(traceback.format_exc())
        return render(request, 'engine/index.html', {
            **_list_context(user=request.user),
            'error_message': error_msg
        })


def run_varx_analysis(request):
    """Handle VARX analysis requests"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        # Get parameters from request
        action = request.POST.get('action', 'new')
        session_id = request.POST.get('session_id')
        dataset_id = request.POST.get('dataset_id')
        formula = request.POST.get('formula', '')
        var_order_input = request.POST.get('var_order', None)
        max_lags_input = request.POST.get('max_lags', 10)

        # Debug logging to trace VAR lag issues
        debug_payload = {
            'action': action,
            'session_id': session_id,
            'dataset_id': dataset_id,
            'var_order_input': var_order_input,
            'max_lags_input': max_lags_input,
            'formula_length': len(formula) if formula else 0,
        }
        print("DEBUG: run_varx_analysis request payload:", debug_payload)
        print("DEBUG: run_varx_analysis POST keys:", list(request.POST.keys()))
        
        # Execute VARX analysis using service
        response = AnalysisExecutionService.execute_varx_analysis(
            request, action, session_id, dataset_id, formula, var_order_input, max_lags_input
        )
        print("DEBUG: run_varx_analysis completed")
        return response
        
    except Exception as e:
        import traceback
        error_msg = f'Error running VARX analysis: {str(e)}'
        print(f"VARX ERROR: {error_msg}")
        print(traceback.format_exc())
        return render(request, 'engine/index.html', {
            **_list_context(user=request.user),
            'error_message': error_msg
        })


@csrf_exempt
@require_http_methods(["POST"])
def generate_varx_irf_view(request, session_id):
    """Generate Impulse Response Function plot for VARX analysis"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        # Security: Only allow access to user's own sessions
        session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
        
        # Validate session using service
        is_valid, error = IRFService.validate_session_for_irf(session)
        if not is_valid:
            return JsonResponse({'error': error}, status=400)
        
        # Get parameters
        data = json.loads(request.body)
        periods = int(data.get('irf_horizon', data.get('periods', 10)))
        shock_var = data.get('shock_var') or data.get('irf_shock_var')
        response_vars = data.get('response_vars', [])
        if not response_vars:
            response_var = data.get('response_var') or data.get('irf_response_var')
            if response_var:
                response_vars = [response_var]
        shock_type = data.get('shock_type', 'orthogonal')
        show_ci = data.get('show_ci', data.get('irf_show_ci', True))
        
        # Generate IRF using service
        result = IRFService.generate_irf_plot(
            session, periods, shock_var, response_vars, shock_type, show_ci
        )
        
        if not result.get('success', True):
            return JsonResponse({'error': result.get('error', 'Failed to generate IRF')}, status=500)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': f'Error generating IRF: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_varx_irf_data_view(request, session_id):
    """Generate IRF data (not plot) for VARX analysis"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        # Security: Only allow access to user's own sessions
        session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
        
        # Validate session using service
        is_valid, error = IRFService.validate_session_for_irf(session)
        if not is_valid:
            return JsonResponse({'error': error}, status=400)
        
        # Get parameters
        data = json.loads(request.body)
        periods = int(data.get('irf_horizon', data.get('periods', 10)))
        shock_var = data.get('shock_var') or data.get('irf_shock_var')
        response_vars = data.get('response_vars', [])
        if not response_vars:
            response_var = data.get('response_var') or data.get('irf_response_var')
            if response_var:
                response_vars = [response_var]
        
        # Generate IRF data using service
        result = IRFService.generate_irf_data(session, periods, shock_var, response_vars)
        
        if not result.get('success', True):
            return JsonResponse({'error': result.get('error', 'Failed to generate IRF data')}, status=500)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': f'Error generating IRF data: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ai_chat(request):
    """
    Handle AI chat requests. Sends user messages to an AI API and returns responses.
    Expects JSON with:
    - message: user's message
    - context (optional): additional context about the current analysis/session
    """
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        context = data.get('context', '')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Here you would integrate with your AI service
        # For now, return a placeholder response
        response = {
            'success': True,
            'response': f'AI chat functionality is not yet implemented. Your message was: {message}'
        }
        
        return JsonResponse(response)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


def add_model_errors_to_dataset(request, session_id):
    """
    Add model residuals/errors to the dataset as new columns.
    
    IMPORTANT: This function does NOT modify the analysis session in any way.
    It only adds new columns to the dataset file. The session's formula, 
    dependent variables, and all other analysis parameters remain unchanged.
    """
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        import json
        import re
        from data_prep.file_handling import _read_dataset_file
        from engine.services.model_service import ModelService
        from engine.services.residual_service import ResidualCalculationService
        from engine.services.dataset_service import DatasetService
        
        # Get session and dataset (read-only - we will NOT modify the session)
        # Security: Only allow access to user's own sessions
        session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
        data = json.loads(request.body)
        dataset_id = data.get('dataset_id')
        
        if not dataset_id:
            return JsonResponse({'error': 'dataset_id is required'}, status=400)
        
        # Security: Only allow access to user's own datasets
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        
        # Store original session formula to ensure it's never modified
        original_formula = session.formula
        
        # Load the dataset
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Get fitted models for all equations
        try:
            equation_results = ModelService.get_equation_results(session, dataset)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            import traceback
            print(f"DEBUG: Error getting equation results: {e}")
            print(traceback.format_exc())
            return JsonResponse({'error': f'Failed to get fitted models: {str(e)}'}, status=500)
        
        # Get session name for column naming (read-only - only used for naming new columns)
        session_name = session.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        session_name = re.sub(r'[^\w\-_]', '_', session_name)
        
        # Calculate residuals for all equations
        residual_columns, column_names = ResidualCalculationService.calculate_all_residuals(
            equation_results=equation_results,
            session_name=session_name,
            df=df
        )
        
        # Add residual columns to dataframe
        df = DatasetService.align_and_add_residuals(df, residual_columns, column_names)
        
        # Ensure all new columns are properly formatted (convert to numeric, handle NaN)
        import pandas as pd
        import numpy as np
        for col_name in column_names:
            if col_name in df.columns:
                # Ensure the column is numeric (float) and handle any type issues
                try:
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                except Exception as e:
                    print(f"DEBUG: Warning - could not convert {col_name} to numeric: {e}")
                    # If conversion fails, try to keep as is or convert to string
                    pass
        
        # Clean up any duplicate columns that might have been created
        df = df.loc[:, ~df.columns.duplicated()].copy()
        
        # Save the updated dataset (handling encryption if needed)
        # NOTE: We only save the dataset file, NOT the session
        from engine.encrypted_storage import is_encrypted_file, save_encrypted_dataframe
        from engine.dataprep.views import _infer_dataset_format
        
        try:
            if is_encrypted_file(dataset.file_path):
                # File is encrypted - use encrypted save function
                file_format = _infer_dataset_format(dataset.file_path)
                save_encrypted_dataframe(df, dataset.file_path, user_id=request.user.id, file_format=file_format)
            else:
                # File is not encrypted - use regular save
                DatasetService.save_dataframe(df, dataset.file_path)
        except Exception as save_error:
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG: Error saving dataset after adding residuals: {save_error}")
            print(f"DEBUG: Traceback: {error_details}")
            return JsonResponse({
                'error': f'Failed to save dataset after adding errors: {str(save_error)}'
            }, status=500)
        
        # CRITICAL: Verify session was not modified (safety check)
        # Refresh from database to ensure we have the latest state
        session.refresh_from_db()
        if session.formula != original_formula:
            # This should never happen, but log it if it does
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"WARNING: Session formula was modified during add_model_errors_to_dataset. "
                f"Original: {original_formula[:100]}, Current: {session.formula[:100]}"
            )
            # Restore original formula
            session.formula = original_formula
            session.save(update_fields=['formula'])
        
        # Return success - session remains unchanged
        return JsonResponse({
            'success': True,
            'columns_added': len(column_names),
            'column_names': column_names,
            'message': f'Successfully added {len(column_names)} residual column(s) to dataset. Analysis session unchanged.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}\nTraceback: {traceback.format_exc()}'
        print(error_msg)
        return JsonResponse({'error': f'Failed to add model errors: {str(e)}'}, status=500)

