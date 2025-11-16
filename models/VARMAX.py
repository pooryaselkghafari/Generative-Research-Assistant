import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.varmax import VARMAX
from statsmodels.tools.eval_measures import aic, bic
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


def fit_varmax_per_eq_exog(
    endog_df: pd.DataFrame,
    exog_df: pd.DataFrame,
    exog_map: dict,
    order=(2, 0),
    trend="c",
    enforce_stationarity=True,
    steps_irf=12,
    alpha=0.05
):
    """
    Fit VARMAX model with per-equation exogenous controls.
    
    Parameters:
    - endog_df: DataFrame with columns = endogenous series in desired order
    - exog_df: DataFrame with all candidate exogenous controls (union across equations)
    - exog_map: dict mapping each endog name to the list of exog names allowed in its equation
                e.g. {'Y1': ['X1','X2'], 'Y2': ['X3']}
    - order: (p, q) for VARMAX
    - trend: "c" for constant, "n" for none, "t" for linear trend
    - enforce_stationarity: Whether to enforce stationarity constraints
    - steps_irf: horizon for IRF
    - alpha: Significance level for confidence intervals
    
    Returns:
    - res: Fitted VARMAX model results
    - df_params: Tidy parameter table DataFrame
    - fit_table: Model fit statistics DataFrame
    - df_irf: IRF results DataFrame
    """
    endog_names = list(endog_df.columns)
    
    # Basic checks - ensure all endog have entries in exog_map
    for y in endog_names:
        if y not in exog_map:
            exog_map[y] = []  # allow none by default
    
    # Fit an initial model so we can discover parameter names reliably
    mod0 = VARMAX(
        endog_df, 
        exog=exog_df, 
        order=order, 
        trend=trend, 
        enforce_stationarity=enforce_stationarity
    )
    res0 = mod0.fit(disp=False)
    
    # Build zero constraints for disallowed exog-by-equation coefficients
    param_names = res0.param_names
    zero_constraints = []
    
    # Create a quick lookup of allowed exogs per equation
    allowed = {y: set(exog_map.get(y, [])) for y in endog_names}
    all_exogs = set(exog_df.columns)
    
    # For each equation y, all exogs not in allowed[y] should be zero
    for y in endog_names:
        disallowed_for_y = all_exogs - allowed[y]
        for pname in param_names:
            # Heuristic: match beta parameters that look tied to exog and endog
            low = pname.lower()
            if ('beta' in low or 'exog' in low) and y.lower() in low:
                for x in disallowed_for_y:
                    if x.lower() in low:
                        zero_constraints.append(f"{pname} = 0")
    
    # Build constraint string
    constraint_str = " , ".join(sorted(set(zero_constraints)))
    
    # Fit constrained if we have any constraints, else keep res0
    if constraint_str:
        try:
            res = mod0.fit_constrained(constraint_str, disp=False)
        except Exception as e:
            print(f"Constraint fit failed, falling back to unconstrained fit. Reason: {str(e)}")
            res = res0
    else:
        res = res0
    
    # ---- Tidy parameter table ----
    params = res.params
    bse = res.bse
    pvalues = res.pvalues
    conf_int = res.conf_int(alpha=alpha)
    conf_int.columns = ['ci_low', 'ci_high']
    
    df_params = pd.concat(
        [
            params.rename("coef"),
            bse.rename("std_err"),
            res.tvalues.rename("z"),
            pvalues.rename("pvalue"),
            conf_int
        ],
        axis=1
    ).reset_index().rename(columns={"index": "param"})
    
    # Try to parse equation and exog names for readability
    def parse_eq_exog(p):
        lp = p.lower()
        eq_guess, exog_guess = None, None
        # Find which eq the param belongs to
        for y in endog_names:
            if y.lower() in lp:
                eq_guess = y
                break
        # Find which exog it refers to
        for x in exog_df.columns:
            if x.lower() in lp:
                exog_guess = x
                break
        return eq_guess, exog_guess
    
    eqs, exogs = zip(*[parse_eq_exog(p) for p in df_params['param']])
    df_params['equation'] = list(eqs)
    df_params['exog_hint'] = list(exogs)
    
    # Sort by equation then param
    df_params = df_params[
        ['equation', 'param', 'exog_hint', 'coef', 'std_err', 'z', 'pvalue', 'ci_low', 'ci_high']
    ].sort_values(['equation', 'param'])
    
    # ---- Model fit table ----
    fit_table = pd.DataFrame({
        "nobs": [res.nobs],
        "loglik": [res.llf],
        "aic": [res.aic],
        "bic": [res.bic],
        "hqic": [getattr(res, "hqic", np.nan)],
        "k_params": [len(res.params)]
    })
    
    # ---- IRF ----
    irf_array = res.impulse_responses(steps_irf)  # shape: (steps, k_endog, k_endog)
    # Build a tidy IRF DataFrame: columns = ['step','impulse','response','irf']
    records = []
    k = len(endog_names)
    for h in range(steps_irf):
        for i_imp in range(k):
            for j_resp in range(k):
                records.append({
                    "step": h,
                    "impulse": endog_names[i_imp],
                    "response": endog_names[j_resp],
                    "irf": irf_array[h, j_resp, i_imp]
                })
    df_irf = pd.DataFrame(records)
    
    return res, df_params, fit_table, df_irf


class VARMAXModule:
    def run(self, df, formula, analysis_type=None, outdir=None, options=None, schema_types=None, schema_orders=None):
        """
        Run VARMAX (Vector Autoregression Moving Average with Exogenous variables) analysis.
        Supports per-equation exogenous controls.
        
        Parameters:
        - df: DataFrame containing the data
        - formula: Formula string with multiple equations (e.g., "y1 ~ x1 + x2\n y2 ~ x3")
        - analysis_type: Not used in VARMAX
        - outdir: Output directory for results
        - options: Dictionary of analysis options (e.g., {'order': (2,0), 'steps_irf': 12})
        - schema_types: Column type information
        - schema_orders: Column ordering information
        
        Returns:
        Dictionary with VARMAX results
        """
        
        try:
            # Parse multi-equation formula
            # Formula format: each line is "y ~ x1 + x2 + ..."
            # Lines are separated by newlines
            formula_lines = [line.strip() for line in formula.split('\n') if line.strip()]
            
            if len(formula_lines) < 2:
                return {
                    'error': 'VARMAX requires at least 2 equations. Please write multiple equations, one per line (e.g., "y1 ~ x1 + x2\\n y2 ~ x3")',
                    'has_results': False
                }
            
            # Parse each equation to extract dependent and independent variables
            dependent_vars = []
            exog_map = {}  # Maps each dependent var to its allowed exogenous vars
            
            for line in formula_lines:
                if '~' not in line:
                    return {
                        'error': f'Invalid equation format: "{line}". Use "y ~ x1 + x2"',
                        'has_results': False
                    }
                
                parts = line.split('~')
                dependent_var = parts[0].strip()
                independent_vars_str = parts[1].strip() if len(parts) > 1 else ""
                
                # Parse independent variables
                if independent_vars_str:
                    independent_vars = [v.strip() for v in independent_vars_str.split('+') if v.strip()]
                else:
                    independent_vars = []
                
                # Check if dependent variable exists in dataset
                if dependent_var not in df.columns:
                    # Check for stationary version
                    stationary_var = f'{dependent_var}_stationary'
                    if stationary_var in df.columns:
                        dependent_var = stationary_var
                    else:
                        return {
                            'error': f'Dependent variable "{dependent_var}" not found in dataset',
                            'has_results': False
                        }
                
                dependent_vars.append(dependent_var)
                exog_map[dependent_var] = independent_vars
            
            # Check for duplicate dependent variables
            if len(dependent_vars) != len(set(dependent_vars)):
                return {
                    'error': 'Each equation must have a unique dependent variable',
                    'has_results': False
                }
            
            # Collect all unique exogenous variables
            all_exog_vars = set()
            for exog_list in exog_map.values():
                all_exog_vars.update(exog_list)
            
            # Check if all exogenous variables exist in dataset
            missing_exog = []
            for exog in all_exog_vars:
                if exog not in df.columns:
                    # Check for stationary version
                    stationary_exog = f'{exog}_stationary'
                    if stationary_exog in df.columns:
                        # Update exog_map to use stationary version
                        for dep_var in exog_map:
                            if exog in exog_map[dep_var]:
                                idx = exog_map[dep_var].index(exog)
                                exog_map[dep_var][idx] = stationary_exog
                    else:
                        missing_exog.append(exog)
            
            if missing_exog:
                return {
                    'error': f'Exogenous variables not found in dataset: {", ".join(missing_exog)}',
                    'has_results': False
                }
            
            # Prepare endogenous DataFrame
            endog_df = df[dependent_vars].copy()
            
            # Check for missing values and drop them
            if endog_df.isnull().any().any():
                print("Warning: Missing values found in endogenous variables. Dropping rows with missing values.")
                endog_df = endog_df.dropna()
            
            # Prepare exogenous DataFrame (union of all exogenous variables)
            if all_exog_vars:
                # Update all_exog_vars to include stationary versions if used
                final_exog_vars = []
                for exog in all_exog_vars:
                    if exog in df.columns:
                        final_exog_vars.append(exog)
                    elif f'{exog}_stationary' in df.columns:
                        final_exog_vars.append(f'{exog}_stationary')
                
                exog_df = df[final_exog_vars].copy()
                # Align with endog_df index after dropping NaN
                exog_df = exog_df.loc[endog_df.index]
                
                # Update exog_map to use final variable names
                updated_exog_map = {}
                for dep_var in exog_map:
                    updated_list = []
                    for exog in exog_map[dep_var]:
                        if exog in final_exog_vars:
                            updated_list.append(exog)
                        elif f'{exog}_stationary' in final_exog_vars:
                            updated_list.append(f'{exog}_stationary')
                    updated_exog_map[dep_var] = updated_list
                exog_map = updated_exog_map
            else:
                exog_df = pd.DataFrame(index=endog_df.index)
            
            # Check for missing values in exogenous variables
            if not exog_df.empty and exog_df.isnull().any().any():
                print("Warning: Missing values found in exogenous variables. Dropping rows with missing values.")
                common_index = endog_df.index.intersection(exog_df.dropna().index)
                endog_df = endog_df.loc[common_index]
                exog_df = exog_df.loc[common_index]
            
            # Ensure data is numeric
            for col in endog_df.columns:
                if not pd.api.types.is_numeric_dtype(endog_df[col]):
                    try:
                        endog_df[col] = pd.to_numeric(endog_df[col], errors='coerce')
                    except:
                        return {
                            'error': f'Cannot convert endogenous variable "{col}" to numeric',
                            'has_results': False
                        }
            
            for col in exog_df.columns:
                if not pd.api.types.is_numeric_dtype(exog_df[col]):
                    try:
                        exog_df[col] = pd.to_numeric(exog_df[col], errors='coerce')
                    except:
                        return {
                            'error': f'Cannot convert exogenous variable "{col}" to numeric',
                            'has_results': False
                        }
            
            # Get VARMAX order from options (default to (2, 0))
            var_order = options.get('var_order', 2) if options else 2
            if isinstance(var_order, (list, tuple)) and len(var_order) == 2:
                order = tuple(var_order)
            elif isinstance(var_order, int):
                order = (var_order, 0)  # VAR(p) with no MA terms
            else:
                order = (2, 0)  # Default
            
            # Get IRF steps from options (default to 12)
            steps_irf = options.get('steps_irf', 12) if options else 12
            
            # Get trend from options (default to "c" for constant)
            trend = options.get('trend', 'c') if options else 'c'
            
            # Get enforce_stationarity from options (default to True)
            enforce_stationarity = options.get('enforce_stationarity', True) if options else True
            
            # Fit VARMAX model
            print(f"Fitting VARMAX model with order {order}, trend={trend}, enforce_stationarity={enforce_stationarity}")
            print(f"Endogenous variables: {list(endog_df.columns)}")
            print(f"Exogenous variables: {list(exog_df.columns)}")
            print(f"Exog map: {exog_map}")
            
            res, df_params, fit_table, df_irf = fit_varmax_per_eq_exog(
                endog_df=endog_df,
                exog_df=exog_df,
                exog_map=exog_map,
                order=order,
                trend=trend,
                enforce_stationarity=enforce_stationarity,
                steps_irf=steps_irf,
                alpha=0.05
            )
            
            # Convert parameter table to list of dicts for template
            params_list = df_params.to_dict('records')
            
            # Helper function to format parameter names and extract components
            def parse_param_name(param_name, dep_vars, exog_vars):
                """Parse parameter name to extract equation, variable, and type"""
                param_lower = param_name.lower()
                eq_name = None
                var_name = None
                param_type = None
                
                # Find which equation this belongs to
                for dv in dep_vars:
                    if dv.lower() in param_lower:
                        eq_name = dv
                        break
                
                # Find which variable this refers to
                for ev in exog_vars:
                    if ev.lower() in param_lower:
                        var_name = ev
                        break
                
                # Determine parameter type
                if 'intercept' in param_lower or 'const' in param_lower:
                    param_type = 'intercept'
                elif 'beta' in param_lower or 'exog' in param_lower:
                    param_type = 'exogenous'
                elif 'phi' in param_lower or 'ar' in param_lower or 'l' in param_lower:
                    param_type = 'endogenous'
                else:
                    param_type = 'other'
                
                # Format for display
                formatted = param_name
                if var_name:
                    formatted = f"{var_name}"
                    if 'lag' in param_lower or 'l' in param_lower:
                        # Extract lag number
                        lag_match = re.search(r'l\.?(\d+)', param_lower)
                        if lag_match:
                            formatted = f"{var_name}(-{lag_match.group(1)})"
                
                return formatted, eq_name, param_type
            
            # Organize parameters by equation (matching VARX structure)
            equations_data = []
            for dep_var in dependent_vars:
                eq_params = [p for p in params_list if p.get('equation') == dep_var]
                
                # Separate parameters by type
                intercept_entry = None
                exogenous_coefs = []
                endogenous_coefs = []
                all_coefs = []
                
                for p in eq_params:
                    param_name = p.get('param', '')
                    formatted, eq, ptype = parse_param_name(param_name, dependent_vars, list(exog_df.columns) if not exog_df.empty else [])
                    
                    # Determine significance stars
                    pval = p.get('pvalue', 1.0)
                    if pval < 0.001:
                        sig = "***"
                    elif pval < 0.01:
                        sig = "**"
                    elif pval < 0.05:
                        sig = "*"
                    elif pval < 0.10:
                        sig = "."
                    else:
                        sig = ""
                    
                    coef_entry = {
                        'parameter': formatted,
                        'coefficient': float(p.get('coef', 0)),
                        'std_error': float(p.get('std_err', 0)) if pd.notna(p.get('std_err')) else None,
                        't_statistic': float(p.get('z', 0)) if pd.notna(p.get('z')) else None,
                        'p_value': float(p.get('pvalue', 1.0)) if pd.notna(p.get('pvalue')) else None,
                        'significance': sig,
                        'ci_low': float(p.get('ci_low', 0)) if pd.notna(p.get('ci_low')) else None,
                        'ci_high': float(p.get('ci_high', 0)) if pd.notna(p.get('ci_high')) else None
                    }
                    
                    if ptype == 'intercept':
                        intercept_entry = coef_entry
                    elif ptype == 'exogenous':
                        exogenous_coefs.append(coef_entry)
                    elif ptype == 'endogenous':
                        endogenous_coefs.append(coef_entry)
                    
                    all_coefs.append(coef_entry)
                
                equations_data.append({
                    'dependent_var': dep_var,
                    'intercept': intercept_entry,
                    'exogenous_coefficients': exogenous_coefs,
                    'endogenous_coefficients': endogenous_coefs,
                    'all_coefficients': ([intercept_entry] if intercept_entry else []) + endogenous_coefs + exogenous_coefs
                })
            
            # Convert fit table to rows format (matching VARX structure)
            # Template expects 'Statistic' and 'Value' (capitalized)
            fit_table_rows = []
            for key, value in fit_table.to_dict('records')[0].items():
                fit_table_rows.append({
                    'Statistic': key.upper(),
                    'Value': f'{float(value):.4f}' if pd.notna(value) and np.isfinite(value) else str(value) if pd.notna(value) else 'N/A'
                })
            
            # Convert IRF to list of dicts
            irf_list = df_irf.to_dict('records')
            
            # Prepare results dictionary (matching VARX structure)
            results_data = {
                'has_results': True,
                'fit_stats': fit_table_rows,  # List of dicts with statistic/value
                'equations': equations_data,  # Organized by equation
                'irf_data': irf_list,  # IRF data for plotting
                'dependent_vars': dependent_vars,
                'exogenous_vars': list(exog_df.columns) if not exog_df.empty else [],
                'exog_map': exog_map,  # Per-equation exogenous mapping
                'formula': formula,
                'var_order': order[0] if isinstance(order, tuple) else order,  # For display
                'order': order,  # Full order tuple
                'steps_irf': steps_irf,
                'model_results': res,  # Store for potential future use (IRF generation)
                'endog_data': endog_df,  # Store for IRF generation
                'error': None
            }
            
            return results_data
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'error': f'Error running VARMAX: {str(e)}',
                'has_results': False
            }

