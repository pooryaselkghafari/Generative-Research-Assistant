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
    # Find the main ~ separator (not inside brackets) by tracking bracket depth
    main_tilde_index = -1
    bracket_depth = 0
    for i, char in enumerate(formula):
        if char == '[':
            bracket_depth += 1
        elif char == ']':
            bracket_depth -= 1
        elif char == '~' and bracket_depth == 0:
            main_tilde_index = i
            break
    
    if main_tilde_index == -1:
        raise ValueError(f"Invalid equation format: '{formula}'. Expected format: 'y ~ x1 + x2' or 'y ~ x1 + [x2 ~ z1 + z2]'")
    
    dependent = formula[:main_tilde_index].strip()
    rhs = formula[main_tilde_index + 1:].strip()

    # detect endogenous blocks: [x2 ~ z1 + z2]
    endog_blocks = re.findall(r"\[(.*?)\]", rhs)

    endog = []
    instruments = []
    if endog_blocks:
        for block in endog_blocks:
            # Split by ~ to get endogenous variable and instruments
            block_parts = block.split("~")
            if len(block_parts) != 2:
                raise ValueError(f"Invalid bracket notation: [{block}]. Expected format: [endogenous ~ instrument1 + instrument2]")
            left, right = block_parts[0].strip(), block_parts[1].strip()
            endog_var = left
            instr_vars = [v.strip() for v in right.split("+") if v.strip()]
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

    # jarque_bera returns (statistic, pvalue) or (statistic, pvalue, skewness, kurtosis)
    jb_result = jarque_bera(residuals)
    if len(jb_result) >= 2:
        jb_stat, jb_p = jb_result[0], jb_result[1]
    else:
        jb_stat, jb_p = jb_result[0] if len(jb_result) > 0 else np.nan, np.nan
    
    # het_breuschpagan returns (statistic, pvalue) or (statistic, pvalue, fvalue, f_pvalue)
    bp_result = het_breuschpagan(residuals, X)
    if len(bp_result) >= 2:
        bp_stat, bp_p = bp_result[0], bp_result[1]
    else:
        bp_stat, bp_p = bp_result[0] if len(bp_result) > 0 else np.nan, np.nan

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
        raise ValueError("PACKAGE_ERROR: linearmodels package is not installed. Please install it with: pip install linearmodels>=5.0.0")

    # Normalize method to uppercase and strip whitespace (most robust approach)
    method = str(method).strip().upper() if method else "SUR"
    
    # Validate method - check against list of valid methods
    valid_methods = ["SUR", "2SLS", "3SLS"]
    if method not in valid_methods:
        raise ValueError(f"Method must be one of {valid_methods}. Got: {method}")

    # 1. Identification Check (only for 2SLS and 3SLS, not SUR)
    # SUR doesn't require identification since it doesn't deal with endogeneity
    if method in ["2SLS", "3SLS"]:
        id_results = check_identification(formulas)
        for r in id_results:
            if not r["identified"]:
                raise ValueError(f"System not identifiable for equation: {r['equation']}. Reason: {r['reason']}")

    parsed = [parse_equation(eq) for eq in formulas]

    # ===================================================================
    # SUR
    # ===================================================================
    if method == "SUR":
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

        return res, params, pd.DataFrame(diag_list) if diag_list else pd.DataFrame(columns=["equation", "R2", "DW", "JB_stat", "JB_p", "BP_stat", "BP_p"]), None

    # ===================================================================
    # 2SLS (single equation only)
    # ===================================================================
    if method == "2SLS":
        if len(formulas) > 1:
            raise ValueError("2SLS supports only one equation at a time")

        formula = formulas[0]
        parsed = parse_equation(formula)
        
        # Convert our format to linearmodels format
        # linearmodels expects: y ~ [endogenous ~ instruments] + exogenous
        # or: y ~ exogenous + [endogenous ~ instruments]
        
        # Build the formula for linearmodels
        dependent = parsed["dependent"]
        exog_vars = parsed["exog"]
        endog_vars = parsed["endog"]
        instruments = parsed["instr"]
        
        if not endog_vars:
            raise ValueError("2SLS requires at least one endogenous variable with instruments. Use bracket notation: [endogenous ~ instrument1 + instrument2]")
        
        if len(instruments) < len(endog_vars):
            raise ValueError(f"Insufficient instruments: need at least {len(endog_vars)} instrument(s) for {len(endog_vars)} endogenous variable(s)")
        
        # Build formula for linearmodels IV2SLS
        # linearmodels format: y ~ exog1 + exog2 + [endog ~ instruments]
        # The exogenous variables come first, then the endogenous in brackets
        
        # Build RHS parts
        rhs_parts = []
        
        # Add exogenous variables first
        if exog_vars:
            rhs_parts.extend(exog_vars)
        
        # Add endogenous variables with instruments in brackets (must come after exog)
        if len(endog_vars) == 1:
            # Single endogenous variable
            endog_str = endog_vars[0]
            instr_str = " + ".join(instruments)
            rhs_parts.append(f"[{endog_str} ~ {instr_str}]")
        else:
            # Multiple endogenous variables
            endog_str = " + ".join(endog_vars)
            instr_str = " + ".join(instruments)
            rhs_parts.append(f"[{endog_str} ~ {instr_str}]")
        
        # Combine: y ~ exog1 + exog2 + [endog ~ instruments]
        linearmodels_formula = f"{dependent} ~ {' + '.join(rhs_parts)}"
        
        # Debug: print the formula being passed to linearmodels
        print(f"DEBUG: 2SLS formula for linearmodels: {linearmodels_formula}")
        print(f"DEBUG: Parsed components - dependent: {dependent}, exog: {exog_vars}, endog: {endog_vars}, instruments: {instruments}")
        
        try:
            model = IV2SLS.from_formula(linearmodels_formula, data=data)
            # Fit with robust standard errors for parameter estimates
            res = model.fit(cov_type="robust")
            
            # Also fit without robust for overidentification test (J-statistic may only be available with non-robust)
            res_nonrobust = None
            try:
                res_nonrobust = model.fit(cov_type="unadjusted")  # Try unadjusted for J-stat
            except:
                try:
                    res_nonrobust = model.fit()  # Try default
                except:
                    pass
            
            # Validate that res is not None and has required attributes
            if res is None:
                raise ValueError("Model fitting returned None result")
            if not hasattr(res, 'params') or res.params is None:
                raise ValueError("Model result does not have valid params attribute")
            
            # Debug: Print first_stage info immediately after fitting
            if hasattr(res, 'first_stage'):
                print(f"DEBUG: res.first_stage exists, type: {type(res.first_stage)}")
                if res.first_stage is not None:
                    print(f"DEBUG: first_stage attributes: {[x for x in dir(res.first_stage) if not x.startswith('_')]}")
                    try:
                        # summary might be a property or a method
                        summary_attr = getattr(res.first_stage, 'summary', None)
                        if summary_attr is not None:
                            # Check if it's callable (method) or not (property)
                            if callable(summary_attr):
                                summary = summary_attr()  # Call if it's a method
                            else:
                                summary = summary_attr  # Use directly if it's a property
                            print(f"DEBUG: first_stage summary type: {type(summary)}")
                            if hasattr(summary, '__str__'):
                                print(f"DEBUG: first_stage summary:\n{summary}")
                    except Exception as e:
                        print(f"DEBUG: Could not get summary: {e}")
                    # Check individual attribute
                    if hasattr(res.first_stage, 'individual'):
                        print(f"DEBUG: first_stage.individual type: {type(res.first_stage.individual)}")
                        if res.first_stage.individual is not None:
                            print(f"DEBUG: first_stage.individual: {res.first_stage.individual}")
                    # Check diagnostics attribute
                    if hasattr(res.first_stage, 'diagnostics'):
                        print(f"DEBUG: first_stage.diagnostics type: {type(res.first_stage.diagnostics)}")
                        if res.first_stage.diagnostics is not None:
                            print(f"DEBUG: first_stage.diagnostics: {res.first_stage.diagnostics}")
        except Exception as e:
            error_str = str(e)
            print(f"ERROR in IV2SLS.from_formula: {type(e).__name__}: {error_str}")
            print(f"ERROR: Formula was: {linearmodels_formula}")
            
            # Check for collinearity/rank issues
            if "do not have full column rank" in error_str.lower() or "rank" in error_str.lower() and ("collinear" in error_str.lower() or "singular" in error_str.lower() or "instruments" in error_str.lower()):
                # Extract variable names from error if possible
                raise ValueError(f"COLLINEARITY_ERROR: The instruments or variables in your equation are collinear (linearly dependent). This means some variables are perfectly correlated or redundant.\n\nTo fix this:\n1. Check if any instruments are the same as your exogenous variables\n2. Remove one of the collinear variables\n3. Ensure you have enough unique instruments (at least as many as endogenous variables)\n\nFormula: {linearmodels_formula}")
            
            raise ValueError(f"Error estimating 2SLS model: {str(e)}. Formula: {linearmodels_formula}")

        # ===================================================================
        # Extract instrument diagnostics for 2SLS
        # ===================================================================
        instrument_diagnostics = {}
        
        try:
            # 1. First-stage diagnostics
            first_stage_results = []
            if hasattr(res, 'first_stage') and res.first_stage is not None:
                # Get endogenous variable names from parsed equation
                endog_names = endog_vars if endog_vars else []
                
                # Debug: Print first_stage type and available attributes
                print(f"DEBUG: first_stage type: {type(res.first_stage)}")
                print(f"DEBUG: first_stage dir: {[x for x in dir(res.first_stage) if not x.startswith('_')][:20]}")
                
                # FirstStageResults object - try accessing via summary or DataFrame
                for endog_name in endog_names:
                    fs_fstat = None
                    fs_pval = None
                    partial_r2 = None
                    # Note: Don't create a local variable named 'diagnostics' as it shadows the diagnostics() function
                    
                    try:
                        # Method 1: Access via 'individual' attribute (per-variable results)
                        if hasattr(res.first_stage, 'individual') and res.first_stage.individual is not None:
                            try:
                                individual = res.first_stage.individual
                                # individual might be a dict or have __getitem__
                                if hasattr(individual, '__getitem__'):
                                    try:
                                        stage_info = individual[endog_name]
                                        # Check for f_statistic and partial_r2
                                        if hasattr(stage_info, 'f_statistic'):
                                            fs_obj = stage_info.f_statistic
                                            if hasattr(fs_obj, 'stat'):
                                                fs_fstat = fs_obj.stat
                                            if hasattr(fs_obj, 'pval'):
                                                fs_pval = fs_obj.pval
                                        if hasattr(stage_info, 'partial_r2'):
                                            partial_r2 = stage_info.partial_r2
                                        # Also try partial_f_stat
                                        if hasattr(stage_info, 'partial_f_stat'):
                                            fs_obj = stage_info.partial_f_stat
                                            if hasattr(fs_obj, 'stat'):
                                                fs_fstat = fs_obj.stat
                                            if hasattr(fs_obj, 'pval'):
                                                fs_pval = fs_obj.pval
                                    except (KeyError, TypeError, IndexError):
                                        pass
                            except Exception as e:
                                print(f"DEBUG: Error accessing individual: {e}")
                        
                        # Method 2: Access via 'diagnostics' attribute
                        if fs_fstat is None and hasattr(res.first_stage, 'diagnostics') and res.first_stage.diagnostics is not None:
                            try:
                                first_stage_diagnostics = res.first_stage.diagnostics  # Renamed to avoid shadowing diagnostics() function
                                # first_stage_diagnostics might be a dict or DataFrame
                                if isinstance(first_stage_diagnostics, pd.DataFrame):
                                    if endog_name in first_stage_diagnostics.index:
                                        row = first_stage_diagnostics.loc[endog_name]
                                        # Look for F-statistic and partial R²
                                        for col in first_stage_diagnostics.columns:
                                            col_lower = str(col).lower()
                                            if 'f' in col_lower and 'stat' in col_lower:
                                                fs_fstat = row[col]
                                            if 'partial' in col_lower and 'r' in col_lower:
                                                partial_r2 = row[col]
                                elif hasattr(first_stage_diagnostics, '__getitem__'):
                                    try:
                                        diag_info = first_stage_diagnostics[endog_name]
                                        if hasattr(diag_info, 'f_statistic'):
                                            fs_obj = diag_info.f_statistic
                                            if hasattr(fs_obj, 'stat'):
                                                fs_fstat = fs_obj.stat
                                            if hasattr(fs_obj, 'pval'):
                                                fs_pval = fs_obj.pval
                                        if hasattr(diag_info, 'partial_r2'):
                                            partial_r2 = diag_info.partial_r2
                                    except (KeyError, TypeError):
                                        pass
                            except Exception as e:
                                print(f"DEBUG: Error accessing diagnostics: {e}")
                        
                        # Method 3: Try to get summary as DataFrame or access its properties
                        if fs_fstat is None and hasattr(res.first_stage, 'summary'):
                            try:
                                # summary might be a property or a method
                                summary_attr = getattr(res.first_stage, 'summary', None)
                                if summary_attr is None:
                                    raise AttributeError("summary is None")
                                
                                # Check if it's callable (method) or not (property)
                                if callable(summary_attr):
                                    summary = summary_attr()  # Call if it's a method
                                else:
                                    summary = summary_attr  # Use directly if it's a property
                                
                                # If it's a DataFrame, extract values
                                if isinstance(summary, pd.DataFrame):
                                    if endog_name in summary.index:
                                        row = summary.loc[endog_name]
                                        # Look for F-statistic and partial R² columns
                                        for col in summary.columns:
                                            col_lower = str(col).lower()
                                            if 'f' in col_lower and 'stat' in col_lower and fs_fstat is None:
                                                fs_fstat = row[col]
                                            if 'partial' in col_lower and 'r' in col_lower and '2' in col_lower and partial_r2 is None:
                                                partial_r2 = row[col]
                            except Exception as e:
                                print(f"DEBUG: Error accessing summary: {e}")
                        
                        # Method 2: Try accessing as DataFrame directly
                        if fs_fstat is None and hasattr(res.first_stage, 'to_frame'):
                            try:
                                to_frame_attr = getattr(res.first_stage, 'to_frame', None)
                                if to_frame_attr is None:
                                    raise AttributeError("to_frame is None")
                                
                                # Check if it's callable (method) or not (property)
                                if callable(to_frame_attr):
                                    df = to_frame_attr()  # Call if it's a method
                                else:
                                    df = to_frame_attr  # Use directly if it's a property
                                
                                if isinstance(df, pd.DataFrame) and endog_name in df.index:
                                    row = df.loc[endog_name]
                                    # Look for relevant columns
                                    for col in df.columns:
                                        col_lower = str(col).lower()
                                        if 'f' in col_lower and 'stat' in col_lower:
                                            fs_fstat = row[col]
                                        if 'partial' in col_lower and 'r' in col_lower:
                                            partial_r2 = row[col]
                            except Exception as e:
                                print(f"DEBUG: Error converting to DataFrame: {e}")
                        
                        # Method 3: Try dictionary-like access with variable name
                        if fs_fstat is None and hasattr(res.first_stage, '__getitem__'):
                            try:
                                stage = res.first_stage[endog_name]
                                # Check if stage has the attributes directly
                                if hasattr(stage, 'f_statistic'):
                                    fs_obj = stage.f_statistic
                                    if hasattr(fs_obj, 'stat'):
                                        fs_fstat = fs_obj.stat
                                    if hasattr(fs_obj, 'pval'):
                                        fs_pval = fs_obj.pval
                                if hasattr(stage, 'partial_r2'):
                                    partial_r2 = stage.partial_r2
                                # Also try accessing as attributes directly on stage
                                if hasattr(stage, 'partial_f_stat'):
                                    fs_obj = stage.partial_f_stat
                                    if hasattr(fs_obj, 'stat'):
                                        fs_fstat = fs_obj.stat
                                    if hasattr(fs_obj, 'pval'):
                                        fs_pval = fs_obj.pval
                            except (KeyError, TypeError, IndexError) as e:
                                print(f"DEBUG: Error with __getitem__ access: {e}")
                        
                        # Method 4: Try accessing attributes directly on first_stage
                        if fs_fstat is None:
                            # Try common attribute names
                            for attr_name in ['partial_f_stat', 'f_statistic', 'f_stat', 'partial_f']:
                                if hasattr(res.first_stage, attr_name):
                                    try:
                                        fs_obj = getattr(res.first_stage, attr_name)
                                        if hasattr(fs_obj, 'stat'):
                                            fs_fstat = fs_obj.stat
                                        if hasattr(fs_obj, 'pval'):
                                            fs_pval = fs_obj.pval
                                        break
                                    except:
                                        pass
                            
                            # Try partial_r2
                            for attr_name in ['partial_r2', 'partial_rsquared', 'partial_r_squared']:
                                if hasattr(res.first_stage, attr_name):
                                    try:
                                        partial_r2 = getattr(res.first_stage, attr_name)
                                        break
                                    except:
                                        pass
                        
                        # Method 5: If only one endogenous variable, try accessing by index
                        if fs_fstat is None and len(endog_names) == 1:
                            try:
                                # Try accessing first element if it's iterable
                                if hasattr(res.first_stage, '__iter__') and not isinstance(res.first_stage, str):
                                    items = list(res.first_stage)
                                    if len(items) > 0:
                                        stage = items[0]
                                        if hasattr(stage, 'f_statistic'):
                                            fs_obj = stage.f_statistic
                                            if hasattr(fs_obj, 'stat'):
                                                fs_fstat = fs_obj.stat
                                            if hasattr(fs_obj, 'pval'):
                                                fs_pval = fs_obj.pval
                                        if hasattr(stage, 'partial_r2'):
                                            partial_r2 = stage.partial_r2
                            except Exception as e:
                                print(f"DEBUG: Error with iteration access: {e}")
                        
                    except Exception as inner_e:
                        print(f"Warning: Error accessing first-stage for {endog_name}: {inner_e}")
                        import traceback
                        traceback.print_exc()
                    
                    first_stage_results.append({
                        'endogenous_var': str(endog_name),
                        'f_statistic': float(fs_fstat) if fs_fstat is not None else None,
                        'f_pvalue': float(fs_pval) if fs_pval is not None else None,
                        'partial_r2': float(partial_r2) if partial_r2 is not None else None,
                    })
            
            instrument_diagnostics['first_stage'] = first_stage_results
            
            # 2. Weak instrument test (Sanderson-Windmeijer F-test)
            # Note: This might be in first_stage.diagnostics or accessed differently
            try:
                # Try accessing from first_stage diagnostics
                weak_instrument = None
                if hasattr(res, 'first_stage') and res.first_stage is not None:
                    if hasattr(res.first_stage, 'diagnostics'):
                        diag = res.first_stage.diagnostics
                        # Check if diagnostics has weak instrument info
                        if hasattr(diag, 'weak_instrument') or (isinstance(diag, dict) and 'weak_instrument' in diag):
                            weak_instrument = diag.get('weak_instrument') if isinstance(diag, dict) else getattr(diag, 'weak_instrument', None)
                
                # Also try direct access on res (for some versions)
                if weak_instrument is None and hasattr(res, 'weak_instrument_test'):
                    weak_instrument_attr = getattr(res, 'weak_instrument_test', None)
                    if weak_instrument_attr is not None:
                        # Check if it's callable (method) or not (property)
                        if callable(weak_instrument_attr):
                            try:
                                weak_instrument = weak_instrument_attr()  # Call if it's a method
                            except Exception:
                                weak_instrument = None
                        else:
                            weak_instrument = weak_instrument_attr  # Use directly if it's a property
                
                if weak_instrument is not None:
                    if hasattr(weak_instrument, 'stat'):
                        instrument_diagnostics['weak_instrument'] = {
                            'statistic': float(weak_instrument.stat) if weak_instrument.stat is not None else None,
                            'pvalue': float(weak_instrument.pval) if hasattr(weak_instrument, 'pval') and weak_instrument.pval is not None else None,
                        }
                    else:
                        instrument_diagnostics['weak_instrument'] = None
                else:
                    instrument_diagnostics['weak_instrument'] = None
            except Exception as e:
                instrument_diagnostics['weak_instrument'] = None
                print(f"Warning: Weak instrument test not available: {e}")
            
            # 3. Overidentification test (Hansen J or Sargan)
            # Only available when #instruments > #endogenous variables
            try:
                # First, check if we actually have more instruments than endogenous variables
                num_instruments = len(instruments)
                num_endogenous = len(endog_vars)
                
                print(f"DEBUG: Overidentification check - Instruments: {num_instruments}, Endogenous: {num_endogenous}")
                
                if num_instruments <= num_endogenous:
                    # Model is exactly identified or underidentified - overidentification test not available
                    instrument_diagnostics['overidentification'] = {
                        'available': False,
                        'reason': f'Model is exactly identified (number of instruments ({num_instruments}) equals number of endogenous variables ({num_endogenous}))' if num_instruments == num_endogenous else f'Model is underidentified (number of instruments ({num_instruments}) is less than number of endogenous variables ({num_endogenous}))'
                    }
                else:
                    # Model is overidentified - try to get the test
                    # In linearmodels, the overidentification test is accessed via res.j_stat
                    overid_test = None
                    test_name = 'Hansen J'
                    
                    # Debug: Print all attributes of res to see what's available
                    print(f"DEBUG: Checking for overidentification test. res type: {type(res)}")
                    all_attrs = [x for x in dir(res) if not x.startswith('_')]
                    print(f"DEBUG: All res attributes: {all_attrs}")
                    j_stat_related = [x for x in all_attrs if 'j' in x.lower() or 'overid' in x.lower() or 'sargan' in x.lower() or 'hansen' in x.lower()]
                    print(f"DEBUG: J-stat related attributes: {j_stat_related}")
                    
                    # Try overidentification test attributes
                    # Based on debug output, linearmodels provides 'sargan' and 'wooldridge_overid'
                    # First try on robust result, then on non-robust if available
                    for res_to_check, res_label in [(res, 'robust'), (res_nonrobust, 'non-robust')]:
                        if res_to_check is None:
                            continue
                        
                        # Try sargan first (most common)
                        for attr_name in ['sargan', 'wooldridge_overid', 'j_stat', 'overidentification_test', 'overid_test']:
                            if hasattr(res_to_check, attr_name):
                                try:
                                    test_attr = getattr(res_to_check, attr_name, None)
                                    print(f"DEBUG: {attr_name} attribute exists on {res_label} result, type: {type(test_attr)}")
                                    if test_attr is not None:
                                        # Check if it's callable (method) or not (property)
                                        if callable(test_attr):
                                            overid_test = test_attr()
                                            print(f"DEBUG: Called {attr_name}() as method on {res_label}, result type: {type(overid_test)}")
                                        else:
                                            overid_test = test_attr
                                            print(f"DEBUG: Used {attr_name} as property on {res_label}, type: {type(overid_test)}")
                                        
                                        if overid_test is not None:
                                            print(f"DEBUG: {attr_name} result attributes: {[x for x in dir(overid_test) if not x.startswith('_')]}")
                                            # Try to access common attributes directly
                                            if hasattr(overid_test, 'stat'):
                                                print(f"DEBUG: overid_test.stat = {getattr(overid_test, 'stat', None)}")
                                            if hasattr(overid_test, 'statistic'):
                                                print(f"DEBUG: overid_test.statistic = {getattr(overid_test, 'statistic', None)}")
                                            if hasattr(overid_test, 'pval'):
                                                print(f"DEBUG: overid_test.pval = {getattr(overid_test, 'pval', None)}")
                                            if hasattr(overid_test, 'pvalue'):
                                                print(f"DEBUG: overid_test.pvalue = {getattr(overid_test, 'pvalue', None)}")
                                            break  # Found it, exit inner loop
                                except Exception as e:
                                    import traceback
                                    print(f"DEBUG: Error accessing {attr_name} on {res_label}: {e}")
                                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                                    continue
                        
                        if overid_test is not None:
                            break  # Found it, exit outer loop
                    
                    if overid_test is not None:
                        # Extract statistic and p-value
                        statistic = None
                        pvalue = None
                        
                        # Try common attribute names for statistic
                        for stat_attr in ['stat', 'statistic', 'statistic_value', 'value']:
                            if hasattr(overid_test, stat_attr):
                                stat_val = getattr(overid_test, stat_attr)
                                if stat_val is not None:
                                    statistic = float(stat_val)
                                    break
                        
                        # Try common attribute names for p-value
                        for pval_attr in ['pval', 'pvalue', 'p_value', 'pv']:
                            if hasattr(overid_test, pval_attr):
                                pval_val = getattr(overid_test, pval_attr)
                                if pval_val is not None:
                                    pvalue = float(pval_val)
                                    break
                        
                        # Try to get test name
                        for name_attr in ['test_name', 'name', 'test']:
                            if hasattr(overid_test, name_attr):
                                name_val = getattr(overid_test, name_attr)
                                if name_val is not None:
                                    test_name = str(name_val)
                                    break
                        
                        if statistic is not None or pvalue is not None:
                            instrument_diagnostics['overidentification'] = {
                                'available': True,
                                'statistic': statistic,
                                'pvalue': pvalue,
                                'test_name': test_name,
                            }
                        else:
                            # Test object exists but we can't extract values
                            print(f"DEBUG: Overidentification test object found but cannot extract statistic/pvalue. Object: {overid_test}, type: {type(overid_test)}")
                            instrument_diagnostics['overidentification'] = {
                                'available': False,
                                'reason': f'Overidentification test object found but cannot extract statistic/pvalue (object type: {type(overid_test).__name__})'
                            }
                    else:
                        # Debug: print available attributes on res
                        print(f"DEBUG: Overidentification test not found. Available attributes on res: {[x for x in dir(res) if not x.startswith('_')]}")
                        j_stat_related = [x for x in dir(res) if not x.startswith('_') and ('overid' in x.lower() or 'j' in x.lower() or 'sargan' in x.lower() or 'hansen' in x.lower())]
                        print(f"DEBUG: J-stat related attributes: {j_stat_related}")
                        
                        # Try to get from summary if available
                        if hasattr(res, 'summary'):
                            try:
                                summary = res.summary
                                print(f"DEBUG: Summary type: {type(summary)}")
                                if hasattr(summary, 'as_text'):
                                    summary_text = summary.as_text()
                                    print(f"DEBUG: Summary text (first 2000 chars):\n{summary_text[:2000]}")
                                elif hasattr(summary, '__str__'):
                                    summary_str = str(summary)
                                    print(f"DEBUG: Summary string (first 2000 chars):\n{summary_str[:2000]}")
                            except Exception as e:
                                print(f"DEBUG: Error accessing summary: {e}")
                        
                        instrument_diagnostics['overidentification'] = {
                            'available': False,
                            'reason': f'Overidentification test not available from model (model is overidentified with {num_instruments} instruments for {num_endogenous} endogenous variables, but test could not be extracted. Check console for debug output.)'
                        }
            except Exception as e:
                instrument_diagnostics['overidentification'] = {
                    'available': False,
                    'reason': f'Error checking overidentification: {str(e)}'
                }
                print(f"Info: Overidentification test not available: {e}")
            
            # 4. Endogeneity test (Durbin-Wu-Hausman)
            try:
                wu_hausman_attr = getattr(res, 'wu_hausman', None)
                if wu_hausman_attr is not None:
                    # Check if it's callable (method) or not (property)
                    if callable(wu_hausman_attr):
                        try:
                            wu_hausman = wu_hausman_attr()  # Call if it's a method
                        except Exception:
                            wu_hausman = None
                    else:
                        wu_hausman = wu_hausman_attr  # Use directly if it's a property
                else:
                    wu_hausman = None
                    
                if wu_hausman is not None:
                    if hasattr(wu_hausman, 'stat'):
                        instrument_diagnostics['endogeneity_test'] = {
                            'statistic': float(wu_hausman.stat) if wu_hausman.stat is not None else None,
                            'pvalue': float(wu_hausman.pval) if hasattr(wu_hausman, 'pval') and wu_hausman.pval is not None else None,
                        }
                    else:
                        instrument_diagnostics['endogeneity_test'] = None
                else:
                    instrument_diagnostics['endogeneity_test'] = None
            except Exception as e:
                instrument_diagnostics['endogeneity_test'] = None
                print(f"Warning: Endogeneity test not available: {e}")
                
        except Exception as e:
            print(f"Warning: Could not extract all instrument diagnostics: {e}")
            instrument_diagnostics['error'] = str(e)

        # Convert all to numpy arrays to ensure proper types
        # Safely access params and other attributes
        params_attr = getattr(res, 'params', None)
        if params_attr is None:
            raise ValueError("Model result does not have params attribute")
        
        # Check if params is callable (method) or a property
        if callable(params_attr):
            params_data = params_attr()
        else:
            params_data = params_attr
        
        # Safely access other attributes
        std_errors_attr = getattr(res, 'std_errors', None)
        tstats_attr = getattr(res, 'tstats', None)
        pvalues_attr = getattr(res, 'pvalues', None)
        
        std_errors = std_errors_attr() if callable(std_errors_attr) else (std_errors_attr if std_errors_attr is not None else None)
        tstats = tstats_attr() if callable(tstats_attr) else (tstats_attr if tstats_attr is not None else None)
        pvalues = pvalues_attr() if callable(pvalues_attr) else (pvalues_attr if pvalues_attr is not None else None)
        
        # Ensure we have valid data
        if params_data is None:
            raise ValueError("Model params is None")
        
        params = pd.DataFrame({
            "variable": params_data.index if hasattr(params_data, 'index') else range(len(params_data)),
            "param": np.asarray(params_data.values if hasattr(params_data, 'values') else params_data),
            "std_err": np.asarray(std_errors.values if std_errors is not None and hasattr(std_errors, 'values') else (std_errors if std_errors is not None else np.zeros(len(params_data)))),
            "t": np.asarray(tstats.values if tstats is not None and hasattr(tstats, 'values') else (tstats if tstats is not None else np.zeros(len(params_data)))),
            "p": np.asarray(pvalues.values if pvalues is not None and hasattr(pvalues, 'values') else (pvalues if pvalues is not None else np.zeros(len(params_data))))
        })
        
        # Add instrument diagnostics to params or return separately
        # We'll add it to the results dictionary later

        # Get dependent variable data - IVData object structure
        # The simplest approach: reconstruct y from fitted_values + residuals
        # This is always accurate: y = y_hat + residuals
        # Safely access fitted_values and resids
        fitted_values_attr = getattr(res, 'fitted_values', None)
        resids_attr = getattr(res, 'resids', None)
        
        if fitted_values_attr is None:
            raise ValueError("Model result does not have fitted_values attribute")
        if resids_attr is None:
            raise ValueError("Model result does not have resids attribute")
        
        # Check if they're callable (methods) or properties
        y_hat = np.asarray(fitted_values_attr() if callable(fitted_values_attr) else fitted_values_attr)
        residuals = np.asarray(resids_attr() if callable(resids_attr) else resids_attr)
        y_data = y_hat + residuals
        
        # Get exogenous data for diagnostics
        # Reconstruct X from original data using parsed variables
        # This ensures we have proper regressors for Breusch-Pagan test
        n_obs = len(y_data)
        X_data = None
        
        try:
            # Reconstruct X from original data using the parsed variables
            # We need: constant + exogenous variables + endogenous variables
            X_cols = ['const']  # Start with constant
            
            # Add exogenous variables
            for var in exog_vars:
                if var in data.columns:
                    X_cols.append(var)
            
            # Add endogenous variables (they're still in the model)
            for var in endog_vars:
                if var in data.columns:
                    X_cols.append(var)
            
            # Build X matrix from data
            if len(X_cols) > 1:  # Need at least constant + one regressor
                X_data = data[X_cols].values.astype(np.float64)
            else:
                # Fallback: constant + first available variable
                X_data = np.ones((n_obs, 1), dtype=np.float64)
                if len(data.columns) > 0:
                    first_col = data.columns[0]
                    if first_col != dependent:
                        X_data = np.column_stack([np.ones(n_obs, dtype=np.float64), 
                                                  data[first_col].values.astype(np.float64)])
        except Exception as e:
            # If reconstruction fails, create constant + first variable
            print(f"Warning: Could not reconstruct X_data for diagnostics: {e}")
            X_data = np.ones((n_obs, 1), dtype=np.float64)
            if len(data.columns) > 0:
                try:
                    first_col = [c for c in data.columns if c != dependent][0] if len(data.columns) > 1 else data.columns[0]
                    X_data = np.column_stack([np.ones(n_obs, dtype=np.float64), 
                                              data[first_col].values.astype(np.float64)])
                except:
                    pass
        
        # Ensure X_data has at least constant + one regressor for Breusch-Pagan
        if X_data is None or X_data.shape[1] < 2:
            # Create constant + first available variable
            X_data = np.ones((n_obs, 1), dtype=np.float64)
            if len(data.columns) > 0:
                try:
                    first_col = [c for c in data.columns if c != dependent][0] if len(data.columns) > 1 else data.columns[0]
                    X_data = np.column_stack([np.ones(n_obs, dtype=np.float64), 
                                              data[first_col].values.astype(np.float64)])
                except:
                    # Last resort: constant + zeros (will fail BP test but won't crash)
                    X_data = np.column_stack([np.ones(n_obs, dtype=np.float64), 
                                              np.zeros(n_obs, dtype=np.float64)])
        
        # Ensure it's 2D and float64
        if X_data.ndim == 1:
            X_data = X_data.reshape(-1, 1)
        X_data = X_data.astype(np.float64)

        diag = diagnostics(
            y_data,
            y_hat,
            X_data,
            residuals,
            name="2SLS"
        )

        # Return results with instrument diagnostics
        return res, params, pd.DataFrame([diag]), instrument_diagnostics

    # ===================================================================
    # 3SLS
    # ===================================================================
    if method == "3SLS":
        # 3SLS requires multiple equations (system of equations)
        if len(formulas) < 2:
            raise ValueError(f"EQUATION_COUNT_ERROR: 3SLS (Three-Stage Least Squares) requires at least 2 equations, but you provided {len(formulas)} equation(s).\n\n3SLS is designed for systems of simultaneous equations with endogeneity.\n\nTo fix this:\n1. Add more equations (one per line) to create a system\n2. Or use 2SLS if you only have one equation with endogeneity\n3. Or use SUR if you have multiple equations without endogeneity\n\nExample for 3SLS:\ny1 ~ x1 + [x2 ~ z1 + z2]\ny2 ~ x1 + x2 + [x3 ~ z3 + z4]")
        
        eq_dict = {f"eq{i+1}": f for i, f in enumerate(formulas)}

        try:
            model = IV3SLS.from_formula(eq_dict, data=data)
            res = model.fit()
        except Exception as e:
            error_str = str(e)
            print(f"ERROR in IV3SLS.from_formula: {type(e).__name__}: {error_str}")
            
            # Check for collinearity/rank issues
            if "do not have full column rank" in error_str.lower() or "rank" in error_str.lower() and ("collinear" in error_str.lower() or "singular" in error_str.lower() or "instruments" in error_str.lower()):
                raise ValueError(f"COLLINEARITY_ERROR: The instruments or variables in your equations are collinear (linearly dependent). This means some variables are perfectly correlated or redundant.\n\nTo fix this:\n1. Check if any instruments are the same as your exogenous variables\n2. Remove one of the collinear variables from your equations\n3. Ensure you have enough unique instruments (at least as many as endogenous variables in each equation)\n\nEquations: {formulas}")
            
            raise

        # param table - handle MultiIndex properly
        # For 3SLS, res.params is typically a Series with MultiIndex (equation, variable)
        print(f"DEBUG: 3SLS res.params type: {type(res.params)}")
        print(f"DEBUG: 3SLS res.params index type: {type(res.params.index) if hasattr(res.params, 'index') else 'N/A'}")
        if hasattr(res.params, 'index'):
            print(f"DEBUG: 3SLS res.params index names: {res.params.index.names}")
            print(f"DEBUG: 3SLS res.params first few indices: {list(res.params.index[:5])}")
        
        try:
            # Use reset_index() to convert MultiIndex Series to DataFrame - this is the most reliable method
            params_df = res.params.reset_index()
            print(f"DEBUG: After reset_index(), params_df shape: {params_df.shape}")
            print(f"DEBUG: params_df columns: {params_df.columns.tolist()}")
            print(f"DEBUG: params_df head:\n{params_df.head(10)}")
            
            # The reset_index() can give different structures:
            # 1. [level_0, level_1, 0] - when MultiIndex levels are separate
            # 2. ['index', 'params'] - when MultiIndex is in a single 'index' column
            # 3. Other variations
            
            print(f"DEBUG: params_df columns: {params_df.columns.tolist()}")
            print(f"DEBUG: params_df head:\n{params_df.head(10)}")
            
            # Handle case where index is in a single column (like ['index', 'params'])
            if 'index' in params_df.columns and len(params_df.columns) == 2:
                # The 'index' column contains tuples like (eq, var)
                param_col = [c for c in params_df.columns if c != 'index'][0]
                print(f"DEBUG: Found 'index' column structure, param_col: {param_col}")
                
                params_data = []
                for _, row in params_df.iterrows():
                    index_val = row['index']
                    param_val = float(row[param_col]) if pd.notna(row[param_col]) else None
                    
                    # Extract equation and variable from index
                    if isinstance(index_val, tuple) and len(index_val) == 2:
                        eq, var = index_val
                    elif isinstance(index_val, (list, pd.Index)) and len(index_val) == 2:
                        eq, var = index_val[0], index_val[1]
                    else:
                        # Try to parse as string representation of tuple
                        try:
                            if isinstance(index_val, str) and index_val.startswith('(') and index_val.endswith(')'):
                                # Parse string like "(eq1, const)" 
                                parts = index_val.strip('()').split(',')
                                eq = parts[0].strip().strip("'\"")
                                var = parts[1].strip().strip("'\"") if len(parts) > 1 else str(index_val)
                            else:
                                # Fallback: use the index value as variable, equation unknown
                                eq = "eq1"  # Default equation name
                                var = str(index_val)
                        except:
                            eq = "eq1"
                            var = str(index_val)
                    
                    # Try to get std_err, t, and p from the original Series using the index
                    std_err = None
                    t_stat = None
                    p_val = None
                    
                    # Use the original index to look up values
                    if isinstance(index_val, tuple) and len(index_val) == 2:
                        idx_key = index_val
                    elif hasattr(index_val, '__getitem__') and hasattr(index_val, '__len__') and len(index_val) == 2:
                        idx_key = (index_val[0], index_val[1])
                    else:
                        idx_key = None
                    
                    print(f"DEBUG: Looking up stats for eq={eq}, var={var}, index_val={index_val}, idx_key={idx_key}")
                    
                    # Debug: Check what attributes res has
                    print(f"DEBUG: res attributes with 'std' or 't' or 'p': {[x for x in dir(res) if 'std' in x.lower() or 'tstat' in x.lower() or 'pval' in x.lower()]}")
                    
                    # Try multiple ways to access std_errors, tstats, pvalues
                    # Method 1: Direct attribute access
                    if idx_key is not None:
                        # Try std_errors
                        if hasattr(res, 'std_errors'):
                            try:
                                if idx_key in res.std_errors.index:
                                    std_err = float(res.std_errors.loc[idx_key])
                                    print(f"DEBUG: Found std_err via direct loc: {std_err}")
                            except Exception as e:
                                print(f"DEBUG: Error accessing std_errors.loc[{idx_key}]: {e}")
                        
                        # Try tstats
                        if hasattr(res, 'tstats'):
                            try:
                                if idx_key in res.tstats.index:
                                    t_stat = float(res.tstats.loc[idx_key])
                                    print(f"DEBUG: Found t_stat via direct loc: {t_stat}")
                            except Exception as e:
                                print(f"DEBUG: Error accessing tstats.loc[{idx_key}]: {e}")
                        
                        # Try pvalues
                        if hasattr(res, 'pvalues'):
                            try:
                                if idx_key in res.pvalues.index:
                                    p_val = float(res.pvalues.loc[idx_key])
                                    print(f"DEBUG: Found p_val via direct loc: {p_val}")
                            except Exception as e:
                                print(f"DEBUG: Error accessing pvalues.loc[{idx_key}]: {e}")
                    
                    # Method 2: Use reset_index() and match by index value
                    if std_err is None or t_stat is None or p_val is None:
                        print(f"DEBUG: Trying reset_index() approach for missing stats")
                        try:
                            if std_err is None and hasattr(res, 'std_errors'):
                                std_errors_df = res.std_errors.reset_index() if hasattr(res.std_errors, 'reset_index') else None
                                if std_errors_df is not None:
                                    print(f"DEBUG: std_errors_df columns: {std_errors_df.columns.tolist()}")
                                    if 'index' in std_errors_df.columns:
                                        # Match by index value
                                        match = std_errors_df[std_errors_df['index'] == index_val]
                                        if len(match) > 0:
                                            std_err_col = [c for c in match.columns if c != 'index'][0]
                                            std_err = float(match.iloc[0][std_err_col]) if pd.notna(match.iloc[0][std_err_col]) else None
                                            print(f"DEBUG: Found std_err via reset_index: {std_err}")
                                    elif len(std_errors_df.columns) >= 2:
                                        # Try matching by first two columns (equation, variable)
                                        eq_col = std_errors_df.columns[0]
                                        var_col = std_errors_df.columns[1] if len(std_errors_df.columns) > 1 else None
                                        if var_col:
                                            match = std_errors_df[(std_errors_df[eq_col] == eq) & (std_errors_df[var_col] == var)]
                                            if len(match) > 0:
                                                std_err_col = [c for c in match.columns if c not in [eq_col, var_col]][0]
                                                std_err = float(match.iloc[0][std_err_col]) if pd.notna(match.iloc[0][std_err_col]) else None
                                                print(f"DEBUG: Found std_err via column match: {std_err}")
                        except Exception as e:
                            print(f"DEBUG: Error in reset_index approach for std_err: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        try:
                            if t_stat is None and hasattr(res, 'tstats'):
                                tstats_df = res.tstats.reset_index() if hasattr(res.tstats, 'reset_index') else None
                                if tstats_df is not None:
                                    print(f"DEBUG: tstats_df columns: {tstats_df.columns.tolist()}")
                                    if 'index' in tstats_df.columns:
                                        match = tstats_df[tstats_df['index'] == index_val]
                                        if len(match) > 0:
                                            t_col = [c for c in match.columns if c != 'index'][0]
                                            t_stat = float(match.iloc[0][t_col]) if pd.notna(match.iloc[0][t_col]) else None
                                            print(f"DEBUG: Found t_stat via reset_index: {t_stat}")
                                    elif len(tstats_df.columns) >= 2:
                                        eq_col = tstats_df.columns[0]
                                        var_col = tstats_df.columns[1] if len(tstats_df.columns) > 1 else None
                                        if var_col:
                                            match = tstats_df[(tstats_df[eq_col] == eq) & (tstats_df[var_col] == var)]
                                            if len(match) > 0:
                                                t_col = [c for c in match.columns if c not in [eq_col, var_col]][0]
                                                t_stat = float(match.iloc[0][t_col]) if pd.notna(match.iloc[0][t_col]) else None
                                                print(f"DEBUG: Found t_stat via column match: {t_stat}")
                        except Exception as e:
                            print(f"DEBUG: Error in reset_index approach for t_stat: {e}")
                        
                        try:
                            if p_val is None and hasattr(res, 'pvalues'):
                                pvalues_df = res.pvalues.reset_index() if hasattr(res.pvalues, 'reset_index') else None
                                if pvalues_df is not None:
                                    print(f"DEBUG: pvalues_df columns: {pvalues_df.columns.tolist()}")
                                    if 'index' in pvalues_df.columns:
                                        match = pvalues_df[pvalues_df['index'] == index_val]
                                        if len(match) > 0:
                                            p_col = [c for c in match.columns if c != 'index'][0]
                                            p_val = float(match.iloc[0][p_col]) if pd.notna(match.iloc[0][p_col]) else None
                                            print(f"DEBUG: Found p_val via reset_index: {p_val}")
                                    elif len(pvalues_df.columns) >= 2:
                                        eq_col = pvalues_df.columns[0]
                                        var_col = pvalues_df.columns[1] if len(pvalues_df.columns) > 1 else None
                                        if var_col:
                                            match = pvalues_df[(pvalues_df[eq_col] == eq) & (pvalues_df[var_col] == var)]
                                            if len(match) > 0:
                                                p_col = [c for c in match.columns if c not in [eq_col, var_col]][0]
                                                p_val = float(match.iloc[0][p_col]) if pd.notna(match.iloc[0][p_col]) else None
                                                print(f"DEBUG: Found p_val via column match: {p_val}")
                        except Exception as e:
                            print(f"DEBUG: Error in reset_index approach for p_val: {e}")
                    
                    params_data.append({
                        "equation": str(eq),
                        "variable": str(var),
                        "param": param_val,
                        "std_err": std_err,
                        "t": t_stat,
                        "p": p_val
                    })
                
                print(f"DEBUG: Built {len(params_data)} parameter rows from 'index' column structure")
            elif len(params_df.columns) >= 3:
                # Standard case: level_0 (equation), level_1 (variable), 0 (param value)
                if 'level_0' in params_df.columns and 'level_1' in params_df.columns:
                    eq_col = 'level_0'
                    var_col = 'level_1'
                    param_col = [c for c in params_df.columns if c not in ['level_0', 'level_1']][0]
                else:
                    # Use first three columns
                    eq_col = params_df.columns[0]
                    var_col = params_df.columns[1]
                    param_col = params_df.columns[2]
                
                print(f"DEBUG: Using columns - eq: {eq_col}, var: {var_col}, param: {param_col}")
                
                # Also reset index for std_errors, tstats, and pvalues to match
                std_errors_df = res.std_errors.reset_index() if hasattr(res.std_errors, 'reset_index') else None
                tstats_df = res.tstats.reset_index() if hasattr(res.tstats, 'reset_index') else None
                pvalues_df = res.pvalues.reset_index() if hasattr(res.pvalues, 'reset_index') else None
                
                if std_errors_df is not None:
                    print(f"DEBUG: std_errors_df columns: {std_errors_df.columns.tolist()}")
                if tstats_df is not None:
                    print(f"DEBUG: tstats_df columns: {tstats_df.columns.tolist()}")
                if pvalues_df is not None:
                    print(f"DEBUG: pvalues_df columns: {pvalues_df.columns.tolist()}")
                
                # Build params_data by merging information
                params_data = []
                for idx, row in params_df.iterrows():
                    eq = str(row[eq_col])
                    var = str(row[var_col])
                    param_val = float(row[param_col]) if pd.notna(row[param_col]) else None
                    
                    # Try to find matching std_err, t, and p using the same column structure
                    std_err = None
                    t_stat = None
                    p_val = None
                    
                    if std_errors_df is not None and len(std_errors_df) > 0:
                        try:
                            # Match by equation and variable
                            match = std_errors_df[(std_errors_df[eq_col] == eq) & (std_errors_df[var_col] == var)]
                            if len(match) > 0:
                                std_err_col = [c for c in match.columns if c not in [eq_col, var_col]][0]
                                std_err_val = match.iloc[0][std_err_col]
                                std_err = float(std_err_val) if pd.notna(std_err_val) else None
                        except Exception as e:
                            print(f"DEBUG: Error extracting std_err for {eq}, {var}: {e}")
                    
                    if tstats_df is not None and len(tstats_df) > 0:
                        try:
                            match = tstats_df[(tstats_df[eq_col] == eq) & (tstats_df[var_col] == var)]
                            if len(match) > 0:
                                t_col = [c for c in match.columns if c not in [eq_col, var_col]][0]
                                t_val = match.iloc[0][t_col]
                                t_stat = float(t_val) if pd.notna(t_val) else None
                        except Exception as e:
                            print(f"DEBUG: Error extracting t_stat for {eq}, {var}: {e}")
                    
                    if pvalues_df is not None and len(pvalues_df) > 0:
                        try:
                            match = pvalues_df[(pvalues_df[eq_col] == eq) & (pvalues_df[var_col] == var)]
                            if len(match) > 0:
                                p_col = [c for c in match.columns if c not in [eq_col, var_col]][0]
                                p_val_val = match.iloc[0][p_col]
                                p_val = float(p_val_val) if pd.notna(p_val_val) else None
                        except Exception as e:
                            print(f"DEBUG: Error extracting p_val for {eq}, {var}: {e}")
                    
                    params_data.append({
                        "equation": eq,
                        "variable": var,
                        "param": param_val,
                        "std_err": std_err,
                        "t": t_stat,
                        "p": p_val
                    })
                
                print(f"DEBUG: Built {len(params_data)} parameter rows")
            else:
                raise ValueError(f"Unexpected params_df structure after reset_index. Columns: {params_df.columns.tolist()}, shape: {params_df.shape}")
        except Exception as e:
            import traceback
            print(f"DEBUG: Error parsing 3SLS params: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error parsing 3SLS parameters: {str(e)}")
        
        params = pd.DataFrame(params_data)
        
        # Debug: Print params DataFrame structure
        print(f"DEBUG: Final 3SLS params DataFrame shape: {params.shape}")
        print(f"DEBUG: Final 3SLS params DataFrame columns: {params.columns.tolist()}")
        if len(params) > 0:
            print(f"DEBUG: Final params DataFrame head:\n{params.head(10).to_string()}")
            print(f"DEBUG: Sample variable names: {params['variable'].head(10).tolist()}")
            print(f"DEBUG: Sample equation names: {params['equation'].head(10).tolist()}")
            print(f"DEBUG: Non-null std_err count: {params['std_err'].notna().sum()}")
            print(f"DEBUG: Non-null t count: {params['t'].notna().sum()}")
            print(f"DEBUG: Non-null p count: {params['p'].notna().sum()}")
        else:
            print(f"DEBUG: WARNING: params DataFrame is empty!")
        
        # Ensure all required columns exist with correct names
        required_cols = ['equation', 'variable', 'param', 'std_err', 't', 'p']
        for col in required_cols:
            if col not in params.columns:
                print(f"WARNING: Missing column '{col}' in params DataFrame. Adding with None values.")
                params[col] = None
        
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

        return res, params, pd.DataFrame(diag_list) if diag_list else pd.DataFrame(columns=["equation", "R2", "DW", "JB_stat", "JB_p", "BP_stat", "BP_p"]), None

    # This should never be reached due to validation above, but keep as safety
    #raise ValueError(f"Method must be 'SUR', '2SLS', or '3SLS'. Got: {method}")


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
                'error': 'PACKAGE_ERROR: linearmodels package is not installed. Please install it with: pip install linearmodels>=5.0.0',
                'has_results': False
            }
        
        try:
            # Get method from options, default to SUR, and normalize to uppercase with whitespace stripped
            method_raw = options.get('method', 'SUR') if options else 'SUR'
            method = str(method_raw).strip().upper()
            
            # Validate method
            valid_methods = ['SUR', '2SLS', '3SLS']
            if method not in valid_methods:
                return {
                    'error': f'Invalid method: "{method_raw}" (normalized: "{method}"). Method must be one of {valid_methods}.',
                    'has_results': False
                }
            
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
            # Need to extract individual variable names, not interaction terms
            all_vars = set()
            for eq in formulas:
                parsed = parse_equation(eq)
                # Add dependent variable
                all_vars.add(parsed['dependent'])
                
                # Process exog, endog, and instruments - split interaction terms
                for var_list in [parsed['exog'], parsed['endog'], parsed['instr']]:
                    for var in var_list:
                        # Check if this is an interaction term (contains *)
                        if '*' in var:
                            # Split by * and add individual variables
                            interaction_vars = [v.strip() for v in var.split('*')]
                            all_vars.update(interaction_vars)
                        else:
                            all_vars.add(var)
            
            missing_vars = [v for v in all_vars if v not in df.columns]
            if missing_vars:
                return {
                    'error': f'Variables not found in dataset: {", ".join(missing_vars)}',
                    'has_results': False
                }
            
            # Create interaction terms in the dataframe if needed
            # linearmodels can handle * in formulas, but we need to ensure the base variables exist
            # For SUR, we might need to create interaction terms explicitly
            df = df.copy()
            # Track interaction term replacements for formula updates
            interaction_replacements = {}
            for eq in formulas:
                parsed = parse_equation(eq)
                # Check for interaction terms in exog
                for term in parsed['exog']:
                    if '*' in term:
                        # This is an interaction term - create it in the dataframe
                        parts = [v.strip() for v in term.split('*')]
                        if all(part in df.columns for part in parts):
                            # All parts exist, create interaction
                            interaction_value = df[parts[0]].copy()
                            for part in parts[1:]:
                                interaction_value = interaction_value * df[part]
                            # Use a safe column name (replace * with _x_ to avoid parsing issues)
                            safe_name = term.replace(' * ', '_x_').replace('*', '_x_')
                            df[safe_name] = interaction_value
                            interaction_replacements[term] = safe_name
                            print(f"DEBUG: Created interaction term in dataframe: {safe_name} = {' * '.join(parts)}")
            
            # Update formulas to use safe interaction term names
            if interaction_replacements:
                updated_formulas = []
                for eq in formulas:
                    updated_eq = eq
                    for old, new in interaction_replacements.items():
                        updated_eq = updated_eq.replace(old, new)
                    updated_formulas.append(updated_eq)
                formulas = updated_formulas
            
            # Add constant term to dataframe if not present
            if 'const' not in df.columns:
                df['const'] = 1.0
            
            # Estimate the system
            res, params, diagnostics_df, instrument_diagnostics = estimate_system(formulas, df, method=method)
            
            # Format results for display
            # Ensure diagnostics is always a list, even if empty
            diagnostics_list = diagnostics_df.to_dict('records') if len(diagnostics_df) > 0 else []
            
            # Only include identification check for 2SLS and 3SLS, not SUR
            identification_results = None
            if method in ["2SLS", "3SLS"]:
                identification_results = check_identification(formulas)
            
            # Convert params DataFrame to dict, ensuring all values are Python native types
            params_dict = params.to_dict('records')
            # Convert any numpy types to Python native types
            for param in params_dict:
                for key, value in param.items():
                    if hasattr(value, 'item'):  # numpy scalar
                        param[key] = value.item()
                    elif hasattr(value, '__float__'):  # can be converted to float
                        try:
                            param[key] = float(value)
                        except (ValueError, TypeError):
                            param[key] = str(value)
            
            results = {
                'success': True,
                'has_results': True,
                'method': method,
                'formulas': formulas,
                'params': params_dict,
                'diagnostics': diagnostics_list,
                'identification': identification_results,
                'instrument_diagnostics': instrument_diagnostics,  # Add instrument diagnostics for 2SLS
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
            error_trace = traceback.format_exc()
            print(f"FULL TRACEBACK:\n{error_trace}")
            error_msg = str(e)
            # Provide more context about the error
            if "'NoneType' object is not callable" in error_msg:
                error_msg += "\n\nThis error typically occurs when trying to call a method on a None value. Check if model.fit() returned None or if result attributes are None."
            return {
                'error': f'Error estimating structural model: {error_msg}',
                'has_results': False,
                'traceback': error_trace
            }

