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
            res = model.fit(cov_type="robust")
            
            # Debug: Print first_stage info immediately after fitting
            if hasattr(res, 'first_stage'):
                print(f"DEBUG: res.first_stage exists, type: {type(res.first_stage)}")
                if res.first_stage is not None:
                    print(f"DEBUG: first_stage attributes: {[x for x in dir(res.first_stage) if not x.startswith('_')]}")
                    try:
                        # summary is a property, not a method
                        summary = res.first_stage.summary
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
                                diagnostics = res.first_stage.diagnostics
                                # diagnostics might be a dict or DataFrame
                                if isinstance(diagnostics, pd.DataFrame):
                                    if endog_name in diagnostics.index:
                                        row = diagnostics.loc[endog_name]
                                        # Look for F-statistic and partial R²
                                        for col in diagnostics.columns:
                                            col_lower = str(col).lower()
                                            if 'f' in col_lower and 'stat' in col_lower:
                                                fs_fstat = row[col]
                                            if 'partial' in col_lower and 'r' in col_lower:
                                                partial_r2 = row[col]
                                elif hasattr(diagnostics, '__getitem__'):
                                    try:
                                        diag_info = diagnostics[endog_name]
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
                                summary = res.first_stage.summary  # Property, not method
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
                                df = res.first_stage.to_frame()
                                if endog_name in df.index:
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
                    weak_instrument = res.weak_instrument_test
                
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
                overid_test = None
                # Try different attribute names
                for attr_name in ['overidentification_test', 'overid_test', 'j_stat', 'sargan_stat']:
                    if hasattr(res, attr_name):
                        overid_test = getattr(res, attr_name)
                        break
                
                if overid_test is not None:
                    if hasattr(overid_test, 'stat'):
                        test_name = 'Hansen J'
                        if hasattr(overid_test, 'test_name'):
                            test_name = str(overid_test.test_name)
                        elif hasattr(overid_test, 'name'):
                            test_name = str(overid_test.name)
                        
                        instrument_diagnostics['overidentification'] = {
                            'statistic': float(overid_test.stat) if overid_test.stat is not None else None,
                            'pvalue': float(overid_test.pval) if hasattr(overid_test, 'pval') and overid_test.pval is not None else None,
                            'test_name': test_name,
                        }
                    else:
                        instrument_diagnostics['overidentification'] = None
                else:
                    instrument_diagnostics['overidentification'] = None
            except Exception as e:
                instrument_diagnostics['overidentification'] = None
                print(f"Info: Overidentification test not available (model may be exactly identified): {e}")
            
            # 4. Endogeneity test (Durbin-Wu-Hausman)
            try:
                wu_hausman = res.wu_hausman
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
        params = pd.DataFrame({
            "variable": res.params.index,
            "param": np.asarray(res.params.values),
            "std_err": np.asarray(res.std_errors.values),
            "t": np.asarray(res.tstats.values),
            "p": np.asarray(res.pvalues.values)
        })
        
        # Add instrument diagnostics to params or return separately
        # We'll add it to the results dictionary later

        # Get dependent variable data - IVData object structure
        # The simplest approach: reconstruct y from fitted_values + residuals
        # This is always accurate: y = y_hat + residuals
        y_hat = np.asarray(res.fitted_values)
        residuals = np.asarray(res.resids)
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
            traceback.print_exc()
            return {
                'error': f'Error estimating structural model: {str(e)}',
                'has_results': False
            }

