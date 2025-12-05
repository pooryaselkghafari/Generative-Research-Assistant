"""
Helper functions for analysis operations.

These functions extract complex logic from run_analysis() to improve
maintainability and testability.
"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.conf import settings
from engine.models import Dataset, AnalysisSession
from data_prep.file_handling import _read_dataset_file
from history.history import track_session_iteration


def count_equations(formula_str):
    """Count number of equations (lines with ~)"""
    if not formula_str or not formula_str.strip():
        return 0
    lines = [line.strip() for line in formula_str.split('\n') if line.strip()]
    return len([line for line in lines if '~' in line])


def count_dependent_variables(formula_str):
    """Count dependent variables in equation (variables before ~)"""
    if not formula_str or not formula_str.strip():
        return 0
    
    lines = [line.strip() for line in formula_str.split('\n') if line.strip()]
    total_dvs = 0
    for line in lines:
        if '~' in line:
            lhs = line.split('~')[0].strip()
            # Count variables on LHS (split by +)
            vars_list = [v.strip() for v in lhs.split('+') if v.strip()]
            total_dvs += len(vars_list)
    return total_dvs


def _validate_equation(request, formula, module_name, df, _list_context_func):
    """
    Validate that the equation format matches the selected model.
    
    Returns:
        None if validation passes, HttpResponse/JsonResponse if validation fails
    """
    equation_count = count_equations(formula)
    dv_count = count_dependent_variables(formula)
    
    # DIAGNOSTICS: Log equation detection
    print(f"=== BACKEND VALIDATION DIAGNOSTICS ===")
    print(f"Formula: {formula}")
    print(f"Module: {module_name}")
    print(f"Equation count: {equation_count}")
    print(f"Total dependent variables: {dv_count}")
    
    # Check for multi-equation format (multiple lines with ~)
    if equation_count > 1:
        print(f"✓ MULTI-EQUATION FORMAT DETECTED: {equation_count} equations")
        # Regression and structural models support multi-equation format
        if module_name != 'regression' and module_name != 'structural':
            return render(request, 'engine/index.html', {
                **_list_context_func(user=request.user),
                'error_message': f'You have {equation_count} equation(s) (one per line), but {module_name.upper()} models only support a single equation. Please use only one equation, or select Regression/Structural model for multiple equations.'
            })
        # Parse lines once for all multi-equation validations
        lines = [line.strip() for line in formula.split('\n') if line.strip() and '~' in line]
        
        # For structural models with multiple equations, each equation should have exactly 1 DV
        if module_name == 'structural':
            # Check if 2SLS is selected with multiple equations
            structural_method = request.POST.get('structural_method', 'SUR')
            if structural_method == '2SLS' and equation_count > 1:
                print(f"✗ VALIDATION FAILED: 2SLS with {equation_count} equations")
                print(f"=== END BACKEND VALIDATION DIAGNOSTICS ===")
                return render(request, 'engine/index.html', {
                    **_list_context_func(user=request.user),
                    'error_message': f'You have {equation_count} equation(s), but 2SLS only supports a single equation. Please use only one equation for 2SLS, or select SUR/3SLS method for multiple equations.'
                })
            
            print(f"Validating each structural equation has exactly 1 DV...")
            for i, line in enumerate(lines):
                lhs = line.split('~')[0].strip()
                vars_list = [v.strip() for v in lhs.split('+') if v.strip()]
                print(f"  Line {i + 1}: '{line}' - DVs: {len(vars_list)} ({', '.join(vars_list)})")
                if len(vars_list) > 1:
                    print(f"✗ VALIDATION FAILED: Line {i + 1} has {len(vars_list)} dependent variables")
                    print(f"=== END BACKEND VALIDATION DIAGNOSTICS ===")
                    return render(request, 'engine/index.html', {
                        **_list_context_func(user=request.user),
                        'error_message': f'Line {i + 1} has {len(vars_list)} dependent variable(s). In structural models, each equation must have exactly one dependent variable. Please use one dependent variable per line, for example: y1 ~ x1 + x2\\ny2 ~ x1 + [x3 ~ z1 + z2]'
                    })
            print(f"✓ All structural equations validated: each has exactly 1 DV")
            print(f"=== END BACKEND VALIDATION DIAGNOSTICS ===")
            return None  # Validation passed for structural models
        
        # For regression with multiple equations, each equation should have exactly 1 DV
        print(f"Validating each equation has exactly 1 DV...")
        for i, line in enumerate(lines):
            lhs = line.split('~')[0].strip()
            vars_list = [v.strip() for v in lhs.split('+') if v.strip()]
            print(f"  Line {i + 1}: '{line}' - DVs: {len(vars_list)} ({', '.join(vars_list)})")
            if len(vars_list) > 1:
                print(f"✗ VALIDATION FAILED: Line {i + 1} has {len(vars_list)} dependent variables")
                print(f"=== END BACKEND VALIDATION DIAGNOSTICS ===")
                return render(request, 'engine/index.html', {
                    **_list_context_func(user=request.user),
                    'error_message': f'Line {i + 1} has {len(vars_list)} dependent variable(s). In multi-equation regression, each equation must have exactly one dependent variable. Please use one dependent variable per line, for example: y1 ~ x1 + x2\\ny2 ~ x1 + x3'
                })
        print(f"✓ All equations validated: each has exactly 1 DV")
    
    # VARX/VARMAX requires 2+ dependent variables (but only in single equation format)
    if module_name in ['varx', 'varmax']:
        if equation_count > 1:
            return render(request, 'engine/index.html', {
                **_list_context_func(user=request.user),
                'error_message': 'VARX/VARMAX models require a single equation with 2+ dependent variables, not multiple equations. Please combine into one equation, for example: y1 + y2 ~ x1 + x2'
            })
        if dv_count < 2:
            return render(request, 'engine/index.html', {
                **_list_context_func(user=request.user),
                'error_message': f'VARX/VARMAX models require at least 2 dependent variables. Your equation has {dv_count} dependent variable(s). Please add more dependent variables before the ~ symbol, for example: y1 + y2 ~ x1 + x2'
            })
    elif module_name != 'regression' or equation_count == 1:
        # For non-regression models, or single-equation regression, require exactly 1 dependent variable
        if dv_count > 1:
            return render(request, 'engine/index.html', {
                **_list_context_func(user=request.user),
                'error_message': f'Your equation has {dv_count} dependent variable(s), but {module_name.upper()} models only support a single dependent variable. Please use only one dependent variable before the ~ symbol, or select VARX model for multiple dependent variables.'
            })
        elif dv_count == 0:
            return render(request, 'engine/index.html', {
                **_list_context_func(user=request.user),
                'error_message': 'Your equation must have at least one dependent variable before the ~ symbol.'
            })
    
    return None  # Validation passed


def _prepare_options(request, formula, df):
    """
    Prepare options dictionary from request POST data.
    
    Returns:
        dict: Options dictionary
    """
    options = {
        # Display options
        'show_se': request.POST.get('show_se') == 'on',
        'show_ci': request.POST.get('show_ci') == 'on',
        'bootstrap': request.POST.get('bootstrap', 'off') == 'on',
        'n_boot': int(request.POST.get('n_boot', '500')),
        'interaction_terms': request.POST.get('interaction_terms', ''),
        'x_name': request.POST.get('x_name') or None,
        'y_name': request.POST.get('y_name') or None,
        'moderator_name': request.POST.get('moderator_name') or None,
        'plot_color_low': request.POST.get('plot_color_low', '#999999'),
        'plot_color_high': request.POST.get('plot_color_high', '#111111'),
        'line_style_low': request.POST.get('line_style_low', 'solid'),
        'line_style_high': request.POST.get('line_style_high', 'dashed'),
        'spotlight_ci': request.POST.get('spotlight_ci', 'on') == 'on',
        'partial_covariates': request.POST.get('partial_covariates', '').strip(),
        'custom_labels': request.POST.get('custom_labels', '').strip(),
        'show_t': request.POST.get('show_t') == 'on',
        'show_p': request.POST.get('show_p') == 'on',
        'show_min': request.POST.get('show_min', 'on') == 'on',  # Default to True
        'show_max': request.POST.get('show_max', 'on') == 'on',  # Default to True
        'show_range': request.POST.get('show_range') == 'on',
        'show_variance': request.POST.get('show_variance') == 'on',
        'show_vif': request.POST.get('show_vif') == 'on',
        'show_r2': request.POST.get('show_r2') == 'on',
        'show_aic': request.POST.get('show_aic') == 'on',
        
        # Bayesian model parameters
        'draws': int(request.POST.get('draws', '2000')),
        'tune': int(request.POST.get('tune', '1000')),
        'chains': int(request.POST.get('chains', '4')),
        'cores': int(request.POST.get('cores', '2')),
        'prior': request.POST.get('prior', 'auto'),
    }
    
    # Detect if dependent variable is ordered categorical to inform module selection
    try:
        dep_var = (formula.split('~', 1)[0] or '').strip()
        if dep_var in df.columns:
            col = df[dep_var]
            is_ordered = hasattr(col.dtype, 'ordered') and bool(getattr(col.dtype, 'ordered'))
            options['dependent_is_ordered'] = is_ordered
        else:
            options['dependent_is_ordered'] = False
    except Exception:
        options['dependent_is_ordered'] = False
    
    return options


def _execute_analysis(module_name, df, formula, analysis_type, options, column_types, schema_orders, outdir):
    """
    Execute the analysis using the specified module.
    
    Returns:
        dict: Results dictionary from the module
    """
    import os
    import uuid
    from engine.modules import get_module
    
    mod = get_module(module_name)
    results = mod.run(
        df, 
        formula=formula, 
        analysis_type=analysis_type, 
        outdir=outdir, 
        options=options, 
        schema_types=column_types, 
        schema_orders=schema_orders
    )
    return results


def _build_table_data(results):
    """
    Build table data for the template (robust to old/new module return formats).
    
    Returns:
        tuple: (cols, model_table_matrix, estimate_col_index)
    """
    def _stars(p):
        try:
            p = float(p)
        except Exception:
            return ""
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        if p < 0.10:  return "."
        return ""
    
    cols = results.get("model_table_cols", [])
    rows = results.get("model_table_rows", [])
    
    # Fallback ONLY if the new keys are missing (old module shape)
    if (not cols) and isinstance(results.get("model_table"), dict):
        old = results["model_table"]
        if "columns" in old and "data" in old:
            cols = ["Term", "Estimate"]
            rows = []
            oc = old["columns"]
            od = old["data"]
            term_idx = oc.index("term") if "term" in oc else None
            coef_idx = oc.index("coef") if "coef" in oc else None
            p_idx = oc.index("p") if "p" in oc else None
            stat_idx = oc.index("stat") if "stat" in oc else None
            for r in od:
                term = r[term_idx] if term_idx is not None else ""
                coef = r[coef_idx] if coef_idx is not None else ""
                pval = r[p_idx] if p_idx is not None else None
                stat = r[stat_idx] if stat_idx is not None else ""
                cell = f"{coef}{_stars(pval)}<div class='sub'>{stat}</div>"
                rows.append({"Term": term, "Estimate": cell})
    
    # Build matrix for template
    if cols and rows:
        # Handle both list of lists (Bayesian) and list of dicts (other modules)
        if rows and isinstance(rows[0], list):
            # Bayesian format: list of lists
            model_table_matrix = rows
        else:
            # Other modules format: list of dicts
            model_table_matrix = [[row.get(c, "") for c in cols] for row in rows]
        estimate_col_index = cols.index("Estimate") if "Estimate" in cols else -1
    else:
        model_table_matrix, estimate_col_index = [], -1
    
    return cols, model_table_matrix, estimate_col_index


def _save_results(request, action, session_id, session_name, module_name, formula, 
                  analysis_type, options, dataset, results, cols, model_table_matrix):
    """
    Save analysis results to session and track history.
    
    Returns:
        AnalysisSession: The saved session object
    """
    if action == 'update' and session_id:
        print(f"DEBUG: Updating existing session {session_id}")
        # Security: Only allow access to user's own sessions
        sess = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
        
        sess.name = session_name
        sess.module = module_name
        sess.formula = formula
        sess.analysis_type = analysis_type
        sess.options = options
        sess.dataset = dataset
        # Ensure user is set
        if not sess.user and request.user.is_authenticated:
            sess.user = request.user
    else:
        print(f"DEBUG: Creating new session (action: {action}, session_id: {session_id})")
        # Associate session with user if authenticated
        user = request.user if request.user.is_authenticated else None
        sess = AnalysisSession(
            name=session_name, module=module_name, formula=formula,
            analysis_type=analysis_type, options=options, dataset=dataset,
            user=user
        )
    
    sess.spotlight_rel = results.get('spotlight_rel')
    
    # Store the fitted model for future spotlight plot generation
    fitted_model = results.get('fitted_model')
    if fitted_model:
        try:
            import pickle
            sess.fitted_model = pickle.dumps(fitted_model)
            print("Stored fitted model in session")
        except Exception as e:
            print(f"Failed to store fitted model: {e}")
    
    # Store VARX model results for IRF generation
    if module_name in ['varx', 'varmax']:
        model_results = results.get('model_results')
        endog_data = results.get('endog_data')
        dependent_vars = results.get('dependent_vars', [])
        if model_results and endog_data is not None:
            try:
                import pickle
                varx_data = {
                    'model_results': model_results,
                    'endog_data': endog_data,
                    'dependent_vars': dependent_vars
                }
                sess.fitted_model = pickle.dumps(varx_data)
                print("Stored VARX model results for IRF generation")
            except Exception as e:
                print(f"Failed to store VARX model results: {e}")
    
    # Store ordinal predictions if available
    ordinal_predictions = results.get('ordinal_predictions')
    if ordinal_predictions:
        try:
            sess.ordinal_predictions = ordinal_predictions
            print("Stored ordinal predictions in session")
        except Exception as e:
            print(f"Failed to store ordinal predictions: {e}")
    
    # Store multinomial predictions if available
    multinomial_predictions = results.get('multinomial_predictions')
    print(f"DEBUG: multinomial_predictions from results: {multinomial_predictions}")
    if multinomial_predictions:
        try:
            sess.multinomial_predictions = multinomial_predictions
            print("Stored multinomial predictions in session")
        except Exception as e:
            print(f"Failed to store multinomial predictions: {e}")
    else:
        print("DEBUG: No multinomial predictions to store")
    
    sess.save()
    
    # Track this analysis iteration in session history
    try:
        iteration_type = 'update' if action == 'update' and session_id else 'initial'
        plots_added = []  # Will be populated when plots are added
        
        # Prepare results data with table information
        results_with_tables = results.copy()
        results_with_tables['model_cols'] = cols
        results_with_tables['model_matrix'] = model_table_matrix
        
        track_session_iteration(
            session_id=sess.id,
            iteration_type=iteration_type,
            equation=formula,
            analysis_type=analysis_type,
            results_data=results_with_tables,
            plots_added=plots_added,
            modifications={
                'module': module_name,
                'options': {k: v for k, v in options.items() if k not in ['draws', 'tune', 'chains', 'cores', 'prior']}
            },
            notes=f"Analysis completed successfully with {module_name} module"
        )
    except Exception as e:
        print(f"Failed to track session history: {e}")
    
    return sess


def _prepare_template_context(sess, dataset, results, cols, model_table_matrix, estimate_col_index, options):
    """
    Prepare template context dictionary.
    
    Returns:
        dict: Template context
    """
    import json
    
    # Get dataset columns for help text
    try:
        user_id = dataset.user.id if dataset.user else None
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=user_id)
        dataset_columns = list(df.columns)
        print(f"DEBUG: Dataset columns after update: {dataset_columns}")
        print(f"DEBUG: Summary stats keys: {list(results.get('summary_stats', {}).keys())}")
        print(f"DEBUG: Continuous vars: {results.get('continuous_vars', [])}")
        
        # Extract DV categories for ordinal regression
        dv_categories = []
        if 'Ordinal regression' in results.get('regression_type', ''):
            # Parse formula to get dependent variable
            formula = sess.formula
            if '~' in formula:
                dv = formula.split('~')[0].strip()
                if dv in df.columns:
                    dv_categories = sorted(df[dv].dropna().unique().tolist())
                    print(f"DEBUG: DV categories for ordinal regression: {dv_categories}")
        
        # Extract DV categories for multinomial regression
        multinomial_categories = []
        if 'Multinomial regression' in results.get('regression_type', ''):
            # Parse formula to get dependent variable
            formula = sess.formula
            if '~' in formula:
                dv = formula.split('~')[0].strip()
                if dv in df.columns:
                    multinomial_categories = sorted(df[dv].dropna().unique().tolist())
                    print(f"DEBUG: DV categories for multinomial regression: {multinomial_categories}")
    except Exception:
        dataset_columns = []
        dv_categories = []
        multinomial_categories = []
    
    print(f"DEBUG: regression_type from results: {results.get('regression_type', 'Not found')}")
    
    # DEBUG: Print template condition values
    print(f"DEBUG VIEWS: model_cols = {cols}")
    print(f"DEBUG VIEWS: model_matrix = {model_table_matrix}")
    print(f"DEBUG VIEWS: model_cols truthy = {bool(cols)}")
    print(f"DEBUG VIEWS: model_matrix truthy = {bool(model_table_matrix)}")
    print(f"DEBUG VIEWS: condition result = {bool(cols) and bool(model_table_matrix)}")
    
    ctx = {
        'session': sess,
        'dataset': dataset,
        'dataset_columns': dataset_columns,
        'dataset_columns_json': json.dumps(dataset_columns),
        **results,
        'model_cols': cols,
        'model_matrix': model_table_matrix,
        'estimate_col_index': estimate_col_index,
        'show_min': options.get('show_min', True),  # Default to True
        'show_max': options.get('show_max', True),  # Default to True
        'show_range': options.get('show_range', False),
        'show_variance': options.get('show_variance', False),
        'show_vif': options.get('show_vif', False),
        'summary_stats': results.get('summary_stats'),
        'summary_stats_json': json.dumps(results.get('summary_stats', {})),
        'interactions': results.get('interactions', []),
        'dv_categories': dv_categories,
        'dv_categories_json': json.dumps(dv_categories),
        'multinomial_categories': multinomial_categories,
        'multinomial_categories_json': json.dumps(multinomial_categories),
        'continuous_vars': results.get('continuous_vars', []),
        'continuous_vars_json': json.dumps(results.get('continuous_vars', [])),
        'all_numeric_vars': results.get('all_numeric_vars', []),
        'all_numeric_vars_json': json.dumps(results.get('all_numeric_vars', [])),
        'correlation_matrix': results.get('correlation_matrix', {}),
    }
    
    return ctx


def _determine_template(results, template_override, analysis_type):
    """
    Determine which template to use for rendering results.
    
    Returns:
        str: Template name
    """
    # Check if this is a multi-equation regression result
    print(f"=== TEMPLATE ROUTING DIAGNOSTICS ===")
    print(f"Results keys: {list(results.keys())}")
    print(f"is_multi_equation flag: {results.get('is_multi_equation')}")
    print(f"has_results flag: {results.get('has_results')}")
    if results.get('is_multi_equation'):
        template_name = 'engine/results_multi_regression.html'
        print(f"✓ ROUTING TO: results_multi_regression.html (multi-equation regression)")
        print(f"  Dependent vars: {results.get('dependent_vars', [])}")
        print(f"  RHS vars: {results.get('rhs_vars', [])}")
        print(f"  Grid data keys: {list(results.get('grid_data', {}).keys())}")
        print(f"  Equation results count: {len(results.get('equation_results', []))}")
        print(f"  Error: {results.get('error')}")
        print(f"=== END TEMPLATE ROUTING DIAGNOSTICS ===")
    elif template_override:
        template_name = f'engine/{template_override}.html'
        print(f"DEBUG: Using template override: {template_name}")
    elif analysis_type == 'bayesian':
        template_name = 'engine/bayesian_results.html'
        print(f"DEBUG: Rendering bayesian_results.html for analysis_type: {analysis_type}")
    else:
        template_name = 'engine/results.html'
        print(f"DEBUG: Rendering results.html for analysis_type: {analysis_type}")
    
    return template_name

