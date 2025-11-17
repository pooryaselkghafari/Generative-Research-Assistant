import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.api import VAR, VARMAX
from statsmodels.tools.eval_measures import aic, bic, mse, rmse
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import adfuller
import re
import plotly.graph_objects as go
from io import BytesIO
import base64
import warnings
warnings.filterwarnings("ignore")


def adf_check(series, name):
    """
    Perform the Augmented Dickey-Fuller test on a time series and return results.
    
    Parameters:
    - series: pd.Series - The time series data to be tested
    - name: str - The name of the time series (for labeling purposes)
    
    Returns:
    - dict: Dictionary containing test statistic, p-value, critical values, and stationarity status
    """
    try:
        # Drop NaN values before testing
        series_clean = series.dropna()
        
        if len(series_clean) < 4:  # Need at least 4 observations for ADF test
            return {
                'variable': name,
                'test_statistic': None,
                'p_value': None,
                'critical_value_1pct': None,
                'critical_value_5pct': None,
                'critical_value_10pct': None,
                'is_stationary': False,
                'error': 'Insufficient data (need at least 4 observations)'
            }
        
        # Perform ADF test
        result = adfuller(series_clean, autolag='AIC')
        
        # Extract results
        test_statistic = result[0]
        p_value = result[1]
        critical_values = result[4]
        
        # Determine stationarity (p-value < 0.05 indicates stationarity)
        # Ensure is_stationary is a Python bool, not numpy bool
        is_stationary = bool(p_value < 0.05)
        
        return {
            'variable': name,
            'test_statistic': float(test_statistic),
            'p_value': float(p_value),
            'critical_value_1pct': float(critical_values['1%']),
            'critical_value_5pct': float(critical_values['5%']),
            'critical_value_10pct': float(critical_values['10%']),
            'is_stationary': is_stationary,
            'interpretation': 'Stationary' if is_stationary else 'Non-stationary'
        }
    except Exception as e:
        return {
            'variable': name,
            'test_statistic': None,
            'p_value': None,
            'critical_value_1pct': None,
            'critical_value_5pct': None,
            'critical_value_10pct': None,
            'is_stationary': False,
            'error': str(e)
        }


class VARXModule:
    def run(self, df, formula, analysis_type=None, outdir=None, options=None, schema_types=None, schema_orders=None):
        """
        Run VARX (Vector Autoregression with Exogenous variables) analysis.
        
        Parameters:
        - df: DataFrame containing the data
        - formula: Formula string (e.g., "y1 + y2 ~ x1 + x2")
        - analysis_type: Not used in VARX
        - outdir: Output directory for results
        - options: Dictionary of analysis options (e.g., {'order': 2})
        - schema_types: Column type information
        - schema_orders: Column ordering information
        
        Returns:
        Dictionary with VARX results
        """
        
        # Parse the formula to extract dependent and independent variables
        if '~' not in formula:
            return {
                'error': 'Invalid formula format. Use "y1 + y2 ~ x1 + x2"',
                'has_results': False
            }
        
        # Split formula into dependent (endogenous) and independent (exogenous) variables
        parts = formula.split('~')
        dependent_vars_str = parts[0].strip()
        independent_vars_str = parts[1].strip()
        
        # Parse dependent variables (endogenous)
        dependent_vars = [v.strip() for v in dependent_vars_str.split('+')]
        
        # Parse independent variables (exogenous) - handle interactions
        # Interactions can be between:
        # 1. Exogenous variables (e.g., X1 * X2)
        # 2. Endogenous and exogenous variables (e.g., Y1 * X1)
        raw_independent_terms = [v.strip() for v in independent_vars_str.split('+')]
        independent_vars = []
        interaction_terms = []
        
        # Create working dataframe for interaction creation
        df_work = df.copy()
        
        # Process each term to handle interactions
        for term in raw_independent_terms:
            if '*' in term:
                # Interaction term (e.g., "Y * X2" or "X1 * X2")
                parts = [p.strip() for p in term.split('*') if p.strip()]
                if len(parts) >= 2:
                    # Check if all component variables exist in the dataset
                    missing_parts = [p for p in parts if p not in df.columns]
                    if missing_parts:
                        return {
                            'error': f'Variables not found in dataset for interaction {term}: {", ".join(str(p) for p in missing_parts)}',
                            'has_results': False
                        }
                    
                    # Check if any part is an endogenous variable
                    # If so, we'll use it as-is (no need to add to independent_vars separately)
                    # If all parts are exogenous, we can optionally add them individually
                    # For VARX, we typically only include the interaction term, not the individual components
                    # (unless they're also specified separately in the formula)
                    
                    # Create interaction variable name (use colon notation for consistency)
                    interaction_name = ':'.join(parts)
                    interaction_terms.append({
                        'name': interaction_name,
                        'parts': parts,
                        'original': term
                    })
                    # Add interaction to independent vars (this is the new exogenous regressor)
                    if interaction_name not in independent_vars:
                        independent_vars.append(interaction_name)
            else:
                # Simple variable (no interaction)
                # Only add if it's not already in dependent_vars (endogenous variables)
                if term not in dependent_vars:
                    independent_vars.append(term)
        
        # Check if base variables exist in the dataset (before creating interactions)
        # For interactions, we only need to check the parts, not the interaction name itself
        # Note: We need to check both original variable names AND their stationary versions
        all_base_vars = dependent_vars + [v for v in independent_vars if ':' not in v]
        missing_vars = []
        for v in all_base_vars:
            # Check if variable exists, or if its stationary version exists
            stationary_v = f'{v}_stationary'
            if v not in df.columns and stationary_v not in df.columns:
                missing_vars.append(str(v))  # Ensure it's a string
        if missing_vars:
            return {
                'error': f'Variables not found in dataset: {", ".join(missing_vars)}',
                'has_results': False
            }
        
        # Create interaction variables in the dataframe
        # This treats interactions as additional exogenous regressors (as per VARX best practices)
        for interaction in interaction_terms:
            interaction_name = interaction['name']
            parts = interaction['parts']
            
            # Check if all parts are numeric (required for multiplication)
            all_numeric = all(pd.api.types.is_numeric_dtype(df_work[p]) for p in parts if p in df_work.columns)
            
            if all_numeric:
                # Create interaction by multiplying component variables
                # This works for:
                # - Exogenous * Exogenous (e.g., X1 * X2)
                # - Endogenous * Exogenous (e.g., Y1 * X1) - uses current values
                interaction_value = df_work[parts[0]].copy()
                for part in parts[1:]:
                    interaction_value = interaction_value * df_work[part]
                df_work[interaction_name] = interaction_value
                print(f"DEBUG: Created interaction term {interaction_name} = {' * '.join(parts)}")
            else:
                # At least one part is not numeric - can't multiply
                return {
                    'error': f'Cannot create interaction {interaction["original"]}: all component variables must be numeric',
                    'has_results': False
                }
        
        # Filter to only numeric variables
        # Use df_work which includes interaction terms
        # If a {var}_stationary column exists, use that instead of the original variable
        numeric_dependent_vars = []
        var_mapping = {}  # Map original var name to actual column name used
        
        for var in dependent_vars:
            # Check if a stationary version of this variable exists
            stationary_var_name = f'{var}_stationary'
            var_to_use = var
            
            if stationary_var_name in df_work.columns:
                # Check if the stationary column is constant (can happen after log transformation)
                stationary_col = df_work[stationary_var_name].dropna()
                if len(stationary_col) > 0:
                    unique_values = stationary_col.unique()
                    if len(unique_values) <= 1:
                        # Column is constant - don't use it, use original variable instead
                        print(f"DEBUG: Stationary column '{stationary_var_name}' is constant (all values are the same). Skipping it and using original variable '{var}' instead.")
                        # var_to_use remains as var (original variable)
                    else:
                        # Use the stationary version if it exists and is not constant
                        var_to_use = stationary_var_name
                        var_mapping[var] = stationary_var_name
                        print(f"DEBUG: Found stationary column '{stationary_var_name}', using it for VARX model instead of '{var}'")
            
            if var_to_use in df_work.columns:
                # Check if numeric, or try to convert
                if pd.api.types.is_numeric_dtype(df_work[var_to_use]):
                    numeric_dependent_vars.append(var_to_use)
                    var_mapping[var] = var_to_use
                else:
                    # Try to convert to numeric
                    try:
                        df_work[var_to_use] = pd.to_numeric(df_work[var_to_use], errors='coerce')
                        if pd.api.types.is_numeric_dtype(df_work[var_to_use]):
                            numeric_dependent_vars.append(var_to_use)
                            var_mapping[var] = var_to_use
                    except:
                        pass
        
        # For VARX, we need to handle categorical variables properly
        # Binary variables: convert to 0/1
        # Multi-category variables: use dummy/one-hot encoding (drop_first=True)
        numeric_independent_vars = []
        dummy_encoded_vars = {}  # Track which variables were dummy encoded and their new column names
        
        for var in independent_vars:
            # Check in df_work (which has interaction terms) or df (for base variables)
            check_df = df_work if var in df_work.columns else df
            if var in check_df.columns:
                # Check if numeric
                if pd.api.types.is_numeric_dtype(check_df[var]):
                    numeric_independent_vars.append(var)
                else:
                    # Try to convert to numeric (for binary/categorical variables)
                    try:
                        if var in df_work.columns:
                            # Check if it's categorical/binary
                            if check_df[var].dtype.name == 'category' or check_df[var].dtype == 'object':
                                n_unique = check_df[var].nunique()
                                
                                if n_unique <= 2:
                                    # Binary variable - convert to 0/1
                                    unique_vals = check_df[var].dropna().unique()
                                    if len(unique_vals) == 2:
                                        mapping = {unique_vals[0]: 0, unique_vals[1]: 1}
                                        df_work[var] = check_df[var].map(mapping)
                                    else:
                                        df_work[var] = (check_df[var] == unique_vals[0]).astype(int)
                                    
                                    # Fill NaN with 0 for binary
                                    df_work[var] = df_work[var].fillna(0)
                                    
                                    if pd.api.types.is_numeric_dtype(df_work[var]):
                                        numeric_independent_vars.append(var)
                                        print(f"DEBUG: Converted binary '{var}' to 0/1")
                                else:
                                    # Multi-category variable - use dummy/one-hot encoding
                                    # This is required for VAR models (cannot use numeric codes)
                                    print(f"DEBUG: Converting categorical '{var}' ({n_unique} categories) to dummy variables")
                                    
                                    # Get unique category values for better naming
                                    unique_cats = sorted(check_df[var].dropna().unique())
                                    print(f"DEBUG: Categories in '{var}': {unique_cats}")
                                    
                                    # Create dummy variables (drop_first=True to avoid multicollinearity)
                                    # This creates columns like var_category1, var_category2, etc.
                                    dummies = pd.get_dummies(check_df[var], prefix=var, drop_first=True, dummy_na=False)
                                    
                                    # Rename dummy columns to be more descriptive
                                    # Original names are like "var_category1", we want "var: category1"
                                    # Or better: use the actual category value in the name
                                    dummy_cols_renamed = {}
                                    dummy_cols_list = []
                                    
                                    # Get the reference category (first one, which is dropped)
                                    reference_cat = unique_cats[0] if len(unique_cats) > 0 else None
                                    
                                    # Rename each dummy column to include the actual category value
                                    for i, dummy_col in enumerate(dummies.columns):
                                        # Extract the category value from the column name
                                        # pd.get_dummies creates names like "var_Value" or "var_0", "var_1"
                                        # We want to preserve the actual category value
                                        if '_' in dummy_col:
                                            # Split on underscore, take everything after the prefix
                                            parts = dummy_col.split('_', 1)
                                            if len(parts) == 2:
                                                cat_value = parts[1]
                                                # Create a more readable name: "var: category_value"
                                                new_name = f"{var}: {cat_value}"
                                            else:
                                                new_name = dummy_col
                                        else:
                                            new_name = dummy_col
                                        
                                        dummy_cols_renamed[dummy_col] = new_name
                                        dummy_cols_list.append(new_name)
                                    
                                    # Rename the dummy columns
                                    dummies_renamed = dummies.rename(columns=dummy_cols_renamed)
                                    
                                    # Add dummy columns to df_work with new names
                                    for new_col_name in dummy_cols_list:
                                        old_col_name = [k for k, v in dummy_cols_renamed.items() if v == new_col_name][0]
                                        df_work[new_col_name] = dummies_renamed[new_col_name]
                                        numeric_independent_vars.append(new_col_name)
                                    
                                    # Track which original variable was encoded
                                    dummy_encoded_vars[var] = {
                                        'dummy_columns': dummy_cols_list,
                                        'reference_category': reference_cat,
                                        'all_categories': unique_cats
                                    }
                                    
                                    # Remove original categorical column from df_work
                                    if var in df_work.columns:
                                        df_work = df_work.drop(columns=[var])
                                    
                                    print(f"DEBUG: Created {len(dummy_cols_list)} dummy variables for '{var}': {dummy_cols_list}")
                                    print(f"DEBUG: Reference category (dropped): {reference_cat}")
                            else:
                                # Try direct numeric conversion
                                df_work[var] = pd.to_numeric(check_df[var], errors='coerce')
                                
                                if pd.api.types.is_numeric_dtype(df_work[var]):
                                    numeric_independent_vars.append(var)
                                    print(f"DEBUG: Converted '{var}' to numeric for VARX")
                    except Exception as e:
                        print(f"DEBUG: Could not convert '{var}' to numeric: {e}")
                        import traceback
                        traceback.print_exc()
                        pass
        
        # Check for constant stationary columns and report them
        # This check happens after variable selection to catch cases where log transformation resulted in constant values
        # We'll show a warning popup but continue with original variables
        constant_stationary_vars = []
        for var in dependent_vars:
            stationary_var_name = f'{var}_stationary'
            if stationary_var_name in df_work.columns:
                stationary_col = df_work[stationary_var_name].dropna()
                if len(stationary_col) > 0:
                    unique_values = stationary_col.unique()
                    if len(unique_values) <= 1:
                        constant_stationary_vars.append(var)
                        print(f"DEBUG: Stationary column '{stationary_var_name}' is constant. Will use original variable '{var}' instead.")
        
        if not numeric_dependent_vars:
            return {
                'error': 'No numeric dependent variables found in the equation.',
                'has_results': False
            }
        
        if not numeric_independent_vars:
            return {
                'error': 'No numeric independent (exogenous) variables found in the equation.',
                'has_results': False
            }
        
        # Check stationarity of endogenous variables using ADF test
        # If a {var}_stationary column exists and is not constant, use that instead of the original variable
        stationarity_results = []
        # Use dependent_vars (original names) for display, but check what column is actually being used
        for orig_var in dependent_vars:
            # Get the actual column name being used (from var_mapping or original)
            actual_col = var_mapping.get(orig_var, orig_var)
            
            # Check if a stationary version exists and if it's constant
            stationary_var_name = f'{orig_var}_stationary'
            var_to_test = orig_var
            
            if stationary_var_name in df_work.columns:
                # Check if stationary column is constant
                stationary_col = df_work[stationary_var_name].dropna()
                if len(stationary_col) > 0:
                    unique_values = stationary_col.unique()
                    if len(unique_values) > 1:
                        # Stationary column exists and is not constant - use it
                        var_to_test = stationary_var_name
                        print(f"DEBUG: Found stationary column '{stationary_var_name}', using it for ADF test")
                    else:
                        # Stationary column is constant - use original variable
                        print(f"DEBUG: Stationary column '{stationary_var_name}' is constant, using original variable '{orig_var}' for ADF test")
            
            if var_to_test in df_work.columns:
                adf_result = adf_check(df_work[var_to_test], var_to_test)
                # Update the variable name in the result to show the original variable name
                # but indicate if it's using the transformed version
                adf_result['variable'] = orig_var  # Original variable name for display
                adf_result['tested_column'] = var_to_test  # Column actually tested
                adf_result['is_transformed'] = (var_to_test != orig_var)  # Whether using transformed column
                stationarity_results.append(adf_result)
            else:
                # Variable not found in dataframe
                stationarity_results.append({
                    'variable': orig_var,
                    'test_statistic': None,
                    'p_value': None,
                    'critical_value_1pct': None,
                    'critical_value_5pct': None,
                    'critical_value_10pct': None,
                    'is_stationary': False,
                    'error': 'Variable not found in dataset',
                    'tested_column': orig_var,
                    'is_transformed': False
                })
        
        # Get VAR order from options
        # If var_order is not specified or is 0, use automatic lag selection
        var_order = options.get('var_order', None) if options else None
        print(f"DEBUG: VARX.run received var_order option: {var_order}")
        use_auto_lag_selection = False
        max_lags_to_test = options.get('max_lags', 10) if options else 10  # Default to 10, user can change
        print(f"DEBUG: VARX.run initial max_lags_to_test: {max_lags_to_test}")
        
        # Always get max_lags from options (for lag selection table)
        try:
            max_lags_to_test = int(max_lags_to_test)
        except (ValueError, TypeError):
            max_lags_to_test = 10
        
        # Check if a manual lag order was provided
        # If var_order is a valid integer (not None, 0, or 'auto'), use it as manual selection
        manual_lag_provided = False
        if var_order is not None and var_order != 0 and var_order != 'auto':
            try:
                var_order = int(var_order)
                if var_order > 0:  # Valid positive integer
                    use_auto_lag_selection = False
                    manual_lag_provided = True
                    print(f"DEBUG: Manual lag order provided: {var_order}")
            except (ValueError, TypeError):
                # Invalid value, fall back to auto-selection
                var_order = None
                use_auto_lag_selection = True
        
        if not manual_lag_provided:
            # No valid manual lag provided, use auto-selection
            use_auto_lag_selection = True
            var_order = None  # Will be determined by auto-selection
            print("DEBUG: No manual lag provided. Auto-selection enabled.")
        
        # Prepare data - drop NaN values
        # Use df_work which has interaction terms created
        endog_data = df_work[numeric_dependent_vars].copy()
        exog_data = df_work[numeric_independent_vars].copy()
        
        # Convert to float64 BEFORE dropping NaN to ensure consistent alignment
        # VAR requires float64 for proper calculations
        for col in endog_data.columns:
            endog_data[col] = pd.to_numeric(endog_data[col], errors='coerce').astype('float64')
        
        for col in exog_data.columns:
            exog_data[col] = pd.to_numeric(exog_data[col], errors='coerce').astype('float64')
        
        # Drop rows with any NaN in endogenous OR exogenous variables
        # This ensures both endog and exog have the same number of rows
        valid_mask = ~(endog_data.isna().any(axis=1) | exog_data.isna().any(axis=1))
        endog_clean = endog_data[valid_mask].copy()
        exog_clean = exog_data[valid_mask].copy()
        
        # Verify alignment
        if len(endog_clean) != len(exog_clean):
            return {
                'error': f'Data alignment error: endogenous variables have {len(endog_clean)} rows, but exogenous variables have {len(exog_clean)} rows. This should not happen.',
                'has_results': False
            }
        
        print(f"DEBUG: After cleaning - endog shape: {endog_clean.shape}, exog shape: {exog_clean.shape}")
        
        # Adjust max_lags if dataset is too small
        # Rule: if dataset has less than (max_lags * 3) observations, reduce max_lags to 5
        # This ensures we have enough data for reliable lag selection
        dataset_size = len(endog_clean)
        if max_lags_to_test > 5 and dataset_size < (max_lags_to_test * 3):
            print(f"DEBUG: Dataset size ({dataset_size}) is too small for max_lags={max_lags_to_test}. Reducing to 5.")
            max_lags_to_test = 5
        
        # Check if we have enough data (need at least max_lags_to_test + 1 if auto-selecting, or var_order + 1 if fixed)
        min_required = (max_lags_to_test if use_auto_lag_selection else var_order) + 1
        if len(endog_clean) < min_required:
            return {
                'error': f'Insufficient data. Need at least {min_required} observations, but only have {len(endog_clean)}.',
                'has_results': False
            }
        
        try:
            # Fit VARX model
            # Ensure data is explicitly float64 for VARMAX
            # Debug: Check what we're passing to VARMAX
            print(f"DEBUG: Endogenous variables shape: {endog_clean.shape}")
            print(f"DEBUG: Endogenous variables columns: {list(endog_clean.columns)}")
            print(f"DEBUG: Exogenous variables shape: {exog_clean.shape}")
            print(f"DEBUG: Exogenous variables columns: {list(exog_clean.columns)}")
            print(f"DEBUG: VAR order: {var_order}")
            
            # Check if we have any exogenous variables
            if exog_clean.empty or len(exog_clean.columns) == 0:
                print("WARNING: No exogenous variables to pass to VARX!")
                return {
                    'error': 'No exogenous variables available for the model. Please check that Y and Gender are numeric variables.',
                    'has_results': False
                }
            
            # Check for constant columns in endogenous variables (can happen after diff transformation)
            constant_endog_cols = []
            for col in endog_clean.columns:
                # Check if column has constant values (all same or all NaN)
                unique_non_nan = endog_clean[col].dropna().unique()
                if len(unique_non_nan) <= 1:
                    constant_endog_cols.append(col)
            
            if constant_endog_cols:
                # Check if these are stationary columns (from diff transformation)
                stationary_cols = [col for col in constant_endog_cols if col.endswith('_stationary')]
                if stationary_cols:
                    original_vars = [col.replace('_stationary', '') for col in stationary_cols]
                    return {
                        'error': f'After applying the difference transformation, the following variables became constant (all values are the same): {", ".join(original_vars)}. This typically happens when the original variable had no variation or when differencing removes all variation. Please try a different transformation (e.g., log transformation) or use the original variables if they are already stationary.',
                        'has_results': False
                    }
                else:
                    return {
                        'error': f'The following endogenous variables are constant (all values are the same): {", ".join(constant_endog_cols)}. VAR models require variables with variation. Please check your data or try a different transformation.',
                        'has_results': False
                    }
            
            # Check for constant columns in exogenous variables
            constant_exog_cols = []
            for col in exog_clean.columns:
                # Check if column has constant values (all same or all NaN)
                unique_non_nan = exog_clean[col].dropna().unique()
                if len(unique_non_nan) <= 1:
                    constant_exog_cols.append(col)
            
            if constant_exog_cols:
                return {
                    'error': f'The following exogenous variables are constant (all values are the same): {", ".join(constant_exog_cols)}. VAR models require variables with variation. Please check your data.',
                    'has_results': False
                }
            
            # Use VAR instead of VARMAX for pure VARX models (VAR is designed for VARX)
            # VAR returns params as DataFrame which is easier to work with
            # VARMAX is for VARMA models (with MA terms), VAR is for pure VAR/VARX
            
            # Ensure both are aligned and have same index
            # Reset index to ensure alignment
            endog_clean = endog_clean.reset_index(drop=True)
            exog_clean = exog_clean.reset_index(drop=True)
            
            # Final check before passing to VAR
            if len(endog_clean) != len(exog_clean):
                return {
                    'error': f'Data alignment error before VAR fitting: endogenous variables have {len(endog_clean)} rows, but exogenous variables have {len(exog_clean)} rows.',
                    'has_results': False
                }
            
            print(f"DEBUG: Final data shapes before VAR - endog: {endog_clean.shape}, exog: {exog_clean.shape}")
            
            # Ensure both are float64
            endog_clean = endog_clean.astype('float64')
            exog_clean = exog_clean.astype('float64')
            
            # Initialize VAR model (without exog for lag selection)
            # Note: select_order() only works with endogenous variables
            model = VAR(endog_clean)
            
            # Perform automatic lag selection (always do it to show the table)
            lag_selection_results = None
            lag_selection_table = []
            
            # Always perform lag selection to show the comparison table
            # This helps users see which lag is optimal even if they specified a manual lag
            # Always use max_lags_to_test (user's setting) for the table, regardless of auto-selection
            max_lags_for_table = max_lags_to_test
            
            print(f"DEBUG: Creating lag selection table (testing up to {max_lags_for_table} lags)")
            
            # Use the simpler approach: fit model for each lag and collect AIC/BIC/HQIC/LL
            # This is more reliable than using select_order() which may not work with exog
            # Always generate the table, even if select_order fails
            
            # Try to get optimal lags using select_order (without exog, for reference)
            # But don't fail if this doesn't work - we'll determine optimal from the table itself
            lag_selection_results = None
            try:
                lag_selection = model.select_order(maxlags=max_lags_for_table, verbose=False)
                lag_selection_results = {
                    'aic': lag_selection.aic,
                    'bic': lag_selection.bic,
                    'fpe': lag_selection.fpe if hasattr(lag_selection, 'fpe') else None,
                    'hqic': lag_selection.hqic if hasattr(lag_selection, 'hqic') else None
                }
                print(f"DEBUG: Got optimal lags from select_order: AIC={lag_selection_results['aic']}, BIC={lag_selection_results['bic']}")
            except Exception as e:
                print(f"DEBUG: select_order failed (this is OK, we'll determine optimal from table): {e}")
                lag_selection_results = None
            
            # Now fit models with exog for each lag to get the full table
            # Fit VARX model for each lag and collect AIC/BIC/HQIC/LL
            print(f"DEBUG: Fitting VARX models for lags 1 to {max_lags_for_table}")
            aic_values = []
            bic_values = []
            hqic_values = []
            
            for lag in range(1, max_lags_for_table + 1):
                try:
                    # Fit VARX model with exogenous variables
                    temp_model = VAR(endog_clean, exog=exog_clean)
                    fitted = temp_model.fit(lag, verbose=False)
                    
                    aic_val = fitted.aic
                    bic_val = fitted.bic
                    hqic_val = fitted.hqic if hasattr(fitted, 'hqic') else None
                    ll_val = fitted.llf
                    
                    aic_values.append((lag, aic_val))
                    bic_values.append((lag, bic_val))
                    if hqic_val is not None:
                        hqic_values.append((lag, hqic_val))
                    
                    # Mark optimal lags (use select_order results if available, otherwise determine from table)
                    if lag_selection_results:
                        is_aic_optimal = (lag == lag_selection_results['aic'])
                        is_bic_optimal = (lag == lag_selection_results['bic'])
                        is_fpe_optimal = (lag == lag_selection_results['fpe']) if lag_selection_results['fpe'] else False
                        is_hqic_optimal = (lag == lag_selection_results['hqic']) if lag_selection_results['hqic'] else False
                    else:
                        # Determine optimal from the values we collect (will be set after loop)
                        is_aic_optimal = False
                        is_bic_optimal = False
                        is_fpe_optimal = False
                        is_hqic_optimal = False
                    
                    lag_selection_table.append({
                        'lag': lag,
                        'aic': aic_val,
                        'bic': bic_val,
                        'hqic': hqic_val,
                        'log_likelihood': ll_val,
                        'aic_optimal': is_aic_optimal,
                        'bic_optimal': is_bic_optimal,
                        'fpe_optimal': is_fpe_optimal,
                        'hqic_optimal': is_hqic_optimal
                    })
                    print(f"DEBUG: Lag {lag}: AIC={aic_val:.4f}, BIC={bic_val:.4f}, HQIC={hqic_val if hqic_val else 'N/A'}, LL={ll_val:.4f}")
                except Exception as e:
                    print(f"DEBUG: Could not fit VARX model at lag {lag}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Add row with None values
                    lag_selection_table.append({
                        'lag': lag,
                        'aic': None,
                        'bic': None,
                        'hqic': None,
                        'log_likelihood': None,
                        'aic_optimal': False,
                        'bic_optimal': False,
                        'fpe_optimal': False,
                        'hqic_optimal': False
                    })
                    continue
            
            # If select_order failed, determine optimal lags from the table
            if not lag_selection_results and len(aic_values) > 0:
                # Find optimal lags (minimum AIC, BIC, HQIC)
                optimal_aic_lag = min(aic_values, key=lambda x: x[1])[0] if aic_values else None
                optimal_bic_lag = min(bic_values, key=lambda x: x[1])[0] if bic_values else None
                optimal_hqic_lag = min(hqic_values, key=lambda x: x[1])[0] if hqic_values and len(hqic_values) > 0 else None
                
                lag_selection_results = {
                    'aic': optimal_aic_lag,
                    'bic': optimal_bic_lag,
                    'fpe': None,
                    'hqic': optimal_hqic_lag
                }
                
                # Update optimal flags in the table
                for row in lag_selection_table:
                    if row['lag'] == optimal_aic_lag:
                        row['aic_optimal'] = True
                    if row['lag'] == optimal_bic_lag:
                        row['bic_optimal'] = True
                    if row['lag'] == optimal_hqic_lag and optimal_hqic_lag:
                        row['hqic_optimal'] = True
            
            # Choose best lag by AIC (most common criterion) only if auto-selection was requested
            # IMPORTANT: If manual_lag_provided is True, we MUST use that lag and NOT override it
            if manual_lag_provided:
                # User manually selected a lag - use it exactly as provided
                # var_order is already set to the manual value, just ensure it's an integer
                try:
                    var_order = int(var_order)
                except (ValueError, TypeError):
                    var_order = 1  # Fallback if conversion fails
                print(f"DEBUG: Using manually specified lag order: {var_order} (NOT auto-selected)")
                use_auto_lag_selection = False  # Ensure this is False when manual lag is used
            elif use_auto_lag_selection and lag_selection_results and lag_selection_results.get('aic'):
                var_order = lag_selection_results['aic']
                print(f"DEBUG: Optimal lag order selected: {var_order} (by AIC - auto-selected)")
            elif use_auto_lag_selection:
                # Auto-selection failed or no results - use default lag of 1
                var_order = 1
                print(f"DEBUG: Auto-selection failed, using default lag order: {var_order}")
            else:
                # Fallback: should not happen, but ensure var_order is set
                try:
                    var_order = int(var_order) if var_order is not None else 1
                except (ValueError, TypeError):
                    var_order = 1
                print(f"DEBUG: Using lag order: {var_order} (fallback)")
            
            # Final check: Ensure var_order is an integer (not string or None)
            try:
                var_order = int(var_order)
            except (ValueError, TypeError):
                var_order = 1  # Default to lag 1 if conversion fails
            print(f"DEBUG: Final var_order used for model fitting: {var_order} (auto={use_auto_lag_selection}, manual={manual_lag_provided})")
            
            if lag_selection_results:
                print(f"DEBUG: Lag selection results - AIC: {lag_selection_results.get('aic')}, BIC: {lag_selection_results.get('bic')}, HQIC: {lag_selection_results.get('hqic')}")
            
            print(f"DEBUG: Lag selection table has {len(lag_selection_table)} rows")
            
            print(f"DEBUG: Fitting VAR model with order={var_order}, {len(exog_clean.columns)} exogenous variables")
            
            # Fit VARX model with exogenous variables using the selected lag order
            # VAR will handle lagging internally, but endog and exog must have same length
            model = VAR(endog_clean, exog=exog_clean)
            results = model.fit(maxlags=var_order, verbose=False)
            
            # Debug: Check what parameters VAR returned
            print(f"DEBUG: VAR fitted successfully")
            print(f"DEBUG: Results params type: {type(results.params)}")
            if isinstance(results.params, pd.DataFrame):
                print(f"DEBUG: Params DataFrame shape: {results.params.shape}")
                print(f"DEBUG: Params columns (equations): {list(results.params.columns)}")
                print(f"DEBUG: Params index (variables): {list(results.params.index)[:20]}...")  # First 20
            else:
                print(f"DEBUG: Number of parameters: {len(results.params)}")
                print(f"DEBUG: Parameter names: {list(results.params.index)[:20]}...")  # First 20
            
            # Compute diagnostic tests
            print(f"DEBUG: Computing diagnostic tests...")
            diagnostics = {}
            
            try:
                # Durbin-Watson test for autocorrelation
                dw_stats = durbin_watson(results.resid)
                if isinstance(dw_stats, np.ndarray) and len(dw_stats) == len(numeric_dependent_vars):
                    for i, var in enumerate(numeric_dependent_vars):
                        diagnostics[f"Durbin-Watson ({var})"] = float(dw_stats[i])
                elif isinstance(dw_stats, (int, float)):
                    diagnostics["Durbin-Watson"] = float(dw_stats)
                else:
                    # If it's a Series or other format
                    dw_dict = dict(zip(numeric_dependent_vars, dw_stats))
                    for var, dw_val in dw_dict.items():
                        diagnostics[f"Durbin-Watson ({var})"] = float(dw_val)
            except Exception as e:
                print(f"DEBUG: Could not compute Durbin-Watson test: {e}")
            
            try:
                # Normality test (Jarque-Bera)
                jb_test = results.test_normality()
                diagnostics["JB Statistic"] = float(jb_test.statistic) if hasattr(jb_test, 'statistic') else None
                diagnostics["JB p-value"] = float(jb_test.pvalue) if hasattr(jb_test, 'pvalue') else None
            except Exception as e:
                print(f"DEBUG: Could not compute Jarque-Bera test: {e}")
            
            try:
                # Serial correlation test (Portmanteau LM test)
                sc_test = results.test_serial_correlation(lags=var_order)
                diagnostics["SerialCorr Statistic"] = float(sc_test.statistic) if hasattr(sc_test, 'statistic') else None
                diagnostics["SerialCorr p-value"] = float(sc_test.pvalue) if hasattr(sc_test, 'pvalue') else None
            except Exception as e:
                print(f"DEBUG: Could not compute serial correlation test: {e}")
            
            try:
                # Stability check (roots should be < 1)
                roots = np.abs(results.roots)
                stable = bool(np.all(roots < 1))
                diagnostics["Stable System?"] = "Yes" if stable else "No"
                diagnostics["Max Root Modulus"] = float(np.max(roots))
            except Exception as e:
                print(f"DEBUG: Could not compute stability check: {e}")
            
            # Extract model fit statistics
            fit_stats = {
                "AIC": results.aic,
                "BIC": results.bic,
                "HQIC": results.hqic if hasattr(results, 'hqic') else None,
                "FPE": results.fpe if hasattr(results, 'fpe') else None,
                "Log-Likelihood": results.llf,
            }
            
            # Calculate MSE and RMSE for each dependent variable
            # Note: VAR's fittedvalues will have fewer rows than original data
            # because VAR drops the first var_order rows when creating lags
            fitted_values = results.fittedvalues
            print(f"DEBUG: fitted_values shape: {fitted_values.shape}, endog_clean shape: {endog_clean.shape}")
            
            # Align actual values with fitted values
            # VAR drops the first var_order rows, so we need to drop those from actual too
            # Or use the index from fitted_values to align
            if hasattr(fitted_values, 'index') and len(fitted_values) < len(endog_clean):
                # Get the actual values corresponding to the fitted values
                # VAR's fittedvalues index should align with endog_clean after dropping initial rows
                # We need to drop the first var_order rows from endog_clean to match fitted_values
                actual_aligned = endog_clean.iloc[var_order:].copy()  # Drop first var_order rows
                # Reset index to ensure alignment
                actual_aligned = actual_aligned.reset_index(drop=True)
                fitted_values_aligned = fitted_values.reset_index(drop=True)
                
                print(f"DEBUG: After alignment - actual_aligned shape: {actual_aligned.shape}, fitted_values_aligned shape: {fitted_values_aligned.shape}")
            else:
                # If shapes match, use as-is
                actual_aligned = endog_clean.copy()
                fitted_values_aligned = fitted_values.copy()
            
            for i, var in enumerate(numeric_dependent_vars):
                if var in fitted_values_aligned.columns and var in actual_aligned.columns:
                    # Ensure both are float64 for calculation
                    actual = actual_aligned[var].astype('float64')
                    fitted = fitted_values_aligned[var].astype('float64')
                    
                    # Final check - ensure same length
                    if len(actual) != len(fitted):
                        min_len = min(len(actual), len(fitted))
                        actual = actual.iloc[:min_len]
                        fitted = fitted.iloc[:min_len]
                        print(f"WARNING: Truncated {var} to length {min_len} for MSE calculation")
                    
                    fit_stats[f"MSE ({var})"] = mse(actual, fitted)
                    fit_stats[f"RMSE ({var})"] = rmse(actual, fitted)
                else:
                    print(f"WARNING: Variable {var} not found in fitted_values or actual_aligned")
            
            # Convert fit stats to list of dicts for table display
            fit_table_rows = []
            for key, value in fit_stats.items():
                if value is not None:
                    fit_table_rows.append({
                        'Statistic': key,
                        'Value': f'{value:.4f}' if isinstance(value, (int, float)) else str(value)
                    })
            
            # Helper function to interpret diagnostic results
            def _interpret_diagnostic(test_name, value):
                """Provide interpretation for diagnostic test results"""
                test_lower = test_name.lower()
                
                if 'durbin-watson' in test_lower:
                    if isinstance(value, (int, float)):
                        if 1.5 < value < 2.5:
                            return "No autocorrelation (good)"
                        elif value <= 1.5:
                            return "Positive autocorrelation (concern)"
                        else:
                            return "Negative autocorrelation (concern)"
                    return ""
                
                elif 'jb' in test_lower and 'p-value' in test_lower:
                    if isinstance(value, (int, float)):
                        if value > 0.05:
                            return "Residuals are normal (p > 0.05)"
                        else:
                            return "Residuals not normal (p ≤ 0.05)"
                    return ""
                
                elif 'serialcorr' in test_lower and 'p-value' in test_lower:
                    if isinstance(value, (int, float)):
                        if value > 0.05:
                            return "No serial correlation (p > 0.05)"
                        else:
                            return "Serial correlation present (p ≤ 0.05)"
                    return ""
                
                elif 'stable' in test_lower:
                    if value == "Yes":
                        return "System is stable"
                    else:
                        return "System may be unstable"
                
                elif 'root' in test_lower:
                    if isinstance(value, (int, float)):
                        if value < 1:
                            return "Stable (all roots < 1)"
                        else:
                            return "Unstable (some roots ≥ 1)"
                    return ""
                
                return ""
            
            # Convert diagnostics to list of dicts for table display
            diagnostics_table_rows = []
            for key, value in diagnostics.items():
                if value is not None:
                    if isinstance(value, (int, float)):
                        # Format numbers appropriately
                        if 'p-value' in key.lower():
                            # Format p-values with more precision
                            diagnostics_table_rows.append({
                                'Test': key,
                                'Value': f'{value:.6f}',
                                'Interpretation': _interpret_diagnostic(key, value)
                            })
                        else:
                            diagnostics_table_rows.append({
                                'Test': key,
                                'Value': f'{value:.4f}',
                                'Interpretation': _interpret_diagnostic(key, value)
                            })
                    else:
                        diagnostics_table_rows.append({
                            'Test': key,
                            'Value': str(value),
                            'Interpretation': _interpret_diagnostic(key, value)
                        })
            
            # Extract coefficients - VAR returns params as DataFrame
            # Columns are equations (dependent variables), rows are parameters
            if isinstance(results.params, pd.DataFrame):
                coef_table = results.params
                # VAR returns params as DataFrame: rows = parameters, columns = equations
                # We need to transpose our thinking - each column is an equation
                print(f"DEBUG: VAR params DataFrame - columns (equations): {list(coef_table.columns)}")
                print(f"DEBUG: VAR params DataFrame - index (parameters): {list(coef_table.index)}")
            else:
                # Fallback for Series format (shouldn't happen with VAR)
                coef_table = results.params
            
            # Get standard errors, t-values, and p-values
            # VAR returns these as DataFrames too
            if hasattr(results, 'stderr') and isinstance(results.stderr, pd.DataFrame):
                std_errors = results.stderr
            elif hasattr(results, 'bse'):
                std_errors = results.bse
            else:
                std_errors = None
            
            if hasattr(results, 'tvalues') and isinstance(results.tvalues, pd.DataFrame):
                t_values = results.tvalues
            else:
                t_values = None
            
            if hasattr(results, 'pvalues') and isinstance(results.pvalues, pd.DataFrame):
                p_values = results.pvalues
            else:
                p_values = None
            
            # Helper function to get significance asterisks
            def get_significance(p_value):
                """Return significance asterisks based on p-value"""
                if pd.isna(p_value) or not np.isfinite(p_value):
                    return ""
                if p_value < 0.001:
                    return "***"
                elif p_value < 0.01:
                    return "**"
                elif p_value < 0.05:
                    return "*"
                else:
                    return ""
            
            # VAR returns params as DataFrame: rows = parameters, columns = equations (dependent variables)
            # Parameter names in VAR are like: 'const', 'X1.L1', 'X2.L1', 'X1.L2', 'X2.L2', 'Y', 'Gender'
            # Where .L1, .L2 indicate lags, and direct variable names are exogenous
            
            def parse_param_name(param_name, dependent_vars, independent_vars):
                """Parse VAR parameter name into readable format"""
                # Handle intercept
                if param_name == 'const':
                    return 'Intercept', None, 'intercept'  # Will be assigned to each equation
                
                # Handle lagged endogenous variables
                # VAR can use formats like:
                # - 'X1.L1' (var.lag format)
                # - 'L1.X1' (lag.var format)
                # Try both patterns
                lag_match = re.match(r'(.+?)\.L(\d+)$', param_name)  # X1.L1 format
                if not lag_match:
                    lag_match = re.match(r'L(\d+)\.(.+?)$', param_name)  # L1.X1 format
                
                if lag_match:
                    if param_name.startswith('L'):
                        # L1.X1 format
                        lag_num = int(lag_match.group(1))
                        var_name = lag_match.group(2)
                    else:
                        # X1.L1 format
                        var_name = lag_match.group(1)
                        lag_num = int(lag_match.group(2))
                    # Format as "X1 (lag 1)"
                    formatted_name = f"{var_name} (lag {lag_num})"
                    # Check if this is an endogenous variable
                    if var_name in numeric_dependent_vars:
                        return formatted_name, None, 'lag'  # Will be assigned to each equation
                    else:
                        # Lagged exogenous? Unusual but possible
                        return formatted_name, None, 'lag'
                
                # Check if parameter name directly matches an exogenous variable
                if param_name in numeric_independent_vars:
                    # Direct match - this is an exogenous variable
                    return param_name, None, 'exog'  # Will be assigned to each equation
                
                # Check if it's an interaction term (contains colon)
                if ':' in param_name and param_name in numeric_independent_vars:
                    return param_name, None, 'exog'
                
                # Fallback: return as-is
                return param_name, None, None
            
            # Organize coefficients by equation (dependent variable)
            # VAR returns params as DataFrame: columns = equations, rows = parameters
            equations_coefs = {}
            for dv in numeric_dependent_vars:
                equations_coefs[dv] = []
            
            # Also collect intercepts separately
            intercepts = {}
            
            # Debug: Print structure
            if isinstance(coef_table, pd.DataFrame):
                print(f"DEBUG: VAR params DataFrame structure:")
                print(f"  - Columns (equations): {list(coef_table.columns)}")
                print(f"  - Index (parameters): {list(coef_table.index)}")
                print(f"  - Shape: {coef_table.shape}")
            
            # Process each parameter (row in DataFrame) for each equation (column)
            if isinstance(coef_table, pd.DataFrame):
                # VAR format: iterate over parameters (rows) and equations (columns)
                for param_name in coef_table.index:
                    formatted_name, _, param_type = parse_param_name(param_name, numeric_dependent_vars, numeric_independent_vars)
                    
                    # Debug: Print parameter parsing
                    print(f"DEBUG: Parameter '{param_name}' -> formatted: '{formatted_name}', type: '{param_type}'")
                    
                    # Get statistics for this parameter (if available as DataFrames)
                    std_err_dict = {}
                    t_stat_dict = {}
                    p_val_dict = {}
                    
                    if isinstance(std_errors, pd.DataFrame) and param_name in std_errors.index:
                        std_err_dict = std_errors.loc[param_name].to_dict()
                    if isinstance(t_values, pd.DataFrame) and param_name in t_values.index:
                        t_stat_dict = t_values.loc[param_name].to_dict()
                    if isinstance(p_values, pd.DataFrame) and param_name in p_values.index:
                        p_val_dict = p_values.loc[param_name].to_dict()
                    
                    # For each equation (column in DataFrame)
                    for dv in coef_table.columns:
                        if dv not in numeric_dependent_vars:
                            continue
                        
                        # Get coefficient value for this equation
                        param_value = coef_table.loc[param_name, dv]
                        
                        # Get statistics for this equation
                        std_err = std_err_dict.get(dv, np.nan) if std_err_dict else np.nan
                        t_stat = t_stat_dict.get(dv, np.nan) if t_stat_dict else np.nan
                        p_val = p_val_dict.get(dv, np.nan) if p_val_dict else np.nan
                        
                        # Convert to float, handling Series/array types
                        if hasattr(std_err, 'iloc') and len(std_err) > 0:
                            std_err = float(std_err.iloc[0])
                        elif hasattr(std_err, 'item'):
                            std_err = std_err.item()
                        else:
                            try:
                                std_err = float(std_err) if pd.notna(std_err) and np.isfinite(std_err) else np.nan
                            except (TypeError, ValueError):
                                std_err = np.nan
                        
                        if hasattr(t_stat, 'iloc') and len(t_stat) > 0:
                            t_stat = float(t_stat.iloc[0])
                        elif hasattr(t_stat, 'item'):
                            t_stat = t_stat.item()
                        else:
                            try:
                                t_stat = float(t_stat) if pd.notna(t_stat) and np.isfinite(t_stat) else np.nan
                            except (TypeError, ValueError):
                                t_stat = np.nan
                        
                        if hasattr(p_val, 'iloc') and len(p_val) > 0:
                            p_val = float(p_val.iloc[0])
                        elif hasattr(p_val, 'item'):
                            p_val = p_val.item()
                        else:
                            try:
                                p_val = float(p_val) if pd.notna(p_val) and np.isfinite(p_val) else np.nan
                            except (TypeError, ValueError):
                                p_val = np.nan
                        
                        coef_entry = {
                            'parameter': formatted_name,
                            'coefficient': float(param_value),
                            'std_error': std_err if np.isfinite(std_err) else None,
                            't_statistic': t_stat if np.isfinite(t_stat) else None,
                            'p_value': p_val if np.isfinite(p_val) else None,
                            'significance': get_significance(p_val),
                            'original_name': param_name
                        }
                        
                        # Handle intercepts
                        if param_type == 'intercept':
                            intercepts[dv] = float(param_value)
                        # Handle other parameters (lags and exogenous)
                        else:
                            equations_coefs[dv].append(coef_entry)
            
            # Convert to list format for template
            # Separate coefficients by type: endogenous (lags) vs exogenous
            equations_data = []
            for dv in numeric_dependent_vars:
                # Get all coefficients for this equation
                eq_coefs = equations_coefs.get(dv, [])
                
                # Separate into endogenous (lags) and exogenous
                endogenous_coefs = []  # Lagged endogenous variables
                exogenous_coefs = []    # Exogenous variables
                
                for coef in eq_coefs:
                    param = coef['parameter']
                    # Check if it's a lagged endogenous variable
                    lag_match = re.match(r'.+? \(lag (\d+)\)', param)
                    if lag_match:
                        endogenous_coefs.append(coef)
                    else:
                        # Not a lag, must be exogenous
                        exogenous_coefs.append(coef)
                
                # Sort endogenous by lag number
                def sort_lag_key(entry):
                    param = entry['parameter']
                    lag_match = re.match(r'.+? \(lag (\d+)\)', param)
                    if lag_match:
                        lag_num = int(lag_match.group(1))
                        return lag_num
                    return 0
                
                endogenous_coefs_sorted = sorted(endogenous_coefs, key=sort_lag_key)
                
                # Sort exogenous alphabetically
                exogenous_coefs_sorted = sorted(exogenous_coefs, key=lambda x: x['parameter'])
                
                # Add intercept at the beginning if it exists
                intercept_entry = None
                if dv in intercepts:
                    # Find intercept statistics
                    intercept_param_name = f'const.{dv}' if f'const.{dv}' in coef_table.index else 'const'
                    if intercept_param_name not in coef_table.index and len(numeric_dependent_vars) == 1:
                        intercept_param_name = 'const'
                    
                    intercept_std_err = None
                    intercept_t_stat = None
                    intercept_p_val = None
                    
                    try:
                        if intercept_param_name in std_errors.index:
                            se_val = std_errors.loc[intercept_param_name]
                            if hasattr(se_val, 'item'):
                                se_val = se_val.item()
                            intercept_std_err = float(se_val) if np.isfinite(se_val) else None
                    except (KeyError, ValueError, TypeError):
                        intercept_std_err = None
                    
                    try:
                        if intercept_param_name in t_values.index:
                            t_val = t_values.loc[intercept_param_name]
                            if hasattr(t_val, 'item'):
                                t_val = t_val.item()
                            intercept_t_stat = float(t_val) if np.isfinite(t_val) else None
                    except (KeyError, ValueError, TypeError):
                        intercept_t_stat = None
                    
                    try:
                        if intercept_param_name in p_values.index:
                            p_val = p_values.loc[intercept_param_name]
                            if hasattr(p_val, 'item'):
                                p_val = p_val.item()
                            intercept_p_val = float(p_val) if np.isfinite(p_val) else None
                    except (KeyError, ValueError, TypeError):
                        intercept_p_val = None
                    
                    intercept_entry = {
                        'parameter': 'Intercept',
                        'coefficient': intercepts[dv],
                        'std_error': intercept_std_err,
                        't_statistic': intercept_t_stat,
                        'p_value': intercept_p_val,
                        'significance': get_significance(intercept_p_val) if intercept_p_val is not None else '',
                        'original_name': intercept_param_name
                    }
                
                # Debug: Print what we found for this equation
                print(f"DEBUG: Equation {dv}:")
                print(f"  - Endogenous coefficients: {len(endogenous_coefs_sorted)}")
                for c in endogenous_coefs_sorted[:3]:
                    print(f"    * {c['parameter']}")
                print(f"  - Exogenous coefficients: {len(exogenous_coefs_sorted)}")
                for c in exogenous_coefs_sorted[:3]:
                    print(f"    * {c['parameter']}")
                
                equations_data.append({
                    'dependent_var': dv,
                    'intercept': intercept_entry,
                    'endogenous_coefficients': endogenous_coefs_sorted,  # Lagged endogenous variables
                    'exogenous_coefficients': exogenous_coefs_sorted,    # Exogenous variables
                    'all_coefficients': ([intercept_entry] if intercept_entry else []) + endogenous_coefs_sorted + exogenous_coefs_sorted  # For equation display
                })
            
            # Extract covariance matrix
            try:
                cov_matrix = results.cov_params()
                # Convert to list of lists for template display
                cov_data = []
                cov_index = cov_matrix.index.tolist()
                cov_columns = cov_matrix.columns.tolist()
                
                # Format parameter names in covariance matrix
                formatted_cov_index = []
                formatted_cov_columns = []
                for name in cov_index:
                    # Handle tuple names (can happen with MultiIndex)
                    if isinstance(name, tuple):
                        name = '.'.join(str(n) for n in name)
                    elif not isinstance(name, str):
                        name = str(name)
                    formatted, _, _ = parse_param_name(name, numeric_dependent_vars, numeric_independent_vars)
                    formatted_cov_index.append(formatted)
                for name in cov_columns:
                    # Handle tuple names (can happen with MultiIndex)
                    if isinstance(name, tuple):
                        name = '.'.join(str(n) for n in name)
                    elif not isinstance(name, str):
                        name = str(name)
                    formatted, _, _ = parse_param_name(name, numeric_dependent_vars, numeric_independent_vars)
                    formatted_cov_columns.append(formatted)
                
                # Create covariance matrix data
                # Use a list of lists structure for easier template access
                for i, row_name in enumerate(formatted_cov_index):
                    row_data = {'parameter': row_name}
                    # Store covariance values with formatted column names as keys
                    for j, col_name in enumerate(formatted_cov_columns):
                        # Use the formatted column name as key
                        row_data[col_name] = f'{cov_matrix.iloc[i, j]:.6f}'
                    cov_data.append(row_data)
                
            except Exception as e:
                print(f"Warning: Could not extract covariance matrix: {e}")
                cov_data = []
                formatted_cov_columns = []
            
            # Store results for IRF generation
            # Note: independent_vars may include dummy-encoded variable names
            # Store original variable names for display purposes
            # Map back to original variable names for display (if stationary columns were used)
            display_dependent_vars = []
            for orig_var in dependent_vars:
                if orig_var in var_mapping:
                    # This variable has a stationary version - use original name for display
                    actual_col = var_mapping[orig_var]
                    if actual_col in numeric_dependent_vars:
                        display_dependent_vars.append(orig_var)  # Show original name
                elif orig_var in numeric_dependent_vars:
                    display_dependent_vars.append(orig_var)
            
            results_data = {
                'has_results': True,
                'fit_stats': fit_table_rows,
                'diagnostics': diagnostics_table_rows,  # Diagnostic tests table
                'equations': equations_data,  # Organized by equation
                'covariance_matrix': cov_data,
                'covariance_columns': formatted_cov_columns,
                'dependent_vars': display_dependent_vars,  # Original variable names for display
                'actual_dependent_vars': numeric_dependent_vars,  # Actual columns used in model (may include _stationary)
                'independent_vars': numeric_independent_vars,  # May include dummy variables
                'original_independent_vars': independent_vars,  # Original variable names before encoding
                'dummy_encoded_vars': dummy_encoded_vars,  # Mapping of original -> dummy columns
                'var_mapping': var_mapping,  # Mapping of original -> stationary columns
                'formula': formula,
                'var_order': var_order,
                'max_lags': max_lags_to_test,  # Store max_lags so template can display it
                'lag_selection_table': lag_selection_table if lag_selection_table else [],  # Table of lag selection results
                'lag_selection_results': lag_selection_results,  # Optimal lags for each criterion
                'auto_lag_selection': use_auto_lag_selection,  # Whether auto selection was used
                'stationarity_results': stationarity_results,  # ADF test results for endogenous variables
                'model_results': results,  # Store for IRF generation
                'endog_data': endog_clean,  # Store for IRF generation
                'constant_stationary_vars': constant_stationary_vars,  # Variables with constant stationary columns (will use original instead)
                'error': None
            }
            
            return results_data
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'error': f'Error running VARX: {str(e)}',
                'has_results': False
            }

