"""
Service for executing different types of analyses (BMA, ANOVA, VARX).

This service encapsulates analysis execution logic to keep views thin
and improve maintainability.
"""
from typing import Dict, Any, Optional
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from engine.models import Dataset, AnalysisSession
from data_prep.file_handling import _read_dataset_file
from engine.views.sessions import _list_context


class AnalysisExecutionService:
    """Service for executing analyses."""
    
    @staticmethod
    def execute_bma_analysis(request, action, session_id, dataset_id, formula, categorical_vars):
        """
        Execute BMA analysis.
        
        Args:
            request: Django request object
            action: 'new' or 'update'
            session_id: Session ID if updating
            dataset_id: Dataset ID
            formula: Analysis formula
            categorical_vars: Categorical variables string
            
        Returns:
            Rendered template response
        """
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter a formula', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Import BMA module
        from models.BMA import BMAModule
        
        # Create BMA module instance
        bma_module = BMAModule()
        
        # Prepare options
        options = {}
        if categorical_vars:
            options['categorical_vars'] = categorical_vars
        
        # Run BMA analysis
        result = bma_module.run(df, formula, options)
        
        if not result['success']:
            return render(request, 'engine/index.html', {
                **_list_context(user=request.user),
                'error_message': result.get('error', 'BMA analysis failed')
            })
        
        # Create or update session
        session_name = request.POST.get('session_name') or f"BMA Analysis {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        sess = AnalysisExecutionService._create_or_update_session(
            action, session_id, session_name, 'bma', formula, 'bayesian', options, dataset, request.user
        )
        
        # Render results
        return render(request, 'engine/BMA_results.html', {
            'session': sess,
            'dataset': dataset,
            **result
        })
    
    @staticmethod
    def execute_anova_analysis(request, action, session_id, dataset_id, formula):
        """
        Execute ANOVA analysis.
        
        Args:
            request: Django request object
            action: 'new' or 'update'
            session_id: Session ID if updating
            dataset_id: Dataset ID
            formula: Analysis formula
            
        Returns:
            Rendered template response or error response
        """
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter a formula', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Import ANOVA module
        from models.ANOVA import ANOVAModule
        
        # Create ANOVA module instance
        anova_module = ANOVAModule()
        
        # Run ANOVA analysis
        result = anova_module.run(df, formula, {})
        
        if not result.get('has_results', False):
            return render(request, 'engine/index.html', {
                **_list_context(user=request.user),
                'error_message': result.get('error', 'ANOVA analysis failed')
            })
        
        # Create or update session
        session_name = request.POST.get('session_name') or f"ANOVA Analysis {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        sess = AnalysisExecutionService._create_or_update_session(
            action, session_id, session_name, 'anova', formula, 'frequentist', {}, dataset, request.user
        )
        
        # Get numeric variables from dataset for plot generation dropdowns
        import pandas as pd
        import numpy as np
        numeric_vars = []
        try:
            # Get numeric columns (int64, float64, etc.)
            numeric_vars = df.select_dtypes(include=[np.number]).columns.tolist()
            # Filter out any columns that are all NaN
            numeric_vars = [var for var in numeric_vars if not df[var].isna().all()]
        except Exception as e:
            print(f"DEBUG: Error getting numeric variables: {e}")
            # Fallback: try to identify numeric columns manually
            numeric_vars = []
            for col in df.columns:
                try:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        numeric_vars.append(col)
                except:
                    pass
        
        # Render results
        return render(request, 'engine/ANOVA_results.html', {
            'session': sess,
            'dataset': dataset,
            'results': result,
            'formula': formula,
            'numeric_vars': numeric_vars
        })
    
    @staticmethod
    def execute_varx_analysis(request, action, session_id, dataset_id, formula, var_order_input, max_lags_input):
        """
        Execute VARX analysis.
        
        Args:
            request: Django request object
            action: 'new' or 'update'
            session_id: Session ID if updating
            dataset_id: Dataset ID
            formula: Analysis formula
            var_order_input: VAR order input
            max_lags_input: Max lags input
            
        Returns:
            Rendered template response or error response
        """
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter a formula', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Import VARX module
        from models.VARX import VARXModule
        
        # Create VARX module instance
        varx_module = VARXModule()
        
        # Prepare options
        try:
            max_lags = int(max_lags_input)
        except (ValueError, TypeError):
            max_lags = 10
        
        # Handle var_order input - preserve manual selection
        var_order = 'auto'
        manual_value_raw = None
        if var_order_input is not None:
            manual_value_raw = str(var_order_input).strip()
            print(f"DEBUG: Raw var_order_input received: '{manual_value_raw}' (type={type(var_order_input)})")
            if manual_value_raw.lower() != 'auto' and manual_value_raw != '':
                try:
                    # Allow inputs like "3", "3.0", or "  4 "
                    manual_value = float(manual_value_raw)
                    if manual_value > 0:
                        manual_int = int(round(manual_value))
                        if manual_int <= 0:
                            raise ValueError("Lag order must be positive")
                        var_order = manual_int
                        print(f"DEBUG: Manual VAR lag order accepted: {var_order} (raw input: {manual_value_raw})")
                    else:
                        print(f"DEBUG: Invalid VAR lag order (<=0): {manual_value_raw}. Falling back to auto.")
                except (ValueError, TypeError):
                    print(f"DEBUG: Could not parse VAR lag order input '{manual_value_raw}', using auto-selection.")
            else:
                print(f"DEBUG: VAR lag order set to auto (input='{manual_value_raw}')")
        
        options = {
            'var_order': var_order,
            'max_lags': max_lags
        }
        print(f"DEBUG: VARX options prepared: {options}")
        
        # Run VARX analysis
        result = varx_module.run(df, formula, options=options)
        print(f"DEBUG: VARX module run completed. has_results={result.get('has_results')}, error={result.get('error')}")
        
        if not result.get('has_results', False):
            return render(request, 'engine/index.html', {
                **_list_context(user=request.user),
                'error_message': result.get('error', 'VARX analysis failed')
            })
        
        # Create or update session
        session_name = request.POST.get('session_name') or f"VARX Analysis {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        sess = AnalysisExecutionService._create_or_update_session(
            action, session_id, session_name, 'varx', formula, 'frequentist', options, dataset, request.user
        )
        
        # Store VARX model results for IRF generation
        model_results = result.get('model_results')
        endog_data = result.get('endog_data')
        dependent_vars = result.get('dependent_vars', [])
        if model_results and endog_data is not None:
            try:
                import pickle
                varx_data = {
                    'model_results': model_results,
                    'endog_data': endog_data,
                    'dependent_vars': dependent_vars
                }
                sess.fitted_model = pickle.dumps(varx_data)
                sess.save()
                print("Stored VARX model results for IRF generation")
            except Exception as e:
                print(f"Note: Could not store VARX model results (may not be pickleable): {e}")
                # This is OK - IRF service will re-run if needed
        
        # Render results
        return render(request, 'engine/VARX_results.html', {
            'session': sess,
            'dataset': dataset,
            'results': result,
            'formula': formula
        })
    
    @staticmethod
    def execute_structural_analysis(request, action, session_id, dataset_id, formula, structural_method):
        """
        Execute structural model (SUR/2SLS/3SLS) analysis.
        
        Args:
            request: Django request object
            action: 'new' or 'update'
            session_id: Session ID if updating
            dataset_id: Dataset ID
            formula: Analysis formula (equations separated by semicolons)
            structural_method: 'SUR', '2SLS', or '3SLS'
            
        Returns:
            Rendered template response or error response
        """
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter equation(s)', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Import structural model module
        from models.structural_model import StructuralModelModule
        
        # Create structural model module instance
        structural_module = StructuralModelModule()
        
        # Normalize method to uppercase and strip whitespace (handle case variations like '3ls' -> '3SLS')
        method_upper = structural_method.strip().upper() if structural_method else 'SUR'
        valid_methods = ['SUR', '2SLS', '3SLS']
        if method_upper not in valid_methods:
            return render(request, 'engine/index.html', {
                **_list_context(user=request.user),
                'error_message': f'Invalid method: "{structural_method}" (normalized: "{method_upper}"). Method must be one of {valid_methods}.'
            })
        
        # Prepare options
        options = {
            'method': method_upper
        }
        
        # Run structural analysis
        result = structural_module.run(df, formula, options=options)
        
        if not result.get('has_results', False):
            return render(request, 'engine/index.html', {
                **_list_context(user=request.user),
                'error_message': result.get('error', 'Structural model analysis failed')
            })
        
        # Create or update session
        session_name = request.POST.get('session_name') or f"Structural Model ({structural_method}) {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        sess = AnalysisExecutionService._create_or_update_session(
            action, session_id, session_name, 'structural', formula, 'frequentist', options, dataset, request.user
        )
        
        # Render results
        return render(request, 'engine/structural_model_results.html', {
            'session': sess,
            'dataset': dataset,
            'results': result,
            'formula': formula,
            'method': structural_method
        })
    
    @staticmethod
    def _create_or_update_session(action, session_id, session_name, module_name, formula, 
                                  analysis_type, options, dataset, user):
        """Create or update analysis session."""
        if action == 'update' and session_id:
            sess = get_object_or_404(AnalysisSession, pk=session_id, user=user)
            sess.name = session_name
            sess.module = module_name
            sess.formula = formula
            sess.options = options
            sess.dataset = dataset
            if not sess.user and user.is_authenticated:
                sess.user = user
        else:
            user_obj = user if user.is_authenticated else None
            sess = AnalysisSession(
                name=session_name, module=module_name, formula=formula,
                analysis_type=analysis_type, options=options, dataset=dataset,
                user=user_obj
            )
        
        sess.save()
        return sess

