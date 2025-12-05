import re
import numpy as np
import pandas as pd
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.diagnostic import het_breuschpagan
from scipy.stats import jarque_bera

# Import linearmodels with error handling
try:
    from linearmodels.system import SUR, IV3SLS
    from linearmodels.iv import IV2SLS
    LINEARMODELS_AVAILABLE = True
except ImportError:
    LINEARMODELS_AVAILABLE = False
    print("Warning: linearmodels not available. Install with: pip install linearmodels>=5.0.0")


# ===================================================================
# Utility: Parse formula into components
# ===================================================================

def parse_equation(formula):
    """
    Parses strings like:
        "y1 ~ x1 + x2"
        "y1 ~ x1 + [x2 ~ z1 + z2]"

    Returns dict:
       {"dependent": "y1",
        "exog": [...],
        "endog": [...],
        "instr": [...]}
    """
    dependent, rhs = formula.split("~")
    dependent = dependent.strip()

    # detect endogenous blocks: [x2 ~ z1 + z2]
    endog_blocks = re.findall(r"\[(.*?)\]", rhs)

    endog = []
    instruments = []
    if endog_blocks:
        for block in endog_blocks:
            left, right = block.split("~")
            endog_var = left.strip()
            instr_vars = [v.strip() for v in right.split("+")]
            endog.append(endog_var)
            instruments += instr_vars

    # remove brackets part
    rhs_clean = re.sub(r"\[.*?\]", "", rhs)

    # exogenous variables
    exog = [v.strip() for v in rhs_clean.split("+") if v.strip()]

    # remove empty and dependent
    exog = [x for x in exog if x != "" and x != dependent]

    # deduplicate
    exog = list(dict.fromkeys(exog))

    return {
        "dependent": dependent,
        "exog": exog,
        "endog": endog,
        "instr": instruments
    }


# ===================================================================
# Identification Check (Order Condition)
# ===================================================================

def check_identification(system):
    """
    system = list of formula strings
    Returns: list of dicts: {"equation": eq, "identified": True/False, "reason": "..."}
    
    Detects endogenous variables that appear as:
    1. Explicitly marked with brackets: [x ~ z1 + z2]
    2. Dependent variable in one equation and regressor in another
    """

    results = []
    parsed_all = [parse_equation(eq) for eq in system]
    
    # Collect all dependent variables (these are endogenous by definition)
    all_dependent_vars = {parsed["dependent"] for parsed in parsed_all}
    
    # Collect all instruments in the system
    all_instr = set()
    for entry in parsed_all:
        all_instr |= set(entry["instr"])

    for eq, parsed in zip(system, parsed_all):
        # Get explicitly marked endogenous variables from brackets
        explicit_endog = set(parsed["endog"])
        
        # Find variables that are regressors in this equation but are dependent variables in other equations
        # These are implicitly endogenous
        rhs_vars = set(parsed["exog"]) | set(parsed["endog"])
        implicit_endog = rhs_vars & all_dependent_vars
        
        # Combine explicit and implicit endogenous variables
        endog_vars = explicit_endog | implicit_endog
        instr = parsed["instr"]
        exog = parsed["exog"]

        if not endog_vars:
            results.append({"equation": eq, "identified": True, "reason": "No endogenous regressors"})
            continue

        # Build reason message
        endog_list = sorted(list(endog_vars))
        if implicit_endog:
            reason_parts = []
            if implicit_endog:
                reason_parts.append(f"Endogenous: {', '.join(sorted(implicit_endog))} (appears as DV in other equations)")
            if explicit_endog:
                reason_parts.append(f"Endogenous: {', '.join(sorted(explicit_endog))} (explicitly marked)")
            reason_base = "; ".join(reason_parts)
        else:
            reason_base = f"Endogenous variables: {', '.join(endog_list)}"

        # Order condition: number of instruments >= number of endogenous variables
        # For each endogenous variable, we need at least one instrument
        if len(instr) < len(endog_vars):
            results.append({
                "equation": eq,
                "identified": False,
                "reason": f"{reason_base}. Insufficient instruments: needs >= {len(endog_vars)}, has {len(instr)}"
            })
        else:
            results.append({
                "equation": eq,
                "identified": True,
                "reason": f"{reason_base}. Identification satisfied ({len(instr)} instruments for {len(endog_vars)} endogenous variables)"
            })

    return results


# ===================================================================
# Diagnostics
# ===================================================================

def diagnostics(y, y_hat, X, residuals, name="eq"):
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    jb_stat, jb_p, _, _ = jarque_bera(residuals)
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, X)

    return {
        "equation": name,
        "R2": r2,
        "DW": durbin_watson(residuals),
        "JB_stat": jb_stat,
        "JB_p": jb_p,
        "BP_stat": bp_stat,
        "BP_p": bp_p
    }


# ===================================================================
# System Estimation Driver
# ===================================================================

def estimate_system(formulas, data, method="SUR"):
    """
    formulas: list of equation strings
    method: "SUR", "2SLS", "3SLS"
    """
    if not LINEARMODELS_AVAILABLE:
        raise ImportError("linearmodels package is required for structural model estimation. Install with: pip install linearmodels>=5.0.0")

    # 1. Identification Check
    id_results = check_identification(formulas)
    for r in id_results:
        if not r["identified"] and method in ["2SLS", "3SLS"]:
            raise ValueError(f"System not identifiable for equation: {r['equation']}. Reason: {r['reason']}")

    parsed = [parse_equation(eq) for eq in formulas]

    # ===================================================================
    # SUR
    # ===================================================================
    if method.upper() == "SUR":
        sur_eqs = {}
        for i, entry in enumerate(parsed):
            eq_name = f"eq{i+1}"
            exog = ["const"] + entry["exog"] + entry["endog"]
            sur_eqs[eq_name] = {
                "dependent": data[entry["dependent"]],
                "exog": data[exog]
            }

        model = SUR(sur_eqs)
        res = model.fit()

        # param table - handle MultiIndex properly
        params_df = res.params.reset_index()
        # Check the structure and build params DataFrame correctly
        if isinstance(res.params.index, pd.MultiIndex):
            # MultiIndex case: reset_index gives us index levels + values
            if len(params_df.columns) == 3:
                params_df.columns = ["equation", "variable", "param"]
            else:
                # Fallback: build manually
                params_data = []
                for (eq, var), val in res.params.items():
                    params_data.append({"equation": eq, "variable": var, "param": val})
                params_df = pd.DataFrame(params_data)
        else:
            # Single index case
            params_df.columns = ["variable", "param"]
            params_df.insert(0, "equation", [f"eq{i+1}" for i in range(len(params_df))])
        
        params = params_df.copy()
        params["std_err"] = res.std_errors.values
        params["t"] = res.tstats.values
        params["p"] = res.pvalues.values

        # diagnostics - SUR results don't have equation_results, need to compute manually
        diag_list = []
        for i, (eq_name, eq_dict) in enumerate(sur_eqs.items()):
            # Get equation data
            y = eq_dict["dependent"]
            X = eq_dict["exog"]
            
            # Get equation-specific parameters
            eq_params = params[params["equation"] == eq_name]
            if len(eq_params) > 0:
                # Compute fitted values: y_hat = X @ beta
                beta = eq_params.set_index("variable")["param"]
                # Align beta with X columns - ensure we have matching columns
                common_cols = [col for col in X.columns if col in beta.index]
                if len(common_cols) > 0:
                    X_aligned = X[common_cols]
                    beta_aligned = beta[common_cols]
                    y_hat = X_aligned @ beta_aligned
                    residuals = y - y_hat
                    
                    # Ensure we have numpy arrays for diagnostics
                    y_vals = y.values if hasattr(y, 'values') else np.array(y)
                    y_hat_vals = y_hat.values if hasattr(y_hat, 'values') else np.array(y_hat)
                    X_vals = X.values if hasattr(X, 'values') else np.array(X)
                    residuals_vals = residuals.values if hasattr(residuals, 'values') else np.array(residuals)
                    
                    diag = diagnostics(y_vals, y_hat_vals, X_vals, residuals_vals, name=eq_name)
                    diag_list.append(diag)
                else:
                    # Fallback: use res.fitted_values and res.resids if available
                    print(f"Warning: Could not align columns for {eq_name}, skipping diagnostics")

        return res, params, pd.DataFrame(diag_list) if diag_list else pd.DataFrame(columns=["equation", "R2", "DW", "JB_stat", "JB_p", "BP_stat", "BP_p"])

    # ===================================================================
    # 2SLS (single equation only)
    # ===================================================================
    if method.upper() == "2SLS":
        if len(formulas) > 1:
            raise ValueError("2SLS supports only one equation at a time")

        formula = formulas[0]
        model = IV2SLS.from_formula(formula, data=data)
        res = model.fit(cov_type="robust")

        params = pd.DataFrame({
            "variable": res.params.index,
            "param": res.params.values,
            "std_err": res.std_errors.values,
            "t": res.tstats.values,
            "p": res.pvalues.values
        })

        diag = diagnostics(
            res.model.dependent.data,
            res.fitted_values,
            res.model.exog,
            res.resids,
            name="2SLS"
        )

        return res, params, pd.DataFrame([diag])

    # ===================================================================
    # 3SLS
    # ===================================================================
    if method.upper() == "3SLS":
        eq_dict = {f"eq{i+1}": f for i, f in enumerate(formulas)}

        model = IV3SLS.from_formula(eq_dict, data=data)
        res = model.fit()

        # param table - handle MultiIndex properly
        # Build params DataFrame manually to ensure correct alignment
        params_data = []
        for (eq, var), val in res.params.items():
            params_data.append({
                "equation": eq,
                "variable": var,
                "param": val,
                "std_err": res.std_errors.loc[(eq, var)],
                "t": res.tstats.loc[(eq, var)],
                "p": res.pvalues.loc[(eq, var)]
            })
        params = pd.DataFrame(params_data)

        # diagnostics - 3SLS results may not have equation_results, compute manually
        diag_list = []
        for i, (eq_name, formula) in enumerate(eq_dict.items()):
            # Parse the equation to get dependent and regressors
            parsed = parse_equation(formula)
            y = data[parsed["dependent"]]
            
            # Build X matrix
            exog_vars = ["const"] + parsed["exog"] + parsed["endog"]
            X = data[[col for col in exog_vars if col in data.columns]]
            
            # Get equation-specific parameters
            eq_params = params[params["equation"] == eq_name]
            if len(eq_params) > 0:
                # Compute fitted values: y_hat = X @ beta
                beta = eq_params.set_index("variable")["param"]
                # Align beta with X columns - ensure we have matching columns
                common_cols = [col for col in X.columns if col in beta.index]
                if len(common_cols) > 0:
                    X_aligned = X[common_cols]
                    beta_aligned = beta[common_cols]
                    y_hat = X_aligned @ beta_aligned
                    residuals = y - y_hat
                    
                    # Ensure we have numpy arrays for diagnostics
                    y_vals = y.values if hasattr(y, 'values') else np.array(y)
                    y_hat_vals = y_hat.values if hasattr(y_hat, 'values') else np.array(y_hat)
                    X_vals = X.values if hasattr(X, 'values') else np.array(X)
                    residuals_vals = residuals.values if hasattr(residuals, 'values') else np.array(residuals)
                    
                    diag = diagnostics(y_vals, y_hat_vals, X_vals, residuals_vals, name=eq_name)
                    diag_list.append(diag)
                else:
                    # Fallback: use res.fitted_values and res.resids if available
                    print(f"Warning: Could not align columns for {eq_name}, skipping diagnostics")

        return res, params, pd.DataFrame(diag_list) if diag_list else pd.DataFrame(columns=["equation", "R2", "DW", "JB_stat", "JB_p", "BP_stat", "BP_p"])

    raise ValueError("Method must be 'SUR', '2SLS', or '3SLS'")


class StructuralModelModule:
    """Module for SUR/2SLS/3SLS structural equation estimation."""
    
    @staticmethod
    def ui_schema():
        """Return UI schema for structural models."""
        return {
            'formula': {
                'type': 'text',
                'label': 'Equations',
                'help': 'Enter equations separated by newlines (one per line) or semicolons. For endogenous variables, use [var ~ instruments]. Example: "y1 ~ x1 + x2\ny2 ~ x1 + [x3 ~ z1 + z2]"',
                'required': True
            },
            'method': {
                'type': 'select',
                'label': 'Method',
                'options': ['SUR', '2SLS', '3SLS'],
                'default': 'SUR',
                'help': 'SUR: Seemingly Unrelated Regression (no endogeneity). 2SLS: Two-Stage Least Squares (single equation). 3SLS: Three-Stage Least Squares (system with endogeneity).'
            }
        }
    
    @staticmethod
    def run(df, formula, analysis_type=None, outdir=None, options=None, schema_types=None, schema_orders=None):
        """
        Run structural model estimation (SUR/2SLS/3SLS).
        
        Parameters:
        - df: DataFrame containing the data
        - formula: Formula string with equations separated by semicolons
        - analysis_type: Not used
        - outdir: Output directory for results
        - options: Dictionary with 'method' key ('SUR', '2SLS', or '3SLS')
        - schema_types: Column type information
        - schema_orders: Column ordering information
        
        Returns:
        Dictionary with estimation results
        """
        if not LINEARMODELS_AVAILABLE:
            return {
                'error': 'linearmodels package is not installed. Please install it with: pip install linearmodels>=5.0.0',
                'has_results': False
            }
        
        try:
            # Get method from options, default to SUR
            method = options.get('method', 'SUR') if options else 'SUR'
            
            # Parse formula - split by newlines or semicolons to get multiple equations
            # First try newlines (one equation per line), then semicolons as fallback
            if '\n' in formula:
                formulas = [f.strip() for f in formula.split('\n') if f.strip() and '~' in f]
            elif ';' in formula:
                formulas = [f.strip() for f in formula.split(';') if f.strip()]
            else:
                formulas = [formula.strip()]
            
            if not formulas:
                return {
                    'error': 'No equations provided. Use newlines or semicolons to separate multiple equations.',
                    'has_results': False
                }
            
            # Validate that all variables exist in dataset
            all_vars = set()
            for eq in formulas:
                parsed = parse_equation(eq)
                all_vars.update([parsed['dependent']] + parsed['exog'] + parsed['endog'] + parsed['instr'])
            
            missing_vars = [v for v in all_vars if v not in df.columns]
            if missing_vars:
                return {
                    'error': f'Variables not found in dataset: {", ".join(missing_vars)}',
                    'has_results': False
                }
            
            # Add constant term to dataframe if not present
            if 'const' not in df.columns:
                df = df.copy()
                df['const'] = 1.0
            
            # Estimate the system
            res, params, diagnostics_df = estimate_system(formulas, df, method=method)
            
            # Format results for display
            # Ensure diagnostics is always a list, even if empty
            diagnostics_list = diagnostics_df.to_dict('records') if len(diagnostics_df) > 0 else []
            
            results = {
                'success': True,
                'has_results': True,
                'method': method,
                'formulas': formulas,
                'params': params.to_dict('records'),
                'diagnostics': diagnostics_list,
                'identification': check_identification(formulas),
                'n_obs': len(df),
                'n_equations': len(formulas)
            }
            
            # Add summary statistics if available
            if hasattr(res, 'rsquared'):
                results['rsquared'] = res.rsquared
            if hasattr(res, 'rsquared_adj'):
                results['rsquared_adj'] = res.rsquared_adj
            
            return results
            
        except ValueError as e:
            return {
                'error': str(e),
                'has_results': False
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'error': f'Error estimating structural model: {str(e)}',
                'has_results': False
            }

