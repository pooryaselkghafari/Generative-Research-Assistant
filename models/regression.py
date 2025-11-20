# regression/module.py
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor


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

def _calculate_ols_diagnostics(model):
    """
    Calculate diagnostic metrics for OLS regression models.
    
    Parameters:
    - model: Fitted statsmodels OLS model
    
    Returns:
    - DataFrame with diagnostic metrics
    """
    try:
        from statsmodels.stats.stattools import durbin_watson
        from statsmodels.stats.stattools import jarque_bera
        
        # Get residuals
        residuals = model.resid
        
        # Durbin-Watson test for autocorrelation
        dw = durbin_watson(residuals)
        
        # Jarque-Bera test for normality
        jb_stat, jb_p, skew, kurt = jarque_bera(residuals)
        
        # Condition number for multicollinearity
        condition_number = model.condition_number
        
        # Create diagnostic table
        diagnostics_data = {
            "Diagnostic": [
                "Durbin-Watson (Autocorrelation)",
                "Jarque-Bera (Normality Statistic)",
                "Jarque-Bera p-value",
                "Skewness",
                "Kurtosis",
                "Condition Number (Multicollinearity)"
            ],
            "Value": [
                float(dw) if not np.isnan(dw) else np.nan,
                float(jb_stat) if not np.isnan(jb_stat) else np.nan,
                float(jb_p) if not np.isnan(jb_p) else np.nan,
                float(skew) if not np.isnan(skew) else np.nan,
                float(kurt) if not np.isnan(kurt) else np.nan,
                float(condition_number) if not np.isnan(condition_number) else np.nan
            ],
            "Description": [
                "≈2 is ideal → near 0 or 4 indicates autocorrelation.",
                "High value → residuals deviate from normality.",
                "p < 0.05 → violation of normality assumption.",
                "Large magnitude (>1) → asymmetric residuals.",
                "Ideal ≈ 3 → higher = heavy tails.",
                ">30 → possible multicollinearity."
            ]
        }
        
        diagnostics_df = pd.DataFrame(diagnostics_data)
        return diagnostics_df
        
    except Exception as e:
        print(f"DEBUG: Error in _calculate_ols_diagnostics: {e}")
        import traceback
        traceback.print_exc()
        return None

def _calculate_binomial_diagnostics(model):
    """
    Calculate diagnostic metrics for binomial logistic regression models.
    
    Parameters:
    - model: Fitted statsmodels GLM model with Binomial family
    
    Returns:
    - DataFrame with diagnostic metrics
    """
    try:
        # Standardized Pearson residuals
        pearson_resid = model.resid_pearson
        dispersion = (pearson_resid ** 2).sum() / model.df_resid
        
        diagnostics_data = {
            "Diagnostic": [
                "Pearson Dispersion",
                "Max |Standardized Residual|",
                "DF Residuals"
            ],
            "Value": [
                float(dispersion) if not np.isnan(dispersion) else np.nan,
                float(abs(pearson_resid).max()) if len(pearson_resid) > 0 else np.nan,
                float(model.df_resid) if hasattr(model, 'df_resid') else np.nan
            ],
            "Description": [
                "≈1 → good; >>1 → overdispersion.",
                "Values >3 → outliers or poor fit.",
                "Low DF → too many predictors."
            ]
        }
        
        diagnostics_df = pd.DataFrame(diagnostics_data)
        return diagnostics_df
        
    except Exception as e:
        print(f"DEBUG: Error in _calculate_binomial_diagnostics: {e}")
        import traceback
        traceback.print_exc()
        return None

def _calculate_pearson_dispersion(model):
    """Calculate Pearson dispersion for multinomial model."""
    try:
        if hasattr(model, 'resid_pearson') and hasattr(model, 'df_resid') and model.df_resid > 0:
            return float((model.resid_pearson ** 2).sum() / model.df_resid)
    except Exception:
        pass
    return np.nan

def _calculate_max_residual(model):
    """Calculate max standardized residual for multinomial model."""
    try:
        if hasattr(model, 'resid_pearson') and len(model.resid_pearson) > 0:
            return float(abs(model.resid_pearson).max())
    except Exception:
        pass
    return np.nan

def _count_classes(y_data, model):
    """Count number of unique classes in y_data."""
    try:
        if hasattr(y_data, 'unique'):
            return len(y_data.unique())
        elif hasattr(y_data, 'nunique'):
            return y_data.nunique()
        elif isinstance(y_data, (list, pd.Series)):
            return len(set(y_data))
        elif isinstance(y_data, np.ndarray):
            return len(np.unique(y_data))
        elif hasattr(y_data, '__iter__'):
            return len(pd.Series(y_data).unique())
        elif hasattr(model, 'model') and hasattr(model.model, 'endog'):
            endog = model.model.endog
            return len(np.unique(endog)) if hasattr(endog, '__len__') else np.nan
    except Exception:
        pass
    return np.nan

def _get_df_residuals(model):
    """Get degrees of freedom for residuals."""
    try:
        if hasattr(model, 'df_resid'):
            return float(model.df_resid)
    except Exception:
        pass
    return np.nan

def _calculate_multinomial_diagnostics(model, y_data):
    """
    Calculate diagnostic metrics for multinomial logistic regression models.
    
    Parameters:
    - model: Fitted statsmodels MNLogit model
    - y_data: Original dependent variable data (to count classes)
    
    Returns:
    - DataFrame with diagnostic metrics (always returns a DataFrame, even if some values are NaN)
    """
    # Calculate each diagnostic metric using helper functions
    disp = _calculate_pearson_dispersion(model)
    max_resid = _calculate_max_residual(model)
    n_classes = _count_classes(y_data, model)
    df_resid = _get_df_residuals(model)
    
    # Always return a DataFrame, even if some values are NaN
    diagnostics_data = {
        "Diagnostic": [
            "Pearson Dispersion",
            "Max |Standardized Residual|",
            "Number of Classes",
            "DF Residuals"
        ],
        "Value": [
            float(disp) if not np.isnan(disp) else np.nan,
            float(max_resid) if not np.isnan(max_resid) else np.nan,
            int(n_classes) if not np.isnan(n_classes) else np.nan,
            float(df_resid) if not np.isnan(df_resid) else np.nan
        ],
        "Description": [
            "≈1 → good; >>1 → overdispersion or mis-specification.",
            "Residuals >3 → outliers/misfit.",
            "More classes → higher complexity.",
            "Low DF → possible overfitting."
        ]
    }
    
    diagnostics_df = pd.DataFrame(diagnostics_data)
    print(f"DEBUG: Multinomial diagnostics calculated - disp={disp}, max_resid={max_resid}, n_classes={n_classes}, df_resid={df_resid}")
    return diagnostics_df

def _calculate_ordinal_diagnostics(model):
    """
    Calculate diagnostic metrics for ordinal regression models.
    
    Parameters:
    - model: Fitted OrderedModel
    
    Returns:
    - DataFrame with diagnostic metrics (always returns a DataFrame, even if some values are NaN)
    """
    # Initialize all values as NaN - we'll try to calculate each one
    disp = np.nan
    max_resid = np.nan
    threshold_count = np.nan
    df_resid = np.nan
    
    # Try to calculate Pearson Dispersion
    try:
        if hasattr(model, 'resid_pearson'):
            pearson = model.resid_pearson
            if hasattr(model, 'df_resid') and model.df_resid > 0:
                disp = float((pearson ** 2).sum() / model.df_resid)
            else:
                print(f"DEBUG: Ordinal diagnostics - model.df_resid not available or <= 0")
        else:
            print(f"DEBUG: Ordinal diagnostics - model.resid_pearson not available")
    except Exception as e:
        print(f"DEBUG: Error calculating Pearson Dispersion for ordinal: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to calculate Max |Standardized Residual|
    try:
        if hasattr(model, 'resid_pearson'):
            pearson = model.resid_pearson
            if len(pearson) > 0:
                max_resid = float(abs(pearson).max())
            else:
                print(f"DEBUG: Ordinal diagnostics - resid_pearson is empty")
        else:
            print(f"DEBUG: Ordinal diagnostics - model.resid_pearson not available for max residual")
    except Exception as e:
        print(f"DEBUG: Error calculating Max |Standardized Residual| for ordinal: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to get Threshold Count
    try:
        if hasattr(model, 'model') and hasattr(model.model, '_thresholds'):
            threshold_count = len(model.model._thresholds)
        else:
            print(f"DEBUG: Ordinal diagnostics - model.model._thresholds not available")
    except Exception as e:
        print(f"DEBUG: Error calculating Threshold Count for ordinal: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to get DF Residuals
    try:
        if hasattr(model, 'df_resid'):
            df_resid = float(model.df_resid)
        else:
            print(f"DEBUG: Ordinal diagnostics - model.df_resid not available")
    except Exception as e:
        print(f"DEBUG: Error getting DF Residuals for ordinal: {e}")
        import traceback
        traceback.print_exc()
    
    # Always return a DataFrame, even if some values are NaN
    diagnostics_data = {
        "Diagnostic": [
            "Pearson Dispersion",
            "Max |Standardized Residual|",
            "Threshold Count",
            "DF Residuals"
        ],
        "Value": [
            float(disp) if not np.isnan(disp) else np.nan,
            float(max_resid) if not np.isnan(max_resid) else np.nan,
            int(threshold_count) if not np.isnan(threshold_count) else np.nan,
            float(df_resid) if not np.isnan(df_resid) else np.nan
        ],
        "Description": [
            "≈1 → good; >>1 → overdispersion.",
            "Residuals >3 → poor fit or influential points.",
            "More thresholds = more category boundaries.",
            "Low DF → possible overfitting."
        ]
    }
    
    diagnostics_df = pd.DataFrame(diagnostics_data)
    print(f"DEBUG: Ordinal diagnostics calculated - disp={disp}, max_resid={max_resid}, threshold_count={threshold_count}, df_resid={df_resid}")
    return diagnostics_df

def _calculate_pseudo_r2(model):
    """Calculate pseudo R² measures for models that don't provide direct R²."""
    try:
        llf = model.llf        # log-likelihood of fitted model
        llnull = model.llnull  # log-likelihood of null (intercept-only)
        n = model.nobs

        # McFadden's R²
        mcfadden = 1 - (llf / llnull)
        
        # Cox & Snell R²
        cox_snell = 1 - np.exp((llnull - llf) * 2 / n)
        
        # Nagelkerke R²
        nagelkerke = cox_snell / (1 - np.exp(llnull * 2 / n))
        
        return {
            "McFadden": mcfadden,
            "CoxSnell": cox_snell,
            "Nagelkerke": nagelkerke
        }
    except Exception as e:
        print(f"DEBUG: Error calculating pseudo R²: {e}")
        return {
            "McFadden": np.nan,
            "CoxSnell": np.nan,
            "Nagelkerke": np.nan
        }

def _quote_column_names_with_spaces(df, formula):
    """Handle column names with spaces for statsmodels processing"""
    import re
    
    # For statsmodels, we need to temporarily rename columns with spaces
    # and update the formula accordingly
    column_mapping = {}
    df_renamed = df.copy()
    
    # Replace longer names first to avoid partial replacements
    cols_with_spaces = [col for col in df.columns if ' ' in col]
    cols_with_spaces.sort(key=len, reverse=True)
    
    # Boundaries treat letters, digits, and underscores as part of identifiers
    def replace_occurrences(text, old, new):
        pattern = rf'(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])'
        return re.sub(pattern, new, text)
    
    for col in cols_with_spaces:
        safe_name = col.replace(' ', '_')
        column_mapping[safe_name] = col
        if col in df_renamed.columns:
            df_renamed = df_renamed.rename(columns={col: safe_name})
        # Update formula to use safe names everywhere (including inside C(), interactions, etc.)
        formula = replace_occurrences(formula, col, safe_name)
    
    return formula, df_renamed, column_mapping

def _parse_formula(formula: str):
    lhs, rhs = formula.split("~", 1)
    outcomes = [t.strip() for t in lhs.split("+") if t.strip()]
    # basic split: remove interaction shorthand x*m -> x, m, x:m (we keep both)
    raw_terms = [t.strip() for t in rhs.split("+") if t.strip()]
    predictors = []
    interactions = []
    
    for t in raw_terms:
        if ":" in t and "*" not in t:
            # already explicit interaction: keep as one name too
            predictors.extend([p.strip() for p in t.split(":") if p.strip()])
            predictors.append(t)
            interactions.append(t)
        elif "*" in t:
            parts = [p.strip() for p in t.split("*") if p.strip()]
            predictors.extend(parts)
            
            # Create ALL interaction terms (two-way, three-way, etc.)
            # For A*B*C, create: A:B, A:C, B:C, A:B:C
            from itertools import combinations
            for r in range(2, len(parts) + 1):  # r=2 for two-way, r=3 for three-way, etc.
                for combo in combinations(parts, r):
                    interaction_name = ":".join(combo)
                    predictors.append(interaction_name)
                    interactions.append(interaction_name)
                    print(f"DEBUG: Found interaction term: {interaction_name} (parts: {combo})")
        else:
            predictors.append(t)
    # de-dup, keep order
    seen = set(); ordered = []
    for p in predictors:
        if p not in seen:
            seen.add(p); ordered.append(p)
    return outcomes, ordered, interactions

def _corr_pvalue(x, y):
    x = pd.Series(x).astype(float)
    y = pd.Series(y).astype(float)
    ok = x.notna() & y.notna()
    if ok.sum() < 3: return np.nan, np.nan
    r = np.corrcoef(x[ok], y[ok])[0,1]
    # t-stat for Pearson r
    n = int(ok.sum())
    if np.isfinite(r):
        t = r * np.sqrt((n-2)/(1-r**2)) if abs(r) < 1 else np.inf
        from scipy.stats import t as tdist
        p = 2*(1-tdist.cdf(abs(t), df=n-2))
    else:
        p = np.nan
    return r, p

def _partial_corr(y, x, controls_df):
    # residualize y and x on controls, then correlate residuals
    if controls_df.shape[1] == 0:
        return _corr_pvalue(x, y)
    df = pd.DataFrame({"y": y, "x": x}).join(controls_df)
    df = df.dropna()
    if df.shape[0] < 3:
        return np.nan, np.nan
    # add const
    Xc = sm.add_constant(df[controls_df.columns], has_constant="add")
    ry = sm.OLS(df["y"], Xc).fit().resid
    rx = sm.OLS(df["x"], Xc).fit().resid
    return _corr_pvalue(ry, rx)

def _calculate_correlation_matrix(df, x_vars, y_vars):
    """Calculate correlation matrix between x and y variables."""
    all_vars = list(set(x_vars + y_vars))
    corr_data = df[all_vars].corr()
    
    corr_matrix = np.zeros((len(y_vars), len(x_vars)))
    for i, y_var in enumerate(y_vars):
        for j, x_var in enumerate(x_vars):
            if y_var == x_var:
                corr_matrix[i, j] = 1.0
            elif y_var in corr_data.index and x_var in corr_data.columns:
                corr_matrix[i, j] = corr_data.loc[y_var, x_var]
            else:
                corr_matrix[i, j] = np.nan
    return corr_matrix

def _calculate_p_values(df, x_vars, y_vars):
    """Calculate p-values for correlation significance."""
    from scipy.stats import pearsonr
    p_values = np.ones((len(y_vars), len(x_vars)))
    
    for i, y_var in enumerate(y_vars):
        for j, x_var in enumerate(x_vars):
            if y_var == x_var:
                p_values[i, j] = 0.0
            else:
                try:
                    data1 = df[y_var].dropna()
                    data2 = df[x_var].dropna()
                    common_idx = data1.index.intersection(data2.index)
                    if len(common_idx) >= 3:
                        _, p_val = pearsonr(data1[common_idx], data2[common_idx])
                        p_values[i, j] = p_val
                    else:
                        p_values[i, j] = np.nan
                except Exception:
                    p_values[i, j] = np.nan
    return p_values

def _format_correlation_text(corr_val, p_val, show_significance):
    """Format correlation value with significance asterisks."""
    corr_str = f"{corr_val:.3f}"
    if show_significance and not np.isnan(p_val):
        if p_val < 0.001:
            corr_str += "***"
        elif p_val < 0.01:
            corr_str += "**"
        elif p_val < 0.05:
            corr_str += "*"
        elif p_val < 0.10:
            corr_str += "."
    return corr_str

def _build_correlation_heatmap_json(df, x_vars, y_vars, options):
    """Build correlation heatmap JSON for Plotly."""
    import plotly.graph_objects as go
    import plotly.io as pio
    
    # Filter to only continuous variables that exist in the dataset
    x_vars = [var for var in x_vars if var in df.columns and pd.api.types.is_numeric_dtype(df[var])]
    y_vars = [var for var in y_vars if var in df.columns and pd.api.types.is_numeric_dtype(df[var])]
    
    if len(x_vars) < 1 or len(y_vars) < 1:
        return None
    
    # Calculate correlation matrix and p-values using helper functions
    corr_matrix = _calculate_correlation_matrix(df, x_vars, y_vars)
    p_values = _calculate_p_values(df, x_vars, y_vars)
    
    # Create text matrix with correlation coefficients and significance
    show_significance = options.get('show_significance', True)
    text_matrix = []
    for i in range(len(y_vars)):
        row = []
        for j in range(len(x_vars)):
            corr_str = _format_correlation_text(corr_matrix[i, j], p_values[i, j], show_significance)
            row.append(corr_str)
        text_matrix.append(row)
    
    # Color scheme options
    color_scheme = options.get('color_scheme', 'RdBu')
    color_schemes = {
        'RdBu': 'RdBu',
        'RdYlBu': 'RdYlBu', 
        'Viridis': 'Viridis',
        'Plasma': 'Plasma',
        'Inferno': 'Inferno',
        'Magma': 'Magma',
        'Blues': 'Blues',
        'Reds': 'Reds',
        'Greens': 'Greens',
        'Purples': 'Purples',
        'Oranges': 'Oranges',
        'Greys': 'Greys',
        'White': [[0, 'white'], [1, 'white']],  # Pure white
        'White-Blue': [[0, 'white'], [1, 'blue']],  # White to blue
        'White-Red': [[0, 'white'], [1, 'red']],  # White to red
        'White-Green': [[0, 'white'], [1, 'green']],  # White to green
        'White-Purple': [[0, 'white'], [1, 'purple']],  # White to purple
        'White-Orange': [[0, 'white'], [1, 'orange']],  # White to orange
    }
    
    colorscale = color_schemes.get(color_scheme, 'RdBu')
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=x_vars,
        y=y_vars,
        text=text_matrix,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorscale=colorscale,
        zmid=0,  # Center the colorscale at 0
        hoverongaps=False,
        hovertemplate="<b>%{y}</b> vs <b>%{x}</b><br>Correlation: %{z:.3f}<extra></extra>"
    ))
    
    # Update layout
    fig.update_layout(
        title="Correlation Heatmap",
        xaxis_title="X Variables",
        yaxis_title="Y Variables",
        height=max(400, len(y_vars) * 40 + 100),
        width=max(500, len(x_vars) * 40 + 100),
        margin=dict(l=60, r=20, t=60, b=60),
        template="plotly_white"
    )
    
    return pio.to_json(fig, pretty=False)

def _build_spotlight_json(model, df, x, moderator, opts):
    # opts: colors, styles, ci band toggle etc.
    if x not in df.columns or moderator not in df.columns:
        print(f"Variables not found: x='{x}' in columns: {x in df.columns}, moderator='{moderator}' in columns: {moderator in df.columns}")
        return None
    
    print(f"Building spotlight plot for x='{x}', moderator='{moderator}'")

    # get two moderator levels based on separation method
    mod_vals = np.sort(df[moderator].dropna().unique())
    if len(mod_vals) <= 2:  # binary-like
        mod_levels = list(mod_vals)
        labels = ["Low", "High"] if len(mod_vals) == 2 else [str(mod_vals[0]),]
    else:
        # Check if moderator is categorical (non-numeric)
        if not pd.api.types.is_numeric_dtype(df[moderator]):
            # For categorical variables, use first and last unique values
            print(f"DEBUG: Categorical moderator detected, using first and last values")
            mod_levels = [mod_vals[0], mod_vals[-1]]
            labels = ["Low", "High"]
            print(f"DEBUG: Categorical levels: {mod_levels}")
        else:
            # For numeric variables, use mean/median ± std_dev approach
            separation_method = opts.get('moderator_separation', 'mean')
            std_dev_multiplier = float(opts.get('moderator_std_dev_multiplier', 1.0))
            print(f"DEBUG: Numeric moderator - separation_method={separation_method}, std_dev_multiplier={std_dev_multiplier}")
            
            if separation_method == 'median':
                # Median-based split: median ± (std_dev_multiplier * std_dev)
                m = df[moderator].median()
                s = df[moderator].std(ddof=0) * std_dev_multiplier
                mod_levels = [m - s, m + s]
                labels = ["Low", "High"]
                print(f"DEBUG: Median-based split - center={m:.3f}, std_dev={df[moderator].std(ddof=0):.3f}, multiplier={std_dev_multiplier}, levels={[f'{x:.3f}' for x in mod_levels]}")
            else:  # mean (default)
                # Mean-based split: mean ± (std_dev_multiplier * std_dev)
                m = df[moderator].mean()
                s = df[moderator].std(ddof=0) * std_dev_multiplier
                mod_levels = [m - s, m + s]
                labels = ["Low", "High"]
                print(f"DEBUG: Mean-based split - center={m:.3f}, std_dev={df[moderator].std(ddof=0):.3f}, multiplier={std_dev_multiplier}, levels={[f'{x:.3f}' for x in mod_levels]}")
    
    # Override labels with custom values if provided
    if opts.get("legend_low"):
        labels[0] = opts.get("legend_low")
    if opts.get("legend_high") and len(labels) > 1:
        labels[1] = opts.get("legend_high")

    # X grid
    xx = df[x].dropna()
    if xx.nunique() <= 6:  # treat as discrete/binary
        x_grid = np.sort(xx.unique())
    else:
        x_grid = np.linspace(xx.min(), xx.max(), 100)

    print(f"DEBUG: ===== SPOTLIGHT PLOT GRID CREATION =====")
    print(f"DEBUG: X variable '{x}' - unique values: {xx.nunique()}")
    print(f"DEBUG: X grid length: {len(x_grid)}")
    print(f"DEBUG: X grid range: {x_grid.min()} to {x_grid.max()}")
    print(f"DEBUG: X grid sample (first 5): {x_grid[:5]}")

    # prepare pred dataframe
    traces = []
    bands = []

    # Line styles map
    dash_map = {
        "solid": None, "dashed": "dash", "dotted": "dot", "dashdot": "dashdot"
    }
    c_low = opts.get("color_low") or opts.get("plot_color_low", "#999999")
    c_high = opts.get("color_high") or opts.get("plot_color_high", "#111111")
    d_low = dash_map.get(opts.get("line_style_low", "solid"), None)
    d_high = dash_map.get(opts.get("line_style_high", "solid"), None)

    for idx, mval in enumerate(mod_levels):
        print(f"DEBUG: ===== PROCESSING MODERATOR LEVEL {idx + 1}/{len(mod_levels)} =====")
        print(f"DEBUG: Moderator value: {mval}")
        print(f"DEBUG: Moderator type: {type(mval)}")
        
        # Handle different separation methods
        separation_method = opts.get('moderator_separation', 'mean')
        
        # Use the calculated moderator level value directly
        grid = pd.DataFrame({x: x_grid, moderator: mval})
        print(f"DEBUG: Initial grid shape: {grid.shape}")
        print(f"DEBUG: Initial grid columns: {grid.columns.tolist()}")
        print(f"DEBUG: Initial grid dtypes: {grid.dtypes.to_dict()}")
        print(f"DEBUG: Initial grid sample (first 3 rows):")
        print(grid.head(3).to_string())
        
        # Check for NaN values in the original grid and fill them
        grid = grid.fillna(0.0)
        print(f"DEBUG: After fillna - any NaN values: {grid.isnull().any().any()}")
        
        # Parse the original formula to get all variables that should be in the grid
        # This is important because the model was fitted with a formula that includes C() wrappers
        if hasattr(model, 'model') and hasattr(model.model, 'formula'):
            formula = model.model.formula
            print(f"DEBUG: Parsing formula for grid construction: {formula}")
            
            # Extract variables from the formula (remove C() wrappers)
            lhs, rhs = formula.split("~", 1)
            # Split by + and clean up terms
            terms = [term.strip() for term in rhs.split("+")]
            formula_vars = []
            
            for term in terms:
                # Remove C() wrapper if present
                if term.startswith("C(") and term.endswith(")"):
                    var_name = term[2:-1]  # Remove C( and )
                    formula_vars.append(var_name)
                elif "*" in term or ":" in term:
                    # Handle interaction terms
                    if "*" in term:
                        parts = [part.strip() for part in term.split("*")]
                    else:  # ":"
                        parts = [part.strip() for part in term.split(":")]
                    
                    for part in parts:
                        if part.startswith("C(") and part.endswith(")"):
                            var_name = part[2:-1]
                        else:
                            var_name = part
                        if var_name not in formula_vars:
                            formula_vars.append(var_name)
                else:
                    # Regular variable
                    formula_vars.append(term)
            
            print(f"DEBUG: Variables from formula: {formula_vars}")
            
            # Add missing variables from the formula to the grid
            # Map safe names from the formula back to original df names (with spaces) when needed
            col_map = getattr(model, "_column_mapping", {})  # safe -> original
            for var_name in formula_vars:
                orig_name = col_map.get(var_name, var_name)
                target_name = orig_name  # add to grid using original names; will rename to safe before predict
                if target_name not in grid.columns and target_name in df.columns:
                    # Check if this variable was included in the model exog (using safe name)
                    if var_name in model.model.exog_names:
                        # Use the same data format as in the model
                        if pd.api.types.is_numeric_dtype(df[target_name]):
                            grid[target_name] = df[target_name].mean()
                        else:
                            # For categorical variables, use the mode (most frequent value)
                            mode_val = df[target_name].mode()
                            grid[target_name] = mode_val.iloc[0] if len(mode_val) > 0 else (df[target_name].dropna().iloc[0] if df[target_name].notna().any() else None)
                        print(f"DEBUG: Added missing variable '{target_name}' to grid (from formula var '{var_name}')")
                    else:
                        # Fallback: use original logic on original column
                        if pd.api.types.is_numeric_dtype(df[target_name]):
                            grid[target_name] = df[target_name].mean()
                        else:
                            mode_val = df[target_name].mode()
                            grid[target_name] = mode_val.iloc[0] if len(mode_val) > 0 else (df[target_name].dropna().iloc[0] if df[target_name].notna().any() else None)
                        print(f"DEBUG: Added missing variable '{target_name}' to grid (fallback)")
        
        # Also add missing regressors at default values if present in model (fallback)
        for nm in model.model.exog_names:
            if nm in ("Intercept", "const"): continue
            if nm not in grid.columns and nm in df.columns:
                # numeric -> mean; categorical -> most frequent
                if pd.api.types.is_numeric_dtype(df[nm]):
                    grid[nm] = df[nm].mean()
                else:
                    # For categorical variables, use mode (most frequent value)
                    grid[nm] = df[nm].mode().iloc[0]
        
        # Ensure categorical variables in grid match the data types from the original dataframe
        # This is important for models fitted with C() wrappers
        for col in grid.columns:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                # Ensure categorical variables maintain their original data type
                # Since we're using C() wrappers, we don't need to convert to numeric codes
                if not pd.api.types.is_numeric_dtype(df[col]):
                    # Keep categorical variables as their original values
                    grid[col] = grid[col].astype(df[col].dtype)
                    print(f"DEBUG: Kept '{col}' as categorical in grid: {grid[col].iloc[0]}")
        
        # Debug: Print grid info before prediction
        print(f"DEBUG: Grid before prediction:")
        print(f"  Columns: {grid.columns.tolist()}")
        print(f"  Shape: {grid.shape}")
        print(f"  Dtypes: {grid.dtypes.to_dict()}")
        print(f"  Sample values:")
        for col in grid.columns:
            print(f"    {col}: {grid[col].iloc[0] if len(grid) > 0 else 'empty'}")
        
        # For multinomial and ordinal models, ensure we have all variables in the correct order
        if 'MultinomialResults' in str(type(model)) or 'OrderedModel' in str(type(model.model)):
            print(f"DEBUG: Building complete grid for {type(model)}")
            print(f"DEBUG: Model exog_names: {model.model.exog_names}")
            print(f"DEBUG: Model params shape: {model.params.shape}")
            print(f"DEBUG: Model params index: {list(model.params.index)}")
            print(f"DEBUG: Original grid columns: {grid.columns.tolist()}")
            
            # Create a complete grid with all model variables
            complete_grid = pd.DataFrame()
            for var_name in model.model.exog_names:
                # Skip threshold parameters for ordinal models (e.g., '0/1', '1/2')
                if 'OrderedModel' in str(type(model.model)) and any(char.isdigit() for char in str(var_name)) and '/' in str(var_name):
                    continue
                elif var_name == 'const':
                    complete_grid[var_name] = 1.0  # Add constant term
                elif var_name in grid.columns:
                    # Use values from grid, but fill any NaNs
                    values = grid[var_name].fillna(0.0)
                    complete_grid[var_name] = values
                    print(f"DEBUG: Added '{var_name}' from grid to complete_grid: dtype={values.dtype}, sample={values.iloc[0] if len(values) > 0 else 'empty'}")
                elif var_name in df.columns:
                    if pd.api.types.is_numeric_dtype(df[var_name]):
                        mean_val = df[var_name].mean()
                        complete_grid[var_name] = mean_val if not pd.isna(mean_val) else 0.0
                    else:
                        # For categorical variables, use the mode (most frequent value) as-is
                        # Since we're using C() wrappers, we don't need to convert to numeric codes
                        mode_val = df[var_name].mode()
                        if len(mode_val) > 0:
                            complete_grid[var_name] = mode_val.iloc[0]
                            print(f"DEBUG: Used categorical value '{var_name}' in complete grid: {mode_val.iloc[0]}")
                        else:
                            # Use the first available value for categorical variables
                            first_val = df[var_name].dropna().iloc[0] if len(df[var_name].dropna()) > 0 else None
                            complete_grid[var_name] = first_val
                else:
                    complete_grid[var_name] = 0.0
            
            print(f"DEBUG: Complete grid columns: {complete_grid.columns.tolist()}")
            print(f"DEBUG: Complete grid shape: {complete_grid.shape}")
            print(f"DEBUG: Any NaN in complete grid: {complete_grid.isnull().any().any()}")
            print(f"DEBUG: Complete grid dtypes: {complete_grid.dtypes.to_dict()}")
            print(f"DEBUG: Complete grid sample values:")
            for col in complete_grid.columns:
                print(f"    {col}: {complete_grid[col].iloc[0] if len(complete_grid) > 0 else 'empty'}")
            
            # Fill any remaining NaN values
            complete_grid = complete_grid.fillna(0.0)
            
            # For ordinal models, we need to handle categorical variables properly
            # Since we're using C() wrappers, categorical variables should remain as-is
            if 'OrderedModel' in str(type(model.model)):
                for col in complete_grid.columns:
                    if not pd.api.types.is_numeric_dtype(complete_grid[col]):
                        # For categorical variables, keep them as-is since C() wrapper handles them
                        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                            # Keep categorical variables as their original values
                            print(f"DEBUG: Keeping '{col}' as categorical for ordinal model: {complete_grid[col].iloc[0]}")
                        else:
                            # Only convert to numeric if it's not a categorical variable
                            complete_grid[col] = pd.to_numeric(complete_grid[col], errors='coerce').fillna(0.0)
                            print(f"DEBUG: Converted '{col}' to numeric for ordinal model: dtype={complete_grid[col].dtype}")
            
            # Ensure categorical variables maintain their original data types
            for col in complete_grid.columns:
                if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                    # Ensure categorical variables maintain their original data type
                    complete_grid[col] = complete_grid[col].astype(df[col].dtype)
            
            # For ordinal models, we need to be more careful about which variables to include
            if 'OrderedModel' in str(type(model.model)):
                print(f"DEBUG: ===== ORDINAL REGRESSION GRID GENERATION =====")
                print(f"DEBUG: Processing ordinal regression grid generation")
                print(f"DEBUG: Original grid shape: {grid.shape}")
                print(f"DEBUG: Original grid columns: {grid.columns.tolist()}")
                print(f"DEBUG: Original grid dtypes: {grid.dtypes.to_dict()}")
                print(f"DEBUG: Original grid sample (first 3 rows):")
                print(grid.head(3).to_string())
                
                # Only include variables that are actually in the model parameters
                # The model parameters should tell us which variables were actually used
                param_vars = []
                for param_name in model.params.index:
                    # Skip threshold parameters (they don't correspond to variables)
                    if not any(char.isdigit() for char in str(param_name)):
                        param_vars.append(param_name)
                
                print(f"DEBUG: Variables from model params: {param_vars}")
                print(f"DEBUG: Model parameter names: {list(model.params.index)}")
                print(f"DEBUG: Threshold parameters (skipped): {[p for p in model.params.index if any(char.isdigit() for char in str(p))]}")
                
                # Filter the grid to only include variables that are in the model
                # But preserve the x-axis variation from the original grid
                filtered_grid = pd.DataFrame()
                for var_name in param_vars:
                    print(f"DEBUG: Processing variable '{var_name}' for ordinal grid")
                    if var_name in grid.columns:
                        # Use the original grid values to preserve x-axis variation
                        filtered_grid[var_name] = grid[var_name]
                        print(f"DEBUG: Preserved x-axis variation for '{var_name}' from original grid")
                        print(f"DEBUG:   - Values range: {grid[var_name].min()} to {grid[var_name].max()}")
                        print(f"DEBUG:   - Unique values: {grid[var_name].nunique()}")
                    elif var_name in complete_grid.columns:
                        filtered_grid[var_name] = complete_grid[var_name]
                        print(f"DEBUG: Used '{var_name}' from complete_grid")
                    elif var_name in df.columns:
                        if pd.api.types.is_numeric_dtype(df[var_name]):
                            mean_val = df[var_name].mean()
                            filtered_grid[var_name] = mean_val
                            print(f"DEBUG: Used mean value for numeric '{var_name}': {mean_val}")
                        else:
                            mode_val = df[var_name].mode().iloc[0]
                            filtered_grid[var_name] = mode_val
                            print(f"DEBUG: Used mode value for categorical '{var_name}': {mode_val}")
                    else:
                        # Check if this is actually a dummy variable by looking for patterns
                        # Dummy variables typically have patterns like "VariableName[T.Category]"
                        if '[' in var_name and ']' in var_name:
                            # This is likely a dummy variable from categorical encoding
                            filtered_grid[var_name] = 0.0
                            print(f"DEBUG: Set dummy variable '{var_name}' to 0.0 (categorical encoding)")
                        else:
                            # This might be a missing variable, try to find it in the dataframe
                            # Check if there's a similar variable name (case-insensitive)
                            similar_vars = [col for col in df.columns if col.lower() == var_name.lower()]
                            if similar_vars:
                                actual_var = similar_vars[0]
                                if pd.api.types.is_numeric_dtype(df[actual_var]):
                                    mean_val = df[actual_var].mean()
                                    filtered_grid[var_name] = mean_val
                                    print(f"DEBUG: Found similar variable '{actual_var}' for '{var_name}', used mean: {mean_val}")
                                else:
                                    mode_val = df[actual_var].mode().iloc[0]
                                    filtered_grid[var_name] = mode_val
                                    print(f"DEBUG: Found similar variable '{actual_var}' for '{var_name}', used mode: {mode_val}")
                            else:
                                # No similar variable found, set to 0
                                filtered_grid[var_name] = 0.0
                                print(f"DEBUG: Set missing variable '{var_name}' to 0.0 (no similar variable found)")
                
                print(f"DEBUG: Filtered grid columns: {filtered_grid.columns.tolist()}")
                print(f"DEBUG: Filtered grid shape: {filtered_grid.shape}")
                print(f"DEBUG: Filtered grid dtypes: {filtered_grid.dtypes.to_dict()}")
                print(f"DEBUG: Filtered grid sample (first 3 rows):")
                print(filtered_grid.head(3).to_string())
                
                # Ensure categorical variables maintain their original data types
                for col in filtered_grid.columns:
                    if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                        # Ensure categorical variables maintain their original data type
                        filtered_grid[col] = filtered_grid[col].astype(df[col].dtype)
                        print(f"DEBUG: Maintained categorical dtype for '{col}': {filtered_grid[col].dtype}")
                
                print(f"DEBUG: Final ordinal grid before prediction:")
                print(f"DEBUG:   - Shape: {filtered_grid.shape}")
                print(f"DEBUG:   - Columns: {filtered_grid.columns.tolist()}")
                print(f"DEBUG:   - Dtypes: {filtered_grid.dtypes.to_dict()}")
                print(f"DEBUG:   - Any NaN values: {filtered_grid.isnull().any().any()}")
                print(f"DEBUG:   - Sample values (first row):")
                for col in filtered_grid.columns:
                    print(f"DEBUG:     {col}: {filtered_grid[col].iloc[0] if len(filtered_grid) > 0 else 'empty'}")
                
                grid = filtered_grid
            else:
                grid = complete_grid
        # predict with se (linear only; glm gives .bse if using get_prediction)
        try:
            # Debug: Print model info before prediction
            print(f"DEBUG: Model type: {type(model)}")
            if hasattr(model, 'model') and hasattr(model.model, 'formula'):
                print(f"DEBUG: Model formula: {model.model.formula}")
            print(f"DEBUG: Model exog_names: {model.model.exog_names}")
            
            # Check if model has get_prediction method and call it correctly
            if hasattr(model, 'get_prediction'):
                # For multinomial models, get_prediction doesn't work the same way
                if 'MultinomialResults' in str(type(model)):
                    print(f"DEBUG: Multinomial model prediction")
                    print(f"DEBUG: Grid columns: {grid.columns.tolist()}")
                    print(f"DEBUG: Model exog_names: {model.model.exog_names}")
                    
                    # Check if this is a formula-based model or manually parsed model
                    if hasattr(model, 'model') and hasattr(model.model, 'formula'):
                        # Formula-based model: pass original variables and let patsy handle design matrix
                        print(f"DEBUG: Using formula-based prediction")
                        
                        # For formula-based models, we need to use the original grid with original column names
                        # The complete_grid has dummy-encoded names, but formula models expect original names
                        # So we need to reconstruct the original grid from the original df
                        original_grid = pd.DataFrame()
                        
                        # Start with the basic x and moderator variables
                        original_grid[x] = grid[x]
                        original_grid[moderator] = grid[moderator]
                        
                        # Add other variables from the original df with their original names
                        # Parse the formula to get the original variable names
                        formula = model.model.formula
                        _, rhs = formula.split("~", 1)
                        formula_vars = []
                        for term in rhs.split("+"):
                            term = term.strip()
                            if term:
                                # Handle interaction terms (e.g., "X1*X2" -> extract X1, X2)
                                if "*" in term:
                                    parts = [var.strip() for var in term.split("*") if var.strip()]
                                    formula_vars.extend(parts)
                                elif ":" in term:
                                    parts = [var.strip() for var in term.split(":") if var.strip()]
                                    formula_vars.extend(parts)
                                else:
                                    formula_vars.append(term)
                        
                        # Remove duplicates
                        formula_vars = list(dict.fromkeys(formula_vars))
                        
                        for col in df.columns:
                            if col not in [x, moderator] and col in formula_vars:
                                # This variable is used in the model, add it to the grid
                                if pd.api.types.is_numeric_dtype(df[col]):
                                    original_grid[col] = df[col].mean()
                                else:
                                    original_grid[col] = df[col].mode().iloc[0]
                        
                        print(f"DEBUG: Original grid columns: {original_grid.columns.tolist()}")
                        pred_probs = model.predict(original_grid)
                    else:
                        # Manually parsed model: need to build design matrix manually
                        print(f"DEBUG: Using manual design matrix construction")
                        
                        # Build the design matrix in the same format as the model
                        grid_for_pred = pd.DataFrame()
                        
                        # Add constant term if present
                        if 'const' in model.model.exog_names:
                            grid_for_pred['const'] = 1.0
                        
                        # Add variables in the same order as the model
                        for var_name in model.model.exog_names:
                            if var_name == 'const':
                                continue
                            
                            # Check if this is an interaction term
                            if ':' in var_name:
                                # This is an interaction term - create it by multiplying component variables
                                parts = var_name.split(':')
                                print(f"DEBUG: Creating interaction term {var_name} from parts: {parts}")
                                
                                # Check if all parts are available
                                if all(part in grid.columns for part in parts):
                                    # Create interaction by multiplying component variables
                                    interaction_value = grid[parts[0]]
                                    for part in parts[1:]:
                                        # Check if both variables are numeric
                                        if pd.api.types.is_numeric_dtype(grid[parts[0]]) and pd.api.types.is_numeric_dtype(grid[part]):
                                            # Both numeric - can multiply
                                            val1 = pd.to_numeric(interaction_value, errors='coerce').fillna(0.0)
                                            val2 = pd.to_numeric(grid[part], errors='coerce').fillna(0.0)
                                            interaction_value = val1 * val2
                                        else:
                                            # At least one is categorical - use string concatenation for interaction
                                            interaction_value = interaction_value.astype(str) + "_" + grid[part].astype(str)
                                    grid_for_pred[var_name] = interaction_value
                                    print(f"DEBUG: Created interaction {var_name} = {' * '.join(parts)}")
                                else:
                                    print(f"DEBUG: Warning - Cannot create interaction {var_name}, missing parts: {[p for p in parts if p not in grid.columns]}")
                                    grid_for_pred[var_name] = 0.0
                            elif var_name in grid.columns:
                                # Use values from grid, but fill any NaNs
                                values = grid[var_name].fillna(0.0)
                                
                                # For categorical variables, keep them as-is since C() wrapper handles them
                                if not pd.api.types.is_numeric_dtype(values):
                                    # Keep categorical variables as their original values
                                    # The C() wrapper in the formula will handle the encoding
                                    print(f"DEBUG: Keeping categorical variable '{var_name}' as-is: {values.iloc[0] if len(values) > 0 else 'empty'}")
                                
                                grid_for_pred[var_name] = values
                            elif var_name in df.columns:
                                # Use mean for missing variables, but handle NaNs
                                if pd.api.types.is_numeric_dtype(df[var_name]):
                                    mean_val = df[var_name].mean()
                                    grid_for_pred[var_name] = mean_val if not pd.isna(mean_val) else 0.0
                                else:
                                    mode_val = df[var_name].mode()
                                    if len(mode_val) > 0:
                                        grid_for_pred[var_name] = mode_val.iloc[0]
                                    else:
                                        grid_for_pred[var_name] = 0.0
                            else:
                                # Variable not found, use 0
                                grid_for_pred[var_name] = 0.0
                        
                        # Ensure the order matches the model
                        grid_for_pred = grid_for_pred[model.model.exog_names]
                        
                        # Final check for NaN values and fill them
                        grid_for_pred = grid_for_pred.fillna(0.0)
                        
                        print(f"DEBUG: Grid for prediction shape: {grid_for_pred.shape}")
                        print(f"DEBUG: Grid for prediction columns: {grid_for_pred.columns.tolist()}")
                        print(f"DEBUG: Any NaN in final grid: {grid_for_pred.isnull().any().any()}")
                        
                        pred_probs = model.predict(grid_for_pred)
                    
                    # Check for NaNs and raise error if found
                    if hasattr(pred_probs, 'isnull') and pred_probs.isnull().any().any():
                        raise ValueError(
                            "Multinomial predict produced NaNs. "
                            "This usually means the grid is missing required variables or has invalid values. "
                            f"Grid columns: {grid.columns.tolist()}, "
                            f"Grid shape: {grid.shape}, "
                            f"Any NaN in grid: {grid.isnull().any().any()}"
                        )
                    
                    print(f"DEBUG: Prediction shape: {pred_probs.shape}")
                    print(f"DEBUG: First prediction: {pred_probs.iloc[0].tolist() if hasattr(pred_probs, 'iloc') else pred_probs[0]}")
                    
                    # For multinomial, pred_probs is a DataFrame with probabilities for each class
                    # Get the selected category from options
                    selected_category = opts.get('multinomial_category')
                    print(f"DEBUG: Selected multinomial category: {selected_category}")
                    print(f"DEBUG: Available prediction columns: {pred_probs.columns.tolist() if hasattr(pred_probs, 'columns') else 'No columns'}")
                    print(f"DEBUG: All options passed to function: {opts}")
                    
                    # Check if columns are numeric (indicating we need to map to category names)
                    if hasattr(pred_probs, 'columns'):
                        print(f"DEBUG: Checking for category matches...")
                        print(f"DEBUG: Column types: {[type(col).__name__ for col in pred_probs.columns]}")
                        
                        # If columns are numeric, we need to map them to category names
                        if all(isinstance(col, (int, float)) for col in pred_probs.columns):
                            print(f"DEBUG: Numeric columns detected, need to map to category names")
                            # Get the model's category names
                            if hasattr(model, 'model') and hasattr(model.model, 'endog_names'):
                                # For multinomial, we need to get the actual category names
                                # This is a bit tricky - we need to get them from the original data
                                y_var = model.model.endog_names
                                if y_var in df.columns:
                                    categories = sorted(df[y_var].dropna().unique())
                                    print(f"DEBUG: Available categories from data: {categories}")
                                    
                                    # Map category to column index
                                    if selected_category in categories:
                                        category_index = categories.index(selected_category)
                                        if category_index < len(pred_probs.columns):
                                            print(f"DEBUG: Mapped '{selected_category}' to column index {category_index}")
                                            pred = pred_probs.iloc[:, category_index]
                                            print(f"DEBUG: Sample predictions for '{selected_category}': {pred.head().tolist()}")
                                        else:
                                            print(f"DEBUG: Category index {category_index} out of range, using first column")
                                            pred = pred_probs.iloc[:, 0]
                                    else:
                                        print(f"DEBUG: Category '{selected_category}' not found in data categories, using first column")
                                        pred = pred_probs.iloc[:, 0]
                                else:
                                    print(f"DEBUG: Could not find dependent variable '{y_var}' in data, using first column")
                                    pred = pred_probs.iloc[:, 0]
                            else:
                                print(f"DEBUG: Could not get category names from model, using first column")
                                pred = pred_probs.iloc[:, 0]
                        else:
                            # Columns are string names, use the original matching logic
                            exact_match = selected_category in pred_probs.columns
                            print(f"DEBUG: Exact match for '{selected_category}': {exact_match}")
                            
                            if exact_match:
                                pred = pred_probs[selected_category]
                                print(f"DEBUG: Using exact match category '{selected_category}' for predictions")
                            else:
                                # Try case-insensitive match
                                matched_column = None
                                for col in pred_probs.columns:
                                    if str(col).lower() == selected_category.lower():
                                        matched_column = col
                                        break
                                
                                if matched_column:
                                    pred = pred_probs[matched_column]
                                    print(f"DEBUG: Using case-insensitive match '{matched_column}' for '{selected_category}'")
                                else:
                                    print(f"DEBUG: No match found for '{selected_category}', using first column")
                                    pred = pred_probs.iloc[:, 0]
                    else:
                        # No category specified, use first column
                        print(f"DEBUG: No category specified, using first column")
                        if hasattr(pred_probs, 'iloc'):
                            pred = pred_probs.iloc[:, 0] if pred_probs.shape[1] > 0 else pd.Series([0] * len(grid), index=grid.index)
                        else:
                            pred = pred_probs[:, 0] if pred_probs.shape[1] > 0 else np.zeros(len(grid))
                    
                    # For multinomial, we don't have standard errors easily available
                    se = pd.Series(np.nan, index=grid.index)
                # For ordinal regression models
                elif 'OrderedModel' in str(type(model.model)):
                    print(f"DEBUG: ===== ORDINAL REGRESSION PREDICTION =====")
                    print(f"DEBUG: Using OrderedModel for prediction")
                    print(f"DEBUG: Grid before conversion to array:")
                    print(f"DEBUG:   - Shape: {grid.shape}")
                    print(f"DEBUG:   - Columns: {grid.columns.tolist()}")
                    print(f"DEBUG:   - Dtypes: {grid.dtypes.to_dict()}")
                    print(f"DEBUG:   - Sample values (first 3 rows):")
                    print(grid.head(3).to_string())
                    
                    # For ordinal regression, predict() returns probabilities for each category
                    # Use the properly constructed grid that varies with x-axis values
                    # Convert to numpy array to avoid data type issues
                    grid_array = grid.values.astype(float)
                    print(f"DEBUG: Grid array shape: {grid_array.shape}")
                    print(f"DEBUG: Grid array dtype: {grid_array.dtype}")
                    print(f"DEBUG: Grid array sample (first 3 rows):")
                    print(grid_array[:3])
                    
                    pred_probs = model.predict(grid_array)
                    print(f"DEBUG: Ordinal prediction shape: {pred_probs.shape}")
                    print(f"DEBUG: Ordinal prediction columns: {pred_probs.columns.tolist() if hasattr(pred_probs, 'columns') else 'No columns'}")
                    print(f"DEBUG: Ordinal prediction sample (first 3 rows):")
                    if hasattr(pred_probs, 'iloc'):
                        print(pred_probs.head(3).to_string())
                    else:
                        print(pred_probs[:3])
                    
                    # Get the selected category from options
                    selected_category = opts.get('ordinal_category')
                    print(f"DEBUG: Selected ordinal category: {selected_category}")
                    
                    if selected_category is not None:
                        # Check if columns are numeric (indicating we need to map to category names)
                        if hasattr(pred_probs, 'columns'):
                            print(f"DEBUG: Ordinal column types: {[type(col).__name__ for col in pred_probs.columns]}")
                            
                            # If columns are numeric, we need to map them to category names
                            if all(isinstance(col, (int, float)) for col in pred_probs.columns):
                                print(f"DEBUG: Numeric columns detected for ordinal, need to map to category names")
                                # Get the model's category names
                                if hasattr(model, 'model') and hasattr(model.model, 'endog_names'):
                                    y_var = model.model.endog_names
                                    if y_var in df.columns:
                                        categories = sorted(df[y_var].dropna().unique())
                                        print(f"DEBUG: Available ordinal categories from data: {categories}")
                                        
                                        # Map category to column index
                                        if selected_category in categories:
                                            category_index = categories.index(selected_category)
                                            if category_index < len(pred_probs.columns):
                                                print(f"DEBUG: Mapped ordinal '{selected_category}' to column index {category_index}")
                                                pred = pred_probs.iloc[:, category_index]
                                                print(f"DEBUG: Sample ordinal predictions for '{selected_category}': {pred.head().tolist()}")
                                            else:
                                                print(f"DEBUG: Ordinal category index {category_index} out of range, using first column")
                                                pred = pred_probs.iloc[:, 0]
                                        else:
                                            print(f"DEBUG: Ordinal category '{selected_category}' not found in data categories, using first column")
                                            pred = pred_probs.iloc[:, 0]
                                    else:
                                        print(f"DEBUG: Could not find ordinal dependent variable '{y_var}' in data, using first column")
                                        pred = pred_probs.iloc[:, 0]
                                else:
                                    print(f"DEBUG: Could not get ordinal category names from model, using first column")
                                    pred = pred_probs.iloc[:, 0]
                            else:
                                # Columns are string names, use the original matching logic
                                if selected_category in pred_probs.columns:
                                    pred = pred_probs[selected_category]
                                    print(f"DEBUG: Using exact match ordinal category '{selected_category}' for predictions")
                                else:
                                    # Try case-insensitive match
                                    matched_column = None
                                    for col in pred_probs.columns:
                                        if str(col).lower() == selected_category.lower():
                                            matched_column = col
                                            break
                                    
                                    if matched_column:
                                        pred = pred_probs[matched_column]
                                        print(f"DEBUG: Using case-insensitive match '{matched_column}' for ordinal '{selected_category}'")
                                    else:
                                        print(f"DEBUG: No match found for ordinal '{selected_category}', using first column")
                                        pred = pred_probs.iloc[:, 0]
                        else:
                            # If it's a numpy array, we need to map the category to the correct column
                            pred = pred_probs[:, 0] if pred_probs.shape[1] > 0 else np.zeros(len(grid))
                    else:
                        # Default to first category if no category specified
                        print(f"DEBUG: No ordinal category specified, using first column")
                        if hasattr(pred_probs, 'iloc'):
                            pred = pred_probs.iloc[:, 0] if pred_probs.shape[1] > 0 else pd.Series([0] * len(grid), index=grid.index)
                        else:
                            pred = pred_probs[:, 0] if pred_probs.shape[1] > 0 else np.zeros(len(grid))
                    # For ordinal regression, we don't have standard errors easily available
                    se = pd.Series(np.nan, index=grid.index)
                else:
                    # Ensure grid uses safe column names used during model fitting
                    if hasattr(model, "_column_mapping") and isinstance(grid, pd.DataFrame):
                        mapping = getattr(model, "_column_mapping", {})  # safe -> original
                        inv_mapping = {orig: safe for safe, orig in mapping.items()}
                        grid = grid.rename(columns=inv_mapping)
                        if 'complete_grid' in locals() and isinstance(complete_grid, pd.DataFrame):
                            complete_grid = complete_grid.rename(columns=inv_mapping)
                    pr = model.get_prediction(grid)
                    pred = pr.predicted_mean
                    se = pr.se_mean
            else:
                # Fallback to predict method
                # Ensure grid uses safe column names used during model fitting
                if hasattr(model, "_column_mapping") and isinstance(grid, pd.DataFrame):
                    mapping = getattr(model, "_column_mapping", {})  # safe -> original
                    inv_mapping = {orig: safe for safe, orig in mapping.items()}
                    grid = grid.rename(columns=inv_mapping)
                    if 'complete_grid' in locals() and isinstance(complete_grid, pd.DataFrame):
                        complete_grid = complete_grid.rename(columns=inv_mapping)
                pred = model.predict(grid)
                se = pd.Series(np.nan, index=grid.index)
        except Exception as e:
            print(f"Prediction failed: {e}")
            # Handle multinomial models in fallback
            if 'MultinomialResults' in str(type(model)):
                # Rebuild a grid using original formula variables (not dummy exog names)
                try:
                    formula = model.model.formula
                    _, rhs = formula.split("~", 1)
                    base_terms = []
                    for term in [t.strip() for t in rhs.split("+") if t.strip()]:
                        if "*" in term:
                            parts = [p.strip() for p in term.split("*") if p.strip()]
                            base_terms.extend(parts)
                        elif ":" in term:
                            parts = [p.strip() for p in term.split(":") if p.strip()]
                            base_terms.extend(parts)
                        else:
                            # Remove C() wrapper if present
                            if term.startswith("C(") and term.endswith(")"):
                                base_terms.append(term[2:-1])
                            else:
                                base_terms.append(term)
                    # De-duplicate preserving order
                    seen = set(); base_terms_dedup = []
                    for t in base_terms:
                        if t not in seen:
                            seen.add(t); base_terms_dedup.append(t)
                    
                    grid_orig = pd.DataFrame(index=grid.index if isinstance(grid, pd.DataFrame) else None)
                    for var in base_terms_dedup:
                        if isinstance(grid, pd.DataFrame) and var in grid.columns:
                            grid_orig[var] = grid[var]
                        elif var in df.columns:
                            if pd.api.types.is_numeric_dtype(df[var]):
                                grid_orig[var] = df[var].mean()
                            else:
                                mode_val = df[var].mode()
                                grid_orig[var] = mode_val.iloc[0] if len(mode_val) > 0 else (df[var].dropna().iloc[0] if df[var].notna().any() else None)
                        else:
                            grid_orig[var] = 0.0
                    
                    # Rename to safe names used during fitting
                    if hasattr(model, "_column_mapping"):
                        mapping = getattr(model, "_column_mapping", {})  # safe -> original
                        inv_mapping = {orig: safe for safe, orig in mapping.items()}
                        grid_for_pred = grid_orig.rename(columns=inv_mapping)
                    else:
                        grid_for_pred = grid_orig
                    
                    pred_probs = model.predict(grid_for_pred)
                except Exception as inner_e:
                    print(f"Multinomial fallback rebuild failed: {inner_e}")
                    # As a last resort, try original grid
                    pred_probs = model.predict(grid)
                if hasattr(pred_probs, 'iloc'):
                    pred = pred_probs.iloc[:, 0] if pred_probs.shape[1] > 0 else pd.Series([0] * len(grid), index=grid.index)
                else:
                    pred = pred_probs[:, 0] if pred_probs.shape[1] > 0 else np.zeros(len(grid))
            else:
                # For other model types, use the complete_grid if available, otherwise use grid
                if 'complete_grid' in locals():
                    pred = model.predict(complete_grid)
                else:
                    pred = model.predict(grid)
            se = pd.Series(np.nan, index=grid.index)

        color = c_low if idx == 0 else c_high
        dash = d_low if idx == 0 else d_high
        
        # Use custom display name if provided, otherwise use original moderator
        moderator_display_name = opts.get('moderator_display_name')
        if moderator_display_name and moderator_display_name.strip():
            display_moderator = moderator_display_name.strip()
        else:
            display_moderator = moderator
        name = f"{labels[idx]} {display_moderator}"

        traces.append(go.Scatter(
            x=x_grid, y=pred, mode="lines", name=name,
            line=dict(width=2.5, color=color, dash=dash)
        ))
        if opts.get("show_ci", opts.get("spotlight_ci", True)) and np.isfinite(se).any():
            lo = pred - 1.96*se
            hi = pred + 1.96*se
            bands.append(go.Scatter(
                x=np.concatenate([x_grid, x_grid[::-1]]),
                y=np.concatenate([hi, lo[::-1]]),
                fill="toself", fillcolor=color.replace("#", "#") if color else None,
                opacity=0.12, line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip", showlegend=False
            ))

    fig = go.Figure(data=bands + traces)
    
    # Set background color
    background_color = opts.get('background_color', 'white')
    
    # Set grid visibility
    show_grid = opts.get('show_grid', True)
    
    # Set default axis labels
    x_axis_title = opts.get("x_name") or x
    
    # For multinomial regression, show the selected category in the y-axis title
    if 'MultinomialResults' in str(type(model)):
        selected_category = opts.get('multinomial_category')
        if selected_category:
            y_axis_title = opts.get("y_name") or f"Probability of {selected_category}"
        else:
            y_axis_title = opts.get("y_name") or "Predicted Probability"
    # For ordinal regression, show the selected category in the y-axis title
    elif 'OrderedModel' in str(type(model.model)):
        selected_category = opts.get('ordinal_category')
        if selected_category:
            y_axis_title = opts.get("y_name") or f"Probability of {selected_category}"
        else:
            y_axis_title = opts.get("y_name") or "Predicted Probability"
    else:
        y_axis_title = opts.get("y_name") or "Predicted Probability"
    
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=60, r=10, t=20, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title=x_axis_title,
        yaxis_title=y_axis_title,
        height=420,
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        xaxis=dict(showgrid=show_grid),
        yaxis=dict(showgrid=show_grid)
    )
    return pio.to_json(fig, pretty=False)

def _parse_interaction_variables(interaction):
    """Parse interaction string to extract x and moderator variables."""
    if "*" in interaction:
        parts = [p.strip() for p in interaction.split("*")]
    else:
        parts = [p.strip() for p in interaction.split(":")]
    
    if len(parts) >= 2:
        x, m = parts[0], parts[1]
        if len(parts) > 2:
            print(f"DEBUG: Multi-way interaction detected: {interaction}, using {x} and {m} for spotlight plot")
        return x, m
    return None, None

def _get_category_selection_response(y_var, categories, interaction, x, m, response_type):
    """Create category selection response for ordinal/multinomial regression."""
    return {
        'type': response_type,
        'categories': categories,
        'dependent_variable': y_var,
        'interaction': interaction,
        'x_variable': x,
        'moderator_variable': m
    }

def _handle_regression_categories(fitted_model, df, options, is_ordinal, is_multinomial, interaction, x, m):
    """Handle category selection for ordinal/multinomial regression."""
    y_var = fitted_model.model.endog_names
    if hasattr(fitted_model, "_column_mapping"):
        y_var = getattr(fitted_model, "_column_mapping", {}).get(y_var, y_var)
    
    if y_var not in df.columns:
        print(f"Warning: Could not find dependent variable '{y_var}' in dataset")
        return None
    
    categories = sorted(df[y_var].dropna().unique())
    regression_type = "Ordinal" if is_ordinal else "Multinomial"
    print(f"{regression_type} regression detected. Available categories for {y_var}: {categories}")
    
    category_key = 'ordinal_category' if is_ordinal else 'multinomial_category'
    selected_category = options.get(category_key)
    
    if not selected_category:
        response_type = 'ordinal_category_selection' if is_ordinal else 'multinomial_category_selection'
        return _get_category_selection_response(y_var, categories, interaction, x, m, response_type)
    
    return None

def generate_spotlight_for_interaction(fitted_model, df, interaction, options, is_ordinal=False, is_multinomial=False):
    """Generate spotlight plot for a specific interaction."""
    x, m = _parse_interaction_variables(interaction)
    if not x or not m:
        print(f"DEBUG: Unsupported interaction format: {interaction}")
        return None
    
    original_moderator = m
    custom_moderator_display = options.get('moderator_var')
    if custom_moderator_display:
        print(f"Using custom moderator display name: '{custom_moderator_display}' (original was: '{original_moderator}')")
    
    if x not in df.columns or original_moderator not in df.columns:
        print(f"Warning: Variables not found in dataset columns: {list(df.columns)}")
        return None
    
    print(f"Generating spotlight plot with X='{x}' and moderator='{original_moderator}' (display: '{custom_moderator_display or original_moderator}')")
    
    if is_ordinal or is_multinomial:
        category_response = _handle_regression_categories(fitted_model, df, options, is_ordinal, is_multinomial, interaction, x, original_moderator)
        if category_response:
            return category_response
    
    # Use the original moderator for analysis, but pass custom display name to the plot
    plot_options = options.copy()
    if custom_moderator_display:
        plot_options['moderator_display_name'] = custom_moderator_display
    
    return _build_spotlight_json(fitted_model, df, x, original_moderator, plot_options)

def _get_continuous_variables(df):
    """Get all continuous (numeric) variables from the dataset."""
    continuous_vars = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            # Check if it has more than 2 unique values (not binary)
            unique_vals = df[col].dropna().nunique()
            if unique_vals > 2:
                continuous_vars.append(col)
    return continuous_vars

def _get_continuous_variables_from_formula(df, formula):
    """Get continuous variables that appear in the formula."""
    # Parse the formula to extract variables
    outcomes, predictors, _ = _parse_formula(formula)
    all_vars = outcomes + predictors
    
    continuous_vars = []
    for var in all_vars:
        if var in df.columns and pd.api.types.is_numeric_dtype(df[var]):
            # Check if it has more than 2 unique values (not binary)
            unique_vals = df[var].dropna().nunique()
            if unique_vals > 2:
                continuous_vars.append(var)
    return continuous_vars

def _get_all_numeric_variables(df):
    """Get all numeric variables from the dataset."""
    numeric_vars = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_vars.append(col)
    return numeric_vars

def _wrap_part_with_c(part, df, categorical_vars):
    """Wrap a single part with C() if it's categorical."""
    if part in df.columns and part in categorical_vars:
        return f"C({part})"
    return part

def _handle_interaction_term(term, df, categorical_vars, separator):
    """Handle interaction term by wrapping categorical parts."""
    parts = [part.strip() for part in term.split(separator)]
    modified_parts = [_wrap_part_with_c(part, df, categorical_vars) for part in parts]
    return separator.join(modified_parts)

def _wrap_categorical_vars_in_formula(formula, df):
    """
    Wrap non-numeric variables in formula with C() to handle them as categorical.
    
    Note: C() wrapping is only needed for OLS and logistic regression models.
    Multinomial and ordinal regression models automatically handle non-numeric variables.
    
    Args:
        formula: The regression formula string
        df: DataFrame containing the variables
        
    Returns:
        Modified formula with C() wrapper for categorical variables
    """
    # Parse the formula to get LHS and RHS
    lhs, rhs = formula.split("~", 1)
    
    # Get numeric variables
    numeric_vars = _get_all_numeric_variables(df)
    
    # Identify categorical variables (non-numeric variables)
    categorical_vars = [col for col in df.columns if col not in numeric_vars]
    print(f"DEBUG: Detected categorical variables: {categorical_vars}")
    
    # Split RHS into terms
    terms = [term.strip() for term in rhs.split("+")]
    modified_terms = []
    
    for term in terms:
        if not term:
            continue
        
        if "*" in term:
            modified_term = _handle_interaction_term(term, df, categorical_vars, "*")
            modified_terms.append(modified_term)
        elif ":" in term:
            modified_term = _handle_interaction_term(term, df, categorical_vars, ":")
            modified_terms.append(modified_term)
        else:
            # Single variable term
            modified_terms.append(_wrap_part_with_c(term, df, categorical_vars))
    
    # Reconstruct the formula
    modified_rhs = " + ".join(modified_terms)
    modified_formula = f"{lhs} ~ {modified_rhs}"
    
    print(f"DEBUG: Original formula: {formula}")
    print(f"DEBUG: Modified formula: {modified_formula}")
    
    return modified_formula

def _generate_summary_stats(df, formula, fitted_model=None):
    """Generate summary statistics for variables in the formula."""
    outcomes, predictors, _ = _parse_formula(formula)
    summary_stats = {}
    
    # Include both outcomes and predictors from the formula (default behavior)
    all_vars = outcomes + predictors
    
    # Calculate VIF if model is available
    vif_map = {}
    if fitted_model is not None:
        try:
            exog = fitted_model.model.exog
            names = list(fitted_model.model.exog_names)
            for i, nm in enumerate(names):
                if nm.lower() in ("const", "intercept"): continue
                try:
                    vif_map[nm] = float(variance_inflation_factor(exog, i))
                except Exception:
                    vif_map[nm] = np.nan
        except Exception:
            pass
    
    for var in all_vars:
        if var in df.columns and pd.api.types.is_numeric_dtype(df[var]):
            series = df[var].dropna()
            if len(series) > 0:
                summary_stats[var] = {
                    'min': float(series.min()),
                    'max': float(series.max()),
                    'range': float(series.max() - series.min()),
                    'variance': float(series.var(ddof=1)),  # Sample variance
                    'vif': vif_map.get(var, np.nan)  # Add VIF
                }
    
    return summary_stats

class RegressionModule:
    @staticmethod
    def _validate_dependent_variable(y, df_renamed, df, column_mapping):
        """Validate that dependent variable exists in dataset."""
        if y not in df_renamed.columns:
            available_cols = list(df.columns)
            suggestions = [col for col in available_cols if col.lower() == y.lower() or y.lower() in col.lower()]
            original_y = column_mapping.get(y, y)
            error_msg = f"Variable '{original_y}' not found in dataset. Available columns: {available_cols}"
            if suggestions:
                error_msg += f". Did you mean: {suggestions}?"
            return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": error_msg}], {"N": int(df.shape[0])}, None, "Error"
        return None
    
    @staticmethod
    def _convert_dependent_variable(dependent_var, df_renamed, original_categories):
        """Convert dependent variable to numeric codes if needed."""
        if dependent_var not in df_renamed.columns:
            return None, original_categories
        
        col = dependent_var
        original_dtype = df_renamed[col].dtype
        original_non_null_count = df_renamed[col].notna().sum()
        
        if not pd.api.types.is_numeric_dtype(df_renamed[col]):
            if hasattr(df_renamed[col].dtype, 'categories'):
                original_categories[col] = list(df_renamed[col].cat.categories)
                df_renamed[col] = df_renamed[col].cat.codes
                df_renamed[col] = df_renamed[col].replace(-1, np.nan)
            else:
                codes, categories = pd.factorize(df_renamed[col])
                original_categories[col] = list(categories)
                df_renamed[col] = codes
                df_renamed[col] = df_renamed[col].replace(-1, np.nan)
            
            final_non_null_count = df_renamed[col].notna().sum()
            if final_non_null_count == 0 and original_non_null_count > 0:
                return f"Dependent variable '{col}' could not be converted to numeric values. Original type: {original_dtype}, Non-null values: {original_non_null_count}. Please check the data type and values.", original_categories
            
            print(f"DEBUG: Converted dependent variable '{col}' to numeric codes")
        
        return None, original_categories
    
    @staticmethod
    def _clean_dataframe(df_renamed, df, equation_vars=None):
        """
        Clean dataframe: remove infinite values and check for all-NaN columns.
        
        Args:
            df_renamed: DataFrame to clean
            df: Original DataFrame (for error messages)
            equation_vars: Optional list of column names to check. If None, checks all columns.
                          Should be set to only columns used in the equation.
        """
        df_renamed = df_renamed.replace([np.inf, -np.inf], np.nan)
        
        # Only check columns that are in the equation (if provided), otherwise check all
        columns_to_check = equation_vars if equation_vars is not None else df_renamed.columns
        
        for col in columns_to_check:
            if col in df_renamed.columns and df_renamed[col].isna().all():
                return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": f"Column '{col}' contains only missing values after data cleaning. Please check your data."}], {"N": int(df.shape[0])}, None, "Error", None
        
        return None, None, None, None, None, df_renamed
    
    @staticmethod
    def _validate_y_series(y, df_renamed, df, original_categories):
        """Validate dependent variable series after conversion."""
        y_series = df_renamed[y].dropna()
        if len(y_series) == 0:
            original_y = df[y].dropna() if y in df.columns else pd.Series()
            original_count = len(original_y)
            original_dtype = df[y].dtype if y in df.columns else "unknown"
            
            if original_count > 0:
                try:
                    df_renamed[y] = pd.factorize(df[y])[0]
                    df_renamed[y] = df_renamed[y].replace(-1, np.nan)
                    y_series = df_renamed[y].dropna()
                    if len(y_series) == 0:
                        return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": f"Dependent variable '{y}' could not be converted to numeric values. Original: {original_count} values, type: {original_dtype}."}], {"N": int(df.shape[0])}, None, "Error", None
                except Exception as e:
                    return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": f"Dependent variable '{y}' conversion failed: {str(e)}. Original: {original_count} values, type: {original_dtype}"}], {"N": int(df.shape[0])}, None, "Error", None
            else:
                return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": f"Dependent variable '{y}' has no valid values in the original dataset"}], {"N": int(df.shape[0])}, None, "Error", None
        
        y_vals = y_series.unique()
        if len(y_vals) < 2:
            return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": f"Dependent variable '{y}' has only one unique value after conversion"}], {"N": int(df.shape[0])}, None, "Error", None
        
        return None, None, None, None, None, y_vals
    
    @staticmethod
    def _determine_regression_type(y, y_vals, df_renamed, schema_types):
        """Determine regression type based on schema and data characteristics."""
        is_ordinal = False
        is_multinomial = False
        is_binary = False
        
        if schema_types is None:
            schema_types = {}
        
        if y in schema_types:
            var_type = schema_types[y]
            if var_type == "ordinal":
                is_ordinal = True
            elif var_type == "categorical":
                is_multinomial = True
            elif var_type == "binary":
                is_binary = True
        else:
            num_unique = len(y_vals)
            if pd.api.types.is_numeric_dtype(df_renamed[y]):
                if num_unique == 2:
                    is_binary = True
                elif num_unique <= 10 and df_renamed[y].dtype in ['int64', 'int32', 'int16', 'int8']:
                    is_multinomial = True
            else:
                if num_unique == 2:
                    is_binary = True
                elif num_unique > 2:
                    is_multinomial = True
        
        y_bin = len(y_vals) <= 2
        return is_ordinal, is_multinomial, is_binary, y_bin
    
    @staticmethod
    def _prepare_clean_data(df_renamed, formula, df):
        """Prepare clean data by dropping rows with missing values in equation variables."""
        outcomes, predictors, _ = _parse_formula(formula)
        equation_vars = [var for var in (outcomes + predictors) if var in df_renamed.columns]
        
        df_clean = df_renamed[equation_vars].dropna()
        df_clean = df_renamed.loc[df_clean.index]
        
        if len(df_clean) == 0:
            return ["Term", "Estimate"], [{"Term": "Model Error", "Estimate": "No valid data remaining after removing missing values. Please check your data for missing values."}], {"N": int(df.shape[0])}, None, "Error", None
        
        return None, None, None, None, None, df_clean
    
    @staticmethod
    def _parse_formula_terms(formula, df_clean):
        """Parse formula and extract predictor variables and interaction terms."""
        _, rhs = formula.split("~", 1)
        predictor_vars = []
        interaction_terms = []
        
        for term in rhs.split("+"):
            term = term.strip()
            if not term:
                continue
            
            if "*" in term:
                parts = [var.strip() for var in term.split("*") if var.strip()]
                if len(parts) >= 2 and all(part in df_clean.columns for part in parts):
                    predictor_vars.extend(parts)
                    from itertools import combinations
                    for r in range(2, len(parts) + 1):
                        for combo in combinations(parts, r):
                            interaction_name = ":".join(combo)
                            interaction_terms.append(interaction_name)
                            predictor_vars.append(interaction_name)
            elif ":" in term:
                parts = [var.strip() for var in term.split(":") if var.strip()]
                if len(parts) == 2 and all(part in df_clean.columns for part in parts):
                    predictor_vars.extend(parts)
                    interaction_terms.append(term)
                    predictor_vars.append(term)
            else:
                if term in df_clean.columns:
                    predictor_vars.append(term)
        
        predictor_vars = list(dict.fromkeys(predictor_vars))
        return predictor_vars, interaction_terms
    
    @staticmethod
    def _create_interaction_terms(df_clean, interaction_terms):
        """Create interaction terms in the dataframe."""
        for interaction in interaction_terms:
            if ":" in interaction:
                parts = interaction.split(":")
                if len(parts) >= 2 and all(part in df_clean.columns for part in parts):
                    interaction_value = df_clean[parts[0]]
                    for part in parts[1:]:
                        interaction_value = interaction_value * df_clean[part]
                    df_clean[interaction] = interaction_value
    
    @staticmethod
    def _fit_models(df, formula, options, schema_types=None, schema_orders=None):
        # Handle column names with spaces for proper processing
        formula, df_renamed, column_mapping = _quote_column_names_with_spaces(df, formula)
        print(f"DEBUG: Formula after safe-name replacement: {formula}")
        print(f"DEBUG: Columns after renaming: {list(df_renamed.columns)}")
        
        lhs, _ = formula.split("~", 1)
        y = [s.strip() for s in lhs.split("+") if s.strip()][0]
        
        # Validate dependent variable
        error_result = RegressionModule._validate_dependent_variable(y, df_renamed, df, column_mapping)
        if error_result:
            return error_result
        
        # Store original categories for ordinal variables before conversion
        original_categories = {}
        
        # Parse formula to identify dependent variable (y) and independent variables
        outcomes, predictors, _ = _parse_formula(formula)
        dependent_var = outcomes[0] if outcomes else y
        independent_vars = predictors
        
        print(f"DEBUG: Dependent variable: {dependent_var}")
        print(f"DEBUG: Independent variables: {independent_vars}")
        
        # Convert dependent variable to numeric codes if needed
        error_msg, original_categories = RegressionModule._convert_dependent_variable(dependent_var, df_renamed, original_categories)
        if error_msg:
            return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": error_msg}], {"N": int(df.shape[0])}, None, "Error"
        
        # Get equation variables (only columns used in the formula)
        equation_vars = [var for var in (outcomes + predictors) if var in df_renamed.columns]
        
        # Clean dataframe, but only check columns used in the equation
        error_result = RegressionModule._clean_dataframe(df_renamed, df, equation_vars=equation_vars)
        if error_result[0]:  # Check if error tuple returned
            return error_result[:5]  # Return first 5 elements (error result)
        df_renamed = error_result[5]  # Get cleaned dataframe
        
        # Validate y series
        error_result = RegressionModule._validate_y_series(y, df_renamed, df, original_categories)
        if error_result[0]:  # Check if error tuple returned
            return error_result[:5]  # Return first 5 elements (error result)
        y_vals = error_result[5]  # Get y_vals
        
        # Determine regression type
        is_ordinal, is_multinomial, is_binary, y_bin = RegressionModule._determine_regression_type(y, y_vals, df_renamed, schema_types)
        
        print(f"DEBUG: is_ordinal = {is_ordinal}")
        print(f"DEBUG: is_multinomial = {is_multinomial}")
        print(f"DEBUG: is_binary = {is_binary}")
        print(f"DEBUG: y_bin = {y_bin}")
        print(f"DEBUG: schema_types for y='{y}': {schema_types.get(y, 'Not found') if schema_types else 'Not found'}")
        print(f"DEBUG: regression_type will be determined based on these flags")

        try:
            # Debug: Check data before cleaning
            print(f"DEBUG: Original dataset shape: {df.shape}")
            print(f"DEBUG: Renamed dataset shape: {df_renamed.shape}")
            print(f"DEBUG: Missing values per column:")
            for col in df_renamed.columns:
                missing_count = df_renamed[col].isna().sum()
                if missing_count > 0:
                    print(f"  {col}: {missing_count} missing values")
            
            # Prepare clean data
            error_result = RegressionModule._prepare_clean_data(df_renamed, formula, df)
            if error_result[0]:  # Check if error tuple returned
                return error_result[:5]  # Return first 5 elements (error result)
            df_clean = error_result[5]  # Get cleaned dataframe
            
            print(f"DEBUG: Clean dataset shape: {df_clean.shape}")
            print(f"DEBUG: Rows dropped: {df_renamed.shape[0] - df_clean.shape[0]}")
            
            if is_ordinal:
                print(f"DEBUG: Taking ordinal regression branch")
                print(f"DEBUG: is_ordinal = {is_ordinal}, is_multinomial = {is_multinomial}")
                # Use proper ordinal regression with OrderedModel
                from statsmodels.miscmodels.ordinal_model import OrderedModel
                
                # Parse formula to extract predictor variables and create interaction terms
                _, rhs = formula.split("~", 1)
                # Extract all predictor variables from the RHS
                predictor_vars = []
                interaction_terms = []
                
                for term in rhs.split("+"):
                    term = term.strip()
                    if term:
                        # Handle interaction terms (e.g., "X1*X2" or "X1*X2*X3" -> create interactions)
                        if "*" in term:
                            parts = [var.strip() for var in term.split("*") if var.strip()]
                            if len(parts) >= 2 and all(part in df_clean.columns for part in parts):
                                # Add individual variables
                                predictor_vars.extend(parts)
                                
                                # Create ALL interaction terms (two-way, three-way, etc.)
                                # For A*B*C, create: A:B, A:C, B:C, A:B:C
                                from itertools import combinations
                                for r in range(2, len(parts) + 1):  # r=2 for two-way, r=3 for three-way, etc.
                                    for combo in combinations(parts, r):
                                        interaction_name = ":".join(combo)
                                        interaction_terms.append(interaction_name)
                                        predictor_vars.append(interaction_name)
                                        print(f"DEBUG: Created interaction term {interaction_name} = {' * '.join(combo)}")
                        elif ":" in term:
                            # Handle explicit interactions (e.g., "X1:X2" -> keep as is)
                            parts = [var.strip() for var in term.split(":") if var.strip()]
                            if len(parts) == 2 and all(part in df_clean.columns for part in parts):
                                # Add individual variables
                                predictor_vars.extend(parts)
                                # Keep the interaction term as is
                                interaction_terms.append(term)
                                predictor_vars.append(term)
                        else:
                            # Simple variable
                            if term in df_clean.columns:
                                predictor_vars.append(term)
                
                # Remove duplicates while preserving order
                predictor_vars = list(dict.fromkeys(predictor_vars))
                
                # Create interaction terms in the data
                for interaction in interaction_terms:
                    if ":" in interaction:
                        parts = interaction.split(":")
                        if len(parts) >= 2 and all(part in df_clean.columns for part in parts):
                            # Create interaction by multiplying all parts
                            interaction_value = df_clean[parts[0]]
                            for part in parts[1:]:
                                interaction_value = interaction_value * df_clean[part]
                            df_clean[interaction] = interaction_value
                            print(f"DEBUG: Created interaction term {interaction} = {' * '.join(parts)}")
                
                # Ensure proper data types: numerics as numeric, non-numerics as Categorical
                df_clean_typed = df_clean.copy()
                for col in df_clean_typed.columns:
                    if col == y:
                        # Keep dependent variable as-is for now - don't convert to categorical yet
                        # It will be handled specifically in ordinal vs multinomial sections
                        print(f"DEBUG: Keeping dependent variable '{y}' as-is in initial processing")
                        continue
                    elif pd.api.types.is_numeric_dtype(df_clean_typed[col]):
                        # Ensure numeric columns are properly typed as numeric
                        df_clean_typed[col] = pd.to_numeric(df_clean_typed[col], errors='coerce')
                    else:
                        # Convert non-numeric columns to Categorical
                        df_clean_typed[col] = pd.Categorical(df_clean_typed[col])
                
                # Parse formula to extract only the variables we need
                _, rhs = formula.split("~", 1)
                # Extract all predictor variables from the RHS
                predictor_vars = []
                interaction_terms = []
                
                for term in rhs.split("+"):
                    term = term.strip()
                    if term:
                        # Handle interaction terms (e.g., "X1*X2" or "X1*X2*X3" -> create interactions)
                        if "*" in term:
                            parts = [var.strip() for var in term.split("*") if var.strip()]
                            if len(parts) >= 2 and all(part in df_clean_typed.columns for part in parts):
                                # Add individual variables
                                predictor_vars.extend(parts)
                                
                                # Create ALL interaction terms (two-way, three-way, etc.)
                                # For A*B*C, create: A:B, A:C, B:C, A:B:C
                                from itertools import combinations
                                for r in range(2, len(parts) + 1):  # r=2 for two-way, r=3 for three-way, etc.
                                    for combo in combinations(parts, r):
                                        interaction_name = ":".join(combo)
                                        interaction_terms.append(interaction_name)
                                        predictor_vars.append(interaction_name)
                                        print(f"DEBUG: Created interaction term {interaction_name} = {' * '.join(combo)}")
                        elif ":" in term:
                            # Handle explicit interactions (e.g., "X1:X2" -> keep as is)
                            parts = [var.strip() for var in term.split(":") if var.strip()]
                            if len(parts) == 2 and all(part in df_clean_typed.columns for part in parts):
                                # Add individual variables
                                predictor_vars.extend(parts)
                                # Keep the interaction term as is
                                interaction_terms.append(term)
                                predictor_vars.append(term)
                        else:
                            # Simple variable - check if it exists in the original dataframe
                            if term in df_clean_typed.columns:
                                predictor_vars.append(term)
                            else:
                                print(f"DEBUG: Variable '{term}' not found in dataframe columns: {list(df_clean_typed.columns)}")
                
                # Remove duplicates while preserving order
                predictor_vars = list(dict.fromkeys(predictor_vars))
                
                print(f"DEBUG: Formula parsing results:")
                print(f"DEBUG: Original formula: {formula}")
                print(f"DEBUG: RHS: {rhs}")
                print(f"DEBUG: Extracted predictor_vars: {predictor_vars}")
                print(f"DEBUG: Interaction terms: {interaction_terms}")
                
                # Create interaction terms in the data
                for interaction in interaction_terms:
                    if ":" in interaction:
                        parts = interaction.split(":")
                        if len(parts) >= 2 and all(part in df_clean_typed.columns for part in parts):
                            # Create interaction by multiplying all parts
                            interaction_value = df_clean_typed[parts[0]]
                            for part in parts[1:]:
                                interaction_value = interaction_value * df_clean_typed[part]
                            df_clean_typed[interaction] = interaction_value
                            print(f"DEBUG: Created interaction term {interaction} = {' * '.join(parts)}")
                
                # Create a subset DataFrame with only the variables needed for the formula
                formula_vars = [y] + predictor_vars
                print(f"DEBUG: Final formula_vars to include: {formula_vars}")
                print(f"DEBUG: Available columns in df_clean_typed: {list(df_clean_typed.columns)}")
                
                # Check which variables are actually available
                missing_vars = [var for var in formula_vars if var not in df_clean_typed.columns]
                if missing_vars:
                    print(f"DEBUG: WARNING - Missing variables: {missing_vars}")
                
                df_formula = df_clean_typed[formula_vars].copy()
                
                # Remove rows with missing values in the dependent variable
                # OrderedModel doesn't support missing values in categorical endog
                initial_rows = len(df_formula)
                print(f"DEBUG: Before dropna - rows: {initial_rows}, missing values in '{y}': {df_formula[y].isna().sum()}")
                print(f"DEBUG: Sample values in '{y}' before dropna: {df_formula[y].head().tolist()}")
                
                df_formula = df_formula.dropna(subset=[y])
                final_rows = len(df_formula)
                
                print(f"DEBUG: After dropna - rows: {final_rows}, missing values in '{y}': {df_formula[y].isna().sum()}")
                print(f"DEBUG: Sample values in '{y}' after dropna: {df_formula[y].head().tolist()}")
                
                if initial_rows != final_rows:
                    print(f"DEBUG: Removed {initial_rows - final_rows} rows with missing values in dependent variable '{y}'")
                    print(f"DEBUG: Remaining rows: {final_rows}")
                else:
                    print(f"DEBUG: No rows removed - no missing values found in dependent variable '{y}'")
                
                # Ensure proper data types: numerics as numeric, non-numerics as Categorical
                for col in df_formula.columns:
                    if col == y:
                       pass 
                        
                    elif pd.api.types.is_numeric_dtype(df_formula[col]):
                        # Ensure numeric columns are properly typed as numeric
                        df_formula[col] = pd.to_numeric(df_formula[col], errors='coerce')
                    else:
                        # Convert non-numeric columns to Categorical
                        df_formula[col] = df_formula[col].astype('category')
                
                print(f"DEBUG: Data types after conversion for OrderedModel:")
                print(df_formula.dtypes.to_dict())
                
                # Debug: Print what we're passing to OrderedModel
                print(f"OrderedModel - Formula: {formula}")
                print(f"OrderedModel - Data shape: {df_formula.shape}")
                print(f"OrderedModel - Data columns: {list(df_formula.columns)}")
                print(f"OrderedModel - Original categories: {original_categories.get(y, 'Not found')}")
                print(f"DEBUG: First 3 rows of data sent to OrderedModel:")
                print(df_formula.head(3).to_string())
                
                # Fit ordinal regression using OrderedModel
                # Extract dependent variable and predictors
                y_data = df_formula[y]
                X_data = df_formula[predictor_vars]
                
                print(f"DEBUG: OrderedModel - y_data type: {type(y_data)}, shape: {y_data.shape}")
                print(f"DEBUG: OrderedModel - X_data type: {type(X_data)}, shape: {X_data.shape}")
                print(f"DEBUG: OrderedModel - X_data columns: {list(X_data.columns)}")
                print(f"DEBUG: OrderedModel - X_data dtypes: {X_data.dtypes.to_dict()}")
                
                # OrderedModel requires numeric independent variables
                # Convert non-numeric IVs to dummy variables and save schema
                print(f"DEBUG: Converting non-numeric IVs to dummy variables for OrderedModel")
                X_data_numeric = pd.DataFrame()
                dummy_schema = {}  # Store mapping of original variables to dummy variables
                
                for col in X_data.columns:
                    if pd.api.types.is_numeric_dtype(X_data[col]):
                        # Keep numeric variables as-is
                        X_data_numeric[col] = X_data[col]
                        dummy_schema[col] = [col]  # Map to itself
                        print(f"DEBUG: Kept numeric variable '{col}' as-is")
                    else:
                        # Convert non-numeric variables to dummy variables
                        print(f"DEBUG: Converting non-numeric variable '{col}' to dummy variables")
                        dummies = pd.get_dummies(X_data[col], prefix=col, drop_first=True)
                        
                        # Sanitize column names to avoid statsmodels issues with special characters
                        sanitized_columns = []
                        for dummy_col in dummies.columns:
                            # Replace problematic characters with underscores
                            sanitized_col = dummy_col.replace('/', '_').replace(' ', '_').replace('-', '_').replace('(', '_').replace(')', '_')
                            sanitized_columns.append(sanitized_col)
                        
                        # Rename columns to sanitized versions
                        dummies.columns = sanitized_columns
                        
                        # Convert boolean dummy variables to 0/1 for OrderedModel
                        dummies = dummies.astype(int)
                        
                        print(f"DEBUG: Created {len(dummies.columns)} dummy variables: {list(dummies.columns)}")
                        print(f"DEBUG: Dummy variable values: {dummies.iloc[0].to_dict()}")
                        X_data_numeric = pd.concat([X_data_numeric, dummies], axis=1)
                        dummy_schema[col] = list(dummies.columns)  # Store mapping
                
                print(f"DEBUG: Final X_data_numeric shape: {X_data_numeric.shape}")
                print(f"DEBUG: Final X_data_numeric columns: {list(X_data_numeric.columns)}")
                print(f"DEBUG: Dummy schema: {dummy_schema}")
                print(f"DEBUG: X_data_numeric dtypes: {X_data_numeric.dtypes.to_dict()}")
                print(f"DEBUG: y_data dtype: {y_data.dtype}")
                
                # Ensure ALL data is numeric for OrderedModel
                print(f"DEBUG: Ensuring all data is numeric for OrderedModel")
                
            
                print(f"DEBUG: Final X_data_numeric dtypes: {X_data_numeric.dtypes.to_dict()}")
                print(f"DEBUG: Final y_data dtype: {y_data.dtype}")
                print(f"DEBUG: First 3 rows of X data sent to OrderedModel:")
                print(X_data_numeric.head(3).to_string())
                print("Y Data")
                print(y_data.head(3).to_string())
                
                # Create model using the structure: OrderedModel(y_data, X_data_numeric, distr='logit')
                try:
                    model = OrderedModel(y_data, X_data_numeric, distr='logit')  # options: 'logit', 'probit', 'loglog', 'cloglog'
                    print(f"DEBUG: OrderedModel created successfully")
                    
                    # Store the schema for later use in results table
                    model._dummy_schema = dummy_schema
                    
                    # Fit model
                    print(f"DEBUG: Fitting OrderedModel...")
                    model = model.fit(method='bfgs', disp=False)
                    print(f"DEBUG: OrderedModel fitted successfully")
                    print(f"DEBUG: Model converged: {model.mle_retvals.get('converged', 'Unknown')}")
                    print(f"DEBUG: Model loglik: {model.llf}")
                    
                    # Calculate diagnostic metrics for ordinal regression
                    try:
                        diagnostics = _calculate_ordinal_diagnostics(model)
                        setattr(model, "_diagnostics", diagnostics)
                    except Exception as e:
                        print(f"DEBUG: Error calculating ordinal diagnostics: {e}")
                        setattr(model, "_diagnostics", None)
                    
                except Exception as e:
                    print(f"DEBUG: Error creating/fitting OrderedModel: {e}")
                    print(f"DEBUG: Error type: {type(e)}")
                    import traceback
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    raise e
                
                # Debug: Print actual parameter names
                print(f"OrderedModel - Actual parameter names: {list(model.params.index)}")
                
                # Relabel intercepts based on original categories
                print(f"OrderedModel - Checking intercept labeling: y='{y}', original_categories keys: {list(original_categories.keys())}")
                if y in original_categories:
                    categories = original_categories[y]
                    print(f"OrderedModel - Found categories for {y}: {categories}")
                    if len(categories) > 1:
                        # Get the current parameter names
                        param_names = list(model.params.index)
                        
                        # Find intercept parameters (they typically start with the dependent variable name)
                        # OrderedModel intercepts might be in format like "y[0]", "y[1]" or just "0", "1" or "0/1", "1/2"
                        intercept_params = []
                        for name in param_names:
                            if (name.startswith(f"{y}[") and "]" in name) or \
                               (name.isdigit() and int(name) < len(categories)) or \
                               (name.startswith(f"{y}/") and name.count("/") == 1) or \
                               ("/" in name and name.count("/") == 1 and all(part.isdigit() for part in name.split("/"))):
                                intercept_params.append(name)
                        
                        print(f"OrderedModel - Intercept params detected: {intercept_params}")
                        
                        print(f"OrderedModel - Intercept params found: {intercept_params}")
                        if intercept_params:
                            print(f"OrderedModel - Starting intercept labeling process...")
                            # Create new parameter names based on original categories
                            new_param_names = []
                            for name in param_names:
                                if name in intercept_params:
                                    # Extract the threshold index from the parameter name
                                    try:
                                        threshold_idx = None
                                        
                                        # Try different formats
                                        if name.isdigit():
                                            # Format: "0", "1", "2"
                                            threshold_idx = int(name)
                                        elif "/" in name and name.count("/") == 1:
                                            # Format: "0/1", "1/2" or "y/0", "y/1"
                                            parts = name.split("/")
                                            if len(parts) == 2 and parts[0].isdigit():
                                                # Format: "0/1", "1/2" - use the first number as threshold index
                                                threshold_idx = int(parts[0])
                                            elif len(parts) == 2 and parts[1].isdigit():
                                                # Format: "y/0", "y/1" - use the second number as threshold index
                                                threshold_idx = int(parts[1])
                                        else:
                                            # Format: "y[0]", "y[1]"
                                            import re
                                            match = re.search(r'\[(\d+)\]', name)
                                            if match:
                                                threshold_idx = int(match.group(1))
                                        
                                        if threshold_idx is not None and threshold_idx < len(categories) - 1:
                                            # Map to original categories
                                            lower_cat = categories[threshold_idx]
                                            upper_cat = categories[threshold_idx + 1]
                                            new_name = f"{y}[{lower_cat} → {upper_cat}]"
                                            print(f"OrderedModel - Mapped {name} -> {new_name} (threshold_idx={threshold_idx})")
                                        else:
                                            new_name = name
                                            print(f"OrderedModel - Keeping {name} as is (threshold_idx={threshold_idx}, categories_len={len(categories)})")
                                    except:
                                        new_name = name
                                else:
                                    new_name = name
                                new_param_names.append(new_name)
                            
                            # Create a mapping from old names to new names for use in results
                            print(f"OrderedModel - New parameter names: {new_param_names}")
                            intercept_name_mapping = dict(zip(param_names, new_param_names))
                            print(f"OrderedModel - Intercept name mapping: {intercept_name_mapping}")
                            
                            # Store the mapping for later use in results table
                            model._intercept_name_mapping = intercept_name_mapping
                
                regression_type = "Ordinal regression"
                
            elif is_multinomial:
                print(f"DEBUG: ===== TAKING MULTINOMIAL REGRESSION BRANCH =====")
                print(f"DEBUG: Taking multinomial regression branch")
                print(f"DEBUG: is_ordinal = {is_ordinal}, is_multinomial = {is_multinomial}")
                print(f"DEBUG: Dependent variable '{y}' unique values: {df_clean[y].unique()}")
                print(f"DEBUG: Dependent variable '{y}' dtype: {df_clean[y].dtype}")
                print(f"DEBUG: Original categories for '{y}': {original_categories.get(y, 'Not found')}")

                # For multinomial regression, we need to work with the original categorical data
                df_multinomial = df_clean.copy()

                # Always preserve all original categories, even if some are missing in df_clean
                if y in original_categories:
                    df_multinomial[y] = pd.Categorical.from_codes(
                        df_clean[y],
                        categories=original_categories[y],   # preserve full set
                        ordered=False
                    )
                    print(f"DEBUG: Restored categorical variable with categories (preserved): {df_multinomial[y].cat.categories}")
                else:
                    # Fallback: create categorical with all levels present in original df
                    all_levels = sorted(df[y].dropna().unique())
                    df_multinomial[y] = pd.Categorical.from_codes(
                        df_clean[y],
                        categories=all_levels,
                        ordered=False
                    )
                    print(f"DEBUG: Created categorical variable with categories (fallback): {df_multinomial[y].cat.categories}")

                # Fit multinomial regression with smf.mnlogit
                # Parse formula to extract only the variables we need
                _, rhs = formula.split("~", 1)
                # Extract all predictor variables from the RHS
                predictor_vars = []
                interaction_terms = []
                    
                for term in rhs.split("+"):
                    term = term.strip()
                    if term:
                        # Handle interaction terms (e.g., "X1*X2" or "X1*X2*X3" -> create interactions)
                        if "*" in term:
                            parts = [var.strip() for var in term.split("*") if var.strip()]
                            if len(parts) >= 2 and all(part in df_multinomial.columns for part in parts):
                                # Add individual variables
                                predictor_vars.extend(parts)
                            
                            # Create ALL interaction terms (two-way, three-way, etc.)
                            # For A*B*C, create: A:B, A:C, B:C, A:B:C
                            from itertools import combinations
                            for r in range(2, len(parts) + 1):  # r=2 for two-way, r=3 for three-way, etc.
                                for combo in combinations(parts, r):
                                        interaction_name = ":".join(combo)
                                        interaction_terms.append(interaction_name)
                                        predictor_vars.append(interaction_name)
                                        print(f"DEBUG: Created interaction term {interaction_name} = {' * '.join(combo)}")
                        elif ":" in term:
                            # Handle explicit interactions (e.g., "X1:X2" -> keep as is)
                            parts = [var.strip() for var in term.split(":") if var.strip()]
                            if len(parts) == 2 and all(part in df_multinomial.columns for part in parts):
                                # Add individual variables
                                predictor_vars.extend(parts)
                                # Keep the interaction term as is
                            interaction_terms.append(term)
                            predictor_vars.append(term)
                        else:
                            # Simple variable - check if it exists in the original dataframe
                            if term in df_multinomial.columns:
                                predictor_vars.append(term)
                            else:
                                print(f"DEBUG: Variable '{term}' not found in dataframe columns: {list(df_multinomial.columns)}")
                
                # Remove duplicates while preserving order
                predictor_vars = list(dict.fromkeys(predictor_vars))
                
                print(f"DEBUG: Formula parsing results:")
                print(f"DEBUG: Original formula: {formula}")
                print(f"DEBUG: RHS: {rhs}")
                print(f"DEBUG: Extracted predictor_vars: {predictor_vars}")
                print(f"DEBUG: Interaction terms: {interaction_terms}")
                    
                # Create interaction terms in the data
                for interaction in interaction_terms:
                        if ":" in interaction:
                            parts = interaction.split(":")
                        if len(parts) >= 2 and all(part in df_multinomial.columns for part in parts):
                                # Create interaction by multiplying all parts
                                interaction_value = df_multinomial[parts[0]]
                                for part in parts[1:]:
                                    interaction_value = interaction_value * df_multinomial[part]
                                df_multinomial[interaction] = interaction_value
                                print(f"DEBUG: Created interaction term {interaction} = {' * '.join(parts)}")
                print(f"DEBUG: df_multinomial shape: {df_multinomial.shape}")
                print(f"DEBUG: df_multinomial columns: {list(df_multinomial.columns)}")
                print(f"DEBUG: df_multinomial dtypes: {df_multinomial.dtypes.to_dict()}")
                print(f"DEBUG: df_multinomial head: {df_multinomial.head().to_string()}")
                
                # Create a subset DataFrame with only the variables needed for the formula
                formula_vars = [y] + predictor_vars
                print(f"DEBUG: Final formula_vars to include: {formula_vars}")
                print(f"DEBUG: Available columns in df_multinomial: {list(df_multinomial.columns)}")
                
                # Check which variables are actually available
                missing_vars = [var for var in formula_vars if var not in df_multinomial.columns]
                if missing_vars:
                    print(f"DEBUG: WARNING - Missing variables: {missing_vars}")
                
                df_formula = df_multinomial[formula_vars].copy()
                
                # For multinomial regression, we need to convert dependent variable to numeric category codes
                # This prevents patsy from dummy-encoding the dependent variable into multiple columns
                print(f"DEBUG: Converting dependent variable '{y}' to numeric category codes for multinomial regression")
                print(f"DEBUG: Original y values: {df_formula[y].unique()}")
                
                # Store original categories before conversion
                original_y_categories = df_formula[y].astype("category").cat.categories.tolist()
                print(f"DEBUG: Original y categories: {original_y_categories}")
                
                # Store original y data for diagnostics
                y_original_data = df_formula[y].copy()
                
                df_formula[y] = df_formula[y].astype("category").cat.codes
                print(f"DEBUG: Converted y values: {df_formula[y].unique()}")
                
                # Store the mapping for later use
                df_formula._y_categories = original_y_categories
                
               
                
                print(f"DEBUG: Data types after conversion for smf.mnlogit:")
                print(df_formula.dtypes.to_dict())
                
                
                model = smf.mnlogit(formula=formula, data=df_formula).fit(method="newton", maxiter=100, disp=False)
                # Attach mapping info for downstream use
                setattr(model, "_column_mapping", column_mapping)
                setattr(model, "_original_endog_name", column_mapping.get(y, y))
                regression_type = "Multinomial regression"
                print(f"DEBUG: Multinomial model fitted successfully with smf.mnlogit")
                print(f"DEBUG: Model type: {type(model)}")
                print(f"DEBUG: Model params shape: {model.params.shape if hasattr(model.params, 'shape') else 'No shape'}")
                print(f"DEBUG: Model converged: {model.mle_retvals.get('converged', 'Unknown')}")
                print(f"DEBUG: Model loglik: {model.llf}")
                
                # Calculate diagnostic metrics for multinomial logistic regression
                try:
                    diagnostics = _calculate_multinomial_diagnostics(model, y_original_data)
                    setattr(model, "_diagnostics", diagnostics)
                except Exception as e:
                    print(f"DEBUG: Error calculating multinomial diagnostics: {e}")
                    setattr(model, "_diagnostics", None)
                
            elif y_bin:
                # For binary dependent variables, use binomial logistic regression
                # No need to wrap with C() since binary variables don't need reference levels
                print(f"DEBUG: Binary dependent variable detected - using binomial logistic regression")
                print(f"DEBUG: Original formula: {formula}")
                print(f"DEBUG: Dataframe shape: {df_clean.shape}")
                print(f"DEBUG: First 3 rows of dataframe sent to binomial model:")
                print(df_clean.head(3).to_string())
                print(f"DEBUG: EQUATION BEING FED TO smf.glm: '{formula}'")
                model = smf.glm(formula=formula, data=df_clean, family=sm.families.Binomial()).fit()
                # Attach mapping info for downstream use
                setattr(model, "_column_mapping", column_mapping)
                setattr(model, "_original_endog_name", column_mapping.get(y, y))
                regression_type = "Binomial Logistic Regression"
                
                # Calculate diagnostic metrics for binomial logistic regression
                try:
                    diagnostics = _calculate_binomial_diagnostics(model)
                    setattr(model, "_diagnostics", diagnostics)
                except Exception as e:
                    print(f"DEBUG: Error calculating binomial diagnostics: {e}")
                    setattr(model, "_diagnostics", None)
            else:
                # Ensure proper data types: numerics as numeric, non-numerics as Categorical
                df_clean_typed = df_clean.copy()
                for col in df_clean_typed.columns:
                    if pd.api.types.is_numeric_dtype(df_clean_typed[col]):
                        # Ensure numeric columns are properly typed as numeric
                        df_clean_typed[col] = pd.to_numeric(df_clean_typed[col], errors='coerce')
                    else:
                        # Convert non-numeric columns to Categorical
                        df_clean_typed[col] = pd.Categorical(df_clean_typed[col])
                
                print(f"DEBUG: Data types after conversion:")
                print(df_clean_typed.dtypes.to_dict())
                
                # Wrap categorical variables with C() for OLS regression
                print(f"DEBUG: df_clean columns: {df_clean_typed.columns.tolist()}")
                print(f"DEBUG: df_clean dtypes: {df_clean_typed.dtypes.to_dict()}")
                modified_formula = _wrap_categorical_vars_in_formula(formula, df_clean_typed)
                print(f"DEBUG: OLS regression formula: {modified_formula}")
                print(f"DEBUG: Dataframe shape: {df_clean_typed.shape}")
                print(f"DEBUG: First 3 rows of dataframe sent to OLS model:")
                print(df_clean_typed.head(3).to_string())
                print(f"DEBUG: EQUATION BEING FED TO smf.ols: '{modified_formula}'")
                model = smf.ols(formula=modified_formula, data=df_clean_typed).fit()
                # Attach mapping info for downstream use
                setattr(model, "_column_mapping", column_mapping)
                setattr(model, "_original_endog_name", column_mapping.get(y, y))
                regression_type = "OLS regression"
                
                # Calculate diagnostic metrics for OLS regression
                try:
                    diagnostics = _calculate_ols_diagnostics(model)
                    setattr(model, "_diagnostics", diagnostics)
                except Exception as e:
                    print(f"DEBUG: Error calculating OLS diagnostics: {e}")
                    setattr(model, "_diagnostics", None)
        except Exception as e:
            # Check if it's a variable not found error
            error_msg = str(e)
            if "not found" in error_msg.lower() or "keyerror" in error_msg.lower():
                # Try to extract variable names from the formula to check which ones are missing
                _, rhs = formula.split("~", 1)
                all_vars = [s.strip() for s in rhs.replace("+", " ").replace("*", " ").replace(":", " ").split() if s.strip()]
                missing_vars = [var for var in all_vars if var not in df_renamed.columns]
                if missing_vars:
                    available_cols = list(df.columns)
                    # Create suggestions for missing variables
                    suggestions = {}
                    for missing_var in missing_vars:
                        var_suggestions = []
                        for col in available_cols:
                            if col.lower() == missing_var.lower() or missing_var.lower() in col.lower():
                                var_suggestions.append(col)
                        if var_suggestions:
                            suggestions[missing_var] = var_suggestions
                    
                    error_msg = f"Variables not found: {missing_vars}. Available columns: {available_cols}"
                    if suggestions:
                        suggestion_text = "; ".join([f"{var} → {suggestions[var]}" for var in suggestions])
                        error_msg += f". Suggestions: {suggestion_text}"
                    
                    return ["Term", "Estimate"], [{"Term": "Variable Error", "Estimate": error_msg}], {"N": int(df.shape[0])}, None, "Error"
            return ["Term", "Estimate"], [{"Term": "Model error", "Estimate": f"{e}"}], {"N": int(df.shape[0])}, None, "Error"

        # Convert column names back to original names in model results
        def convert_model_names(names, column_mapping):
            """Convert model parameter names back to original column names"""
            converted = []
            for name in names:
                # Check if this is an intercept parameter with custom labeling
                if hasattr(model, '_intercept_name_mapping') and name in model._intercept_name_mapping:
                    # Use the custom intercept label
                    converted.append(model._intercept_name_mapping[name])
                    continue
                
                # Check if this is a mapped name
                original_name = None
                for safe_name, orig_name in column_mapping.items():
                    if name == safe_name or name.startswith(safe_name + ":"):
                        original_name = name.replace(safe_name, orig_name)
                        break
                converted.append(original_name if original_name else name)
            return converted
        
        # Get model parameter names and convert them
        model_names = list(model.params.index)
        print(f"OrderedModel - Before convert_model_names: {model_names}")
        original_names = convert_model_names(model_names, column_mapping)
        print(f"OrderedModel - After convert_model_names: {original_names}")
        
        # Create a mapping for the results
        name_mapping = dict(zip(model_names, original_names))
        
        params = model.params; bse = model.bse
        tvals  = getattr(model, "tvalues", None)
        pvals  = getattr(model, "pvalues", None)

        # VIF per exog (skip intercept)
        vif_map = {}
        if options.get("show_vif"):
            try:
                exog = model.model.exog
                names = list(model.model.exog_names)
                for i, nm in enumerate(names):
                    if nm.lower() in ("const", "intercept"): continue
                    try:
                        # Convert name for VIF display
                        display_nm = name_mapping.get(nm, nm)
                        vif_map[display_nm] = float(variance_inflation_factor(exog, i))
                    except Exception:
                        display_nm = name_mapping.get(nm, nm)
                        vif_map[display_nm] = np.nan
            except Exception:
                pass

        show_t   = bool(options.get("show_t"))
        show_p   = bool(options.get("show_p"))
        show_vif = bool(options.get("show_vif"))
        show_summary = bool(options.get("show_summary"))
        show_se  = bool(options.get("show_se"))
        show_ci  = bool(options.get("show_ci"))

        # Special handling for multinomial regression
        if regression_type == "Multinomial regression":
            print(f"DEBUG: ===== MULTINOMIAL REGRESSION TABLE GENERATION =====")
            print(f"DEBUG: Starting multinomial regression table generation")
            print(f"DEBUG: Model type: {type(model)}")
            print(f"DEBUG: Model params type: {type(model.params)}")
            print(f"DEBUG: Model params shape: {model.params.shape if hasattr(model.params, 'shape') else 'No shape'}")
            print(f"DEBUG: Model params columns: {model.params.columns.tolist() if hasattr(model.params, 'columns') else 'No columns'}")
            print(f"DEBUG: Model params index: {model.params.index.tolist() if hasattr(model.params, 'index') else 'No index'}")
            
            # For multinomial regression, we need to create separate tables for each outcome category
            # Get the outcome categories - use original categories if available
            try:
                # First try to get from original categories (preserves actual DV levels)
                if y in original_categories:
                    outcome_categories = original_categories[y]
                    print(f"DEBUG: Using original outcome categories: {outcome_categories}")
                else:
                    # Fallback: get from model or data
                    outcome_categories = model.model.endog_names
                    print(f"DEBUG: Using model outcome categories: {outcome_categories}")
            except Exception as e:
                print(f"DEBUG: Error getting outcome categories: {e}")
                # Final fallback: get from data
                outcome_categories = sorted(df_renamed[y].dropna().unique().tolist())
                print(f"DEBUG: Fallback outcome categories from data: {outcome_categories}")
            
            # Choose reference category based on alphabetical order
            reference_category = sorted(outcome_categories)[0]  # Alphabetically first category as reference
            
            # Create columns for multinomial regression table (same as other regressions + level to reference)
            cols = ["Term", "Estimate"]
            if show_t:   cols.append("t / z")
            if show_p:   cols.append("p")
            if show_se:  cols.append("Std. Error")
            if show_ci:  cols.append("95% CI")
            # Add the level to reference column for multinomial
            cols.append("Level to Reference")
            
            rows = []
            
            # Extract parameters using the proper method for sm.MNLogit
            params = model.params
            conf = model.conf_int()
            pvalues = model.pvalues
            std_err = model.bse
            
            print(f"DEBUG: Params shape: {params.shape}")
            print(f"DEBUG: Params columns: {params.columns.tolist()}")
            print(f"DEBUG: Params index: {params.index.tolist()}")
            
            # Stack the parameters to get all combinations
            params_stacked = params.stack()
            std_err_stacked = std_err.stack()
            pvalues_stacked = pvalues.stack()
            
            print(f"DEBUG: Stacked params shape: {params_stacked.shape}")
            print(f"DEBUG: Stacked params index: {params_stacked.index.tolist()[:10]}...")  # Show first 10
            print(f"DEBUG: All parameter names: {[name for name, _ in params_stacked.index]}")
            print(f"DEBUG: All outcome categories in stacked params: {[cat for _, cat in params_stacked.index]}")
            print(f"DEBUG: Unique outcome categories in stacked params: {list(set([cat for _, cat in params_stacked.index]))}")
            
            # Debug: Check if specific parameter-outcome combinations exist
            test_param = 'Genre[T.Comedy]'
            test_outcome = 0
            test_key = (test_param, test_outcome)
            print(f"DEBUG: Testing access to {test_key}")
            print(f"DEBUG: Key exists in params_stacked: {test_key in params_stacked.index}")
            if test_key in params_stacked.index:
                print(f"DEBUG: Value for {test_key}: {params_stacked[test_key]}")
            else:
                print(f"DEBUG: Key {test_key} not found in params_stacked.index")
                print(f"DEBUG: Available keys with Genre[T.Comedy]: {[k for k in params_stacked.index if 'Genre[T.Comedy]' in str(k)]}")
            
            # Debug: Check the actual structure of the stacked parameters
            print(f"DEBUG: First 5 stacked parameter keys: {list(params_stacked.index)[:5]}")
            print(f"DEBUG: Type of first key: {type(list(params_stacked.index)[0])}")
            print(f"DEBUG: First key content: {list(params_stacked.index)[0]}")
            
            # Debug: Check if the issue is with the index structure
            print(f"DEBUG: params_stacked.index.names: {params_stacked.index.names}")
            print(f"DEBUG: params_stacked.index.levels: {params_stacked.index.levels}")
            print(f"DEBUG: Available name_mapping: {name_mapping}")
            print(f"DEBUG: Conf shape: {conf.shape}")
            print(f"DEBUG: Conf columns: {conf.columns.tolist()}")
            print(f"DEBUG: Conf index: {conf.index.tolist()}")
            
            # Create name mapping for multinomial regression dummy-encoded parameters
            if not name_mapping:
                print(f"DEBUG: Creating name_mapping for multinomial regression")
                name_mapping = {}
                for param_name in params.index:
                    if param_name == 'Intercept':
                        name_mapping[param_name] = 'Intercept'
                    elif '[' in param_name and ']' in param_name:
                        # Handle dummy-encoded categorical variables like 'Genre[T.Comedy]'
                        base_var = param_name.split('[')[0]
                        category = param_name.split('[')[1].rstrip(']')
                        display_name = f"{base_var} ({category})"
                        name_mapping[param_name] = display_name
                        print(f"DEBUG: Mapped '{param_name}' -> '{display_name}'")
                    else:
                        # Regular variables
                        name_mapping[param_name] = param_name
                        print(f"DEBUG: Mapped '{param_name}' -> '{param_name}'")
                
                print(f"DEBUG: Final name_mapping: {name_mapping}")
            
            # Create a mapping from coded values to actual category names
            # The model uses coded values, but we need to map them to actual category names
            # Get the actual categories from the model's endog_names or use the original categories
            coded_to_actual = {}
            
            # Get the actual coded categories from the model parameters
            actual_coded_categories = list(set([cat for _, cat in params_stacked.index]))
            print(f"DEBUG: Actual coded categories from model: {actual_coded_categories}")
            
            # Map the model's actual coded categories to our outcome categories
            # The model might not have parameters for all categories (e.g., reference category)
            for i, coded_cat in enumerate(sorted(actual_coded_categories)):
                if i < len(outcome_categories):
                    coded_to_actual[coded_cat] = outcome_categories[i]
                    print(f"DEBUG: Mapped coded {coded_cat} -> {outcome_categories[i]}")
                else:
                    coded_to_actual[coded_cat] = f"Category_{coded_cat}"
                    print(f"DEBUG: Mapped coded {coded_cat} -> Category_{coded_cat}")
            
            # Also map any missing categories that should be the reference
            # The reference category (alphabetically first) typically doesn't have parameters
            if len(actual_coded_categories) < len(outcome_categories):
                missing_categories = []
                for i, cat in enumerate(outcome_categories):
                    if i not in actual_coded_categories:
                        missing_categories.append(cat)
                print(f"DEBUG: Missing categories (likely reference): {missing_categories}")
                
                # The first missing category is likely the reference
                if missing_categories:
                    reference_cat = missing_categories[0]
                    print(f"DEBUG: Setting reference category to: {reference_cat}")
                    # Update reference category to the actual missing category
                    reference_category = reference_cat
            
            print(f"DEBUG: Coded to actual mapping: {coded_to_actual}")
            print(f"DEBUG: Available coded categories: {list(coded_to_actual.keys())}")
            print(f"DEBUG: Reference category: {reference_category}")
            
            # Process each parameter-outcome combination
            print(f"DEBUG: Processing {len(params_stacked.index)} parameter-outcome combinations")
            for (param_name, outcome_cat_coded) in params_stacked.index:
                # Convert coded outcome category to actual category name
                outcome_cat_actual = coded_to_actual.get(outcome_cat_coded, f"Category_{outcome_cat_coded}")
                
                print(f"DEBUG: Processing param='{param_name}', coded_cat={outcome_cat_coded}, actual_cat='{outcome_cat_actual}', reference='{reference_category}'")
                
                # Skip if this is the reference category
                if outcome_cat_actual == reference_category:
                    print(f"DEBUG: Skipping {outcome_cat_actual} because it's the reference category")
                    continue
                    
                # Use the original name for display
                display_name = name_mapping.get(param_name, param_name)
                
                # Get values for this parameter-outcome combination (use coded values for model access)
                # Add safety check for missing parameters
                access_key = (param_name, outcome_cat_coded)
                print(f"DEBUG: Attempting to access key: {access_key}")
                print(f"DEBUG: Key exists in params_stacked: {access_key in params_stacked.index}")
                
                try:
                    coef = params_stacked[access_key]
                    se = std_err_stacked[access_key]
                    p = pvalues_stacked[access_key]
                    print(f"DEBUG: Successfully accessed {access_key}: coef={coef}, se={se}, p={p}")
                except KeyError as e:
                    print(f"DEBUG: KeyError accessing parameter {param_name} for outcome {outcome_cat_coded}: {e}")
                    print(f"DEBUG: Available parameter-outcome combinations: {list(params_stacked.index)}")
                    
                    # Try alternative access methods
                    print(f"DEBUG: Trying alternative access methods...")
                    
                    # Method 1: Try accessing by position in the stacked index
                    try:
                        # Find the position of this key in the index
                        key_positions = [i for i, key in enumerate(params_stacked.index) if key == access_key]
                        if key_positions:
                            pos = key_positions[0]
                            coef = params_stacked.iloc[pos]
                            se = std_err_stacked.iloc[pos]
                            p = pvalues_stacked.iloc[pos]
                            print(f"DEBUG: Successfully accessed by position {pos}: coef={coef}, se={se}, p={p}")
                        else:
                            raise KeyError("Key not found in index")
                    except Exception as e2:
                        print(f"DEBUG: Position-based access also failed: {e2}")
                        
                        # Method 2: Try accessing from unstacked parameters
                        try:
                            if param_name in params.index and outcome_cat_coded in params.columns:
                                coef = params.loc[param_name, outcome_cat_coded]
                                se = std_err.loc[param_name, outcome_cat_coded]
                                p = pvalues.loc[param_name, outcome_cat_coded]
                                print(f"DEBUG: Successfully accessed from unstacked: coef={coef}, se={se}, p={p}")
                            else:
                                raise KeyError("Parameter not found in unstacked data")
                        except Exception as e3:
                            print(f"DEBUG: Unstacked access also failed: {e3}")
                            # Skip this parameter-outcome combination
                            continue
                z = coef / se if se != 0 else np.nan
                
                # Get confidence intervals from the unstacked conf DataFrame (use coded values)
                try:
                    # Access confidence intervals directly from the conf DataFrame
                    ci_lower = conf.loc[param_name, outcome_cat_coded][0]  # Lower bound
                    ci_upper = conf.loc[param_name, outcome_cat_coded][1]  # Upper bound
                except (KeyError, IndexError, AttributeError) as e:
                    print(f"DEBUG: Error accessing confidence intervals for {param_name}, {outcome_cat_coded}: {e}")
                    # Fallback: calculate from coefficient and standard error
                    ci_lower = coef - 1.96 * se if np.isfinite(se) else np.nan
                    ci_upper = coef + 1.96 * se if np.isfinite(se) else np.nan
                
                # Calculate odds ratio
                odds_ratio = np.exp(coef) if np.isfinite(coef) else np.nan
                
                # Create row for this predictor-outcome combination (standard format + level to reference)
                est_html = f"{coef:.3f}{_stars(p)}"
                row = {"Term": display_name, "Estimate": est_html}
                
                if show_t:
                    row["t / z"] = f"{z:.3f}" if np.isfinite(z) else "—"
                if show_p:
                    row["p"] = f"{p:.4f}" if np.isfinite(p) else "—"
                if show_se:
                    row["Std. Error"] = f"{se:.3f}" if np.isfinite(se) else "—"
                if show_ci:
                    if np.isfinite(ci_lower) and np.isfinite(ci_upper):
                        row["95% CI"] = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
                    else:
                        row["95% CI"] = "—"
                
                # Add the level to reference column (use actual category names)
                row["Level to Reference"] = f"{outcome_cat_actual} vs. {reference_category}"
                
                rows.append(row)
        elif regression_type == "Ordinal regression":
            # Ordinal regression table generation - show all model parameters (main effects + interactions)
            # but handle threshold parameters separately
            cols = ["Term", "Estimate"]
            if show_t:   cols.append("t / z")
            if show_p:   cols.append("p")
            if show_se:  cols.append("Std. Error")
            if show_ci:  cols.append("95% CI")

            rows = []
            
            # Separate threshold parameters from other parameters
            threshold_params = []
            other_params = []
            
            for name in params.index:
                # Check if this is a threshold parameter
                # Threshold parameters are typically numeric (0, 1, 2) or contain "/" (0/1, 1/2)
                is_threshold = (name.isdigit() and int(name) < 10) or ("/" in name and name.count("/") == 1)
                
                if is_threshold:
                    threshold_params.append(name)
                else:
                    other_params.append(name)
            
            # Show threshold parameters first (if any)
            for name in threshold_params:
                display_name = name_mapping.get(name, name)
                coef = params.loc[name]
                se   = bse.loc[name] if name in bse.index else np.nan
                p    = pvals.loc[name] if pvals is not None and name in pvals.index else np.nan

                # Ensure all values are scalars to avoid Series boolean ambiguity
                if hasattr(coef, 'iloc'):
                    coef = coef.iloc[0] if len(coef) > 0 else np.nan
                elif hasattr(coef, 'item'):
                    coef = coef.item()
                    
                if hasattr(se, 'iloc'):
                    se = se.iloc[0] if len(se) > 0 else np.nan
                elif hasattr(se, 'item'):
                    se = se.item()
                    
                if hasattr(p, 'iloc'):
                    p = p.iloc[0] if len(p) > 0 else np.nan
                elif hasattr(p, 'item'):
                    p = p.item()
                
                # Calculate 95% CI
                ci_lower = coef - 1.96 * se if np.isfinite(se) else np.nan
                ci_upper = coef + 1.96 * se if np.isfinite(se) else np.nan

                # Estimate column without std error in parentheses
                est_html = f"{coef:.3f}{_stars(p)}"
                row = {"Term": display_name, "Estimate": est_html}
                
                if show_t:
                    tv = tvals.loc[name] if tvals is not None and name in tvals.index else np.nan
                    # Ensure tv is a scalar value to avoid Series boolean ambiguity
                    if hasattr(tv, 'iloc'):
                        tv = tv.iloc[0] if len(tv) > 0 else np.nan
                    elif hasattr(tv, 'item'):
                        tv = tv.item()
                    row["t / z"] = f"{tv:.3f}" if np.isfinite(tv) else "—"
                if show_p:
                    row["p"] = f"{p:.4f}" if np.isfinite(p) else "—"
                if show_se:
                    row["Std. Error"] = f"{se:.3f}" if np.isfinite(se) else "—"
                if show_ci:
                    if np.isfinite(ci_lower) and np.isfinite(ci_upper):
                        row["95% CI"] = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
                    else:
                        row["95% CI"] = "—"
                rows.append(row)
            
            # Show other parameters (main effects + interactions)
            for name in other_params:
                display_name = name_mapping.get(name, name)
                coef = params.loc[name]
                se   = bse.loc[name] if name in bse.index else np.nan
                p    = pvals.loc[name] if pvals is not None and name in pvals.index else np.nan

                # Ensure all values are scalars to avoid Series boolean ambiguity
                if hasattr(coef, 'iloc'):
                    coef = coef.iloc[0] if len(coef) > 0 else np.nan
                elif hasattr(coef, 'item'):
                    coef = coef.item()
                    
                if hasattr(se, 'iloc'):
                    se = se.iloc[0] if len(se) > 0 else np.nan
                elif hasattr(se, 'item'):
                    se = se.item()
                    
                if hasattr(p, 'iloc'):
                    p = p.iloc[0] if len(p) > 0 else np.nan
                elif hasattr(p, 'item'):
                    p = p.item()
                
                # Calculate 95% CI
                ci_lower = coef - 1.96 * se if np.isfinite(se) else np.nan
                ci_upper = coef + 1.96 * se if np.isfinite(se) else np.nan

                # Estimate column without std error in parentheses
                est_html = f"{coef:.3f}{_stars(p)}"
                row = {"Term": display_name, "Estimate": est_html}
                
                if show_t:
                    tv = tvals.loc[name] if tvals is not None and name in tvals.index else np.nan
                    # Ensure tv is a scalar value to avoid Series boolean ambiguity
                    if hasattr(tv, 'iloc'):
                        tv = tv.iloc[0] if len(tv) > 0 else np.nan
                    elif hasattr(tv, 'item'):
                        tv = tv.item()
                    row["t / z"] = f"{tv:.3f}" if np.isfinite(tv) else "—"
                if show_p:
                    row["p"] = f"{p:.4f}" if np.isfinite(p) else "—"
                if show_se:
                    row["Std. Error"] = f"{se:.3f}" if np.isfinite(se) else "—"
                if show_ci:
                    if np.isfinite(ci_lower) and np.isfinite(ci_upper):
                        row["95% CI"] = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
                    else:
                        row["95% CI"] = "—"
                rows.append(row)
        else:
            # Standard regression table generation (linear, logistic)
            cols = ["Term", "Estimate"]
            if show_t:   cols.append("t / z")
            if show_p:   cols.append("p")
            if show_se:  cols.append("Std. Error")
            if show_ci:  cols.append("95% CI")

            rows = []
            
            for name in params.index:
                # Use the original name for display
                display_name = name_mapping.get(name, name)
                coef = params.loc[name]
                se   = bse.loc[name] if name in bse.index else np.nan
                p    = pvals.loc[name] if pvals is not None and name in pvals.index else np.nan

                # Ensure all values are scalars to avoid Series boolean ambiguity
                if hasattr(coef, 'iloc'):
                    coef = coef.iloc[0] if len(coef) > 0 else np.nan
                elif hasattr(coef, 'item'):
                    coef = coef.item()
                    
                if hasattr(se, 'iloc'):
                    se = se.iloc[0] if len(se) > 0 else np.nan
                elif hasattr(se, 'item'):
                    se = se.item()
                    
                if hasattr(p, 'iloc'):
                    p = p.iloc[0] if len(p) > 0 else np.nan
                elif hasattr(p, 'item'):
                    p = p.item()
                
                # Calculate 95% CI
                ci_lower = coef - 1.96 * se if np.isfinite(se) else np.nan
                ci_upper = coef + 1.96 * se if np.isfinite(se) else np.nan

                # Estimate column without std error in parentheses
                est_html = f"{coef:.3f}{_stars(p)}"
                row = {"Term": display_name, "Estimate": est_html}
                
                if show_t:
                    tv = tvals.loc[name] if tvals is not None and name in tvals.index else np.nan
                    # Ensure tv is a scalar value to avoid Series boolean ambiguity
                    if hasattr(tv, 'iloc'):
                        tv = tv.iloc[0] if len(tv) > 0 else np.nan
                    elif hasattr(tv, 'item'):
                        tv = tv.item()
                    row["t / z"] = f"{tv:.3f}" if np.isfinite(tv) else "—"
                if show_p:
                    row["p"] = f"{p:.4f}" if np.isfinite(p) else "—"
                if show_se:
                    row["Std. Error"] = f"{se:.3f}" if np.isfinite(se) else "—"
                if show_ci:
                    if np.isfinite(ci_lower) and np.isfinite(ci_upper):
                        row["95% CI"] = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
                    else:
                        row["95% CI"] = "—"
                rows.append(row)

        # Model-level stats
        stats_all = {"N": int(model.nobs)}
        if regression_type == "Multinomial regression":
            # For multinomial regression, calculate pseudo R-squared
            pseudo_r2 = _calculate_pseudo_r2(model)
            if not np.isnan(pseudo_r2["McFadden"]):
                stats_all["Pseudo_R²__McFadden_"] = float(pseudo_r2["McFadden"])
            if not np.isnan(pseudo_r2["CoxSnell"]):
                stats_all["Pseudo_R²__Cox_Snell_"] = float(pseudo_r2["CoxSnell"])
            if not np.isnan(pseudo_r2["Nagelkerke"]):
                stats_all["Pseudo_R²__Nagelkerke_"] = float(pseudo_r2["Nagelkerke"])
        elif regression_type == "Ordinal regression":
            # For ordinal regression, calculate pseudo R-squared
            pseudo_r2 = _calculate_pseudo_r2(model)
            if not np.isnan(pseudo_r2["McFadden"]):
                stats_all["Pseudo_R²__McFadden_"] = float(pseudo_r2["McFadden"])
            if not np.isnan(pseudo_r2["CoxSnell"]):
                stats_all["Pseudo_R²__Cox_Snell_"] = float(pseudo_r2["CoxSnell"])
            if not np.isnan(pseudo_r2["Nagelkerke"]):
                stats_all["Pseudo_R²__Nagelkerke_"] = float(pseudo_r2["Nagelkerke"])
        elif y_bin:
            # For binary logistic regression, use built-in pseudo R-squared if available
            pr2 = getattr(model, "prsquared", None)
            if pr2 is not None:
                stats_all["Pseudo R² (McFadden)"] = float(pr2)
            else:
                # Calculate pseudo R² if not available
                pseudo_r2 = _calculate_pseudo_r2(model)
                if not np.isnan(pseudo_r2["McFadden"]):
                    stats_all["Pseudo R² (McFadden)"] = float(pseudo_r2["McFadden"])
        else:
            # For linear regression, use standard R²
            stats_all["R²"] = float(getattr(model, "rsquared", np.nan))
            stats_all["Adj. R²"] = float(getattr(model, "rsquared_adj", np.nan))
        stats_all["AIC"] = float(getattr(model, "aic", np.nan))
        stats_all["BIC"] = float(getattr(model, "bic", np.nan))

        stats_filtered = {"N": stats_all["N"]}
        if options.get("show_r2"):
            if regression_type == "Multinomial regression":
                # Show all available pseudo R² measures for multinomial regression
                if "Pseudo_R²__McFadden_" in stats_all:
                    stats_filtered["Pseudo_R²__McFadden_"] = stats_all["Pseudo_R²__McFadden_"]
                if "Pseudo_R²__Cox_Snell_" in stats_all:
                    stats_filtered["Pseudo_R²__Cox_Snell_"] = stats_all["Pseudo_R²__Cox_Snell_"]
                if "Pseudo_R²__Nagelkerke_" in stats_all:
                    stats_filtered["Pseudo_R²__Nagelkerke_"] = stats_all["Pseudo_R²__Nagelkerke_"]
            elif regression_type == "Ordinal regression":
                # Show all available pseudo R² measures for ordinal regression
                if "Pseudo_R²__McFadden_" in stats_all:
                    stats_filtered["Pseudo_R²__McFadden_"] = stats_all["Pseudo_R²__McFadden_"]
                if "Pseudo_R²__Cox_Snell_" in stats_all:
                    stats_filtered["Pseudo_R²__Cox_Snell_"] = stats_all["Pseudo_R²__Cox_Snell_"]
                if "Pseudo_R²__Nagelkerke_" in stats_all:
                    stats_filtered["Pseudo_R²__Nagelkerke_"] = stats_all["Pseudo_R²__Nagelkerke_"]
            elif y_bin:
                # For binary logistic regression
                if "Pseudo R² (McFadden)" in stats_all:
                    stats_filtered["Pseudo R² (McFadden)"] = stats_all["Pseudo R² (McFadden)"]
            else:
                # For linear regression, use standard R²
                stats_filtered["R²"] = stats_all.get("R²")
                stats_filtered["Adj. R²"] = stats_all.get("Adj. R²")
        if options.get("show_aic"): stats_filtered["AIC"] = stats_all["AIC"]
        if options.get("show_bic"): stats_filtered["BIC"] = stats_all["BIC"]
        
        # Get diagnostics if available (for all regression types)
        diagnostics = None
        if hasattr(model, "_diagnostics") and model._diagnostics is not None:
            diagnostics = model._diagnostics

        return cols, rows, stats_filtered, model, regression_type, diagnostics

    @staticmethod
    def _pre_generate_multinomial_predictions(fitted_model, df, interactions):
        """Pre-generate probability predictions for all multinomial regression level/interaction combinations."""
        print(f"DEBUG: _pre_generate_multinomial_predictions called")
        print(f"DEBUG: interactions = {interactions}")
        print(f"DEBUG: fitted_model type = {type(fitted_model)}")
        print(f"DEBUG: fitted_model str = {str(type(fitted_model))}")
        
        if not interactions or not fitted_model:
            print(f"DEBUG: No interactions or fitted_model, returning None")
            return None
            
        # Check if this is a multinomial regression model - use same logic as ordinal
        if not ('MultinomialResults' in str(type(fitted_model)) or hasattr(fitted_model, 'model') and 'mnlogit' in str(type(fitted_model.model))):
            print(f"DEBUG: Not a multinomial model, returning None")
            print(f"DEBUG: Model type: {type(fitted_model)}")
            return None
            
        # Get the dependent variable and its categories
        y_var = fitted_model.model.endog_names
        if y_var not in df.columns:
            return None
            
        categories = sorted(df[y_var].dropna().unique())
        print(f"DEBUG: Categories found: {categories}")
        predictions = {}
        
        for interaction in interactions:
            if "*" in interaction:
                x, m = [p.strip() for p in interaction.split("*", 1)]
            else:
                parts = interaction.split(":")
                if len(parts) == 2:
                    x, m = parts[0].strip(), parts[1].strip()
                else:
                    continue
                    
            if x not in df.columns or m not in df.columns:
                continue
                
            # Generate predictions for this interaction
            interaction_predictions = {}
            
            # Create grid for predictions (similar to spotlight plot logic)
            x_vals = df[x].dropna()
            m_vals = df[m].dropna()
            
            if pd.api.types.is_numeric_dtype(x_vals):
                x_grid = np.linspace(x_vals.min(), x_vals.max(), 50)
            else:
                x_grid = x_vals.unique()
                
            if pd.api.types.is_numeric_dtype(m_vals):
                # Use mean ± 1sd for low/high moderator levels
                mean_val = m_vals.mean()
                std_val = m_vals.std()
                mod_levels = [mean_val - std_val, mean_val + std_val]  # low and high
            else:
                # For categorical, use first and last unique values
                unique_vals = m_vals.unique()
                if len(unique_vals) >= 2:
                    mod_levels = [unique_vals[0], unique_vals[-1]]
                else:
                    mod_levels = unique_vals
            
            # Generate predictions for each moderator level
            for mval in mod_levels:
                grid = pd.DataFrame({x: x_grid, m: mval})
                
                # Add missing regressors at default values
                for nm in fitted_model.model.exog_names:
                    if nm in ("Intercept", "const"): 
                        continue
                    if nm not in grid.columns and nm in df.columns:
                        if pd.api.types.is_numeric_dtype(df[nm]):
                            grid[nm] = df[nm].mean()
                        else:
                            # For categorical variables, use mode (most frequent value)
                            grid[nm] = df[nm].mode().iloc[0]
                
                try:
                    print(f"DEBUG: About to predict with grid shape: {grid.shape}")
                    print(f"DEBUG: Grid columns: {grid.columns.tolist()}")
                    print(f"DEBUG: Grid sample (first row): {grid.iloc[0].tolist()}")
                    print(f"DEBUG: Model exog_names: {fitted_model.model.exog_names}")
                    
                    # Check if this is a formula-based model or manually parsed model
                    if hasattr(fitted_model, 'model') and hasattr(fitted_model.model, 'formula'):
                        # Formula-based model: pass original variables and let patsy handle design matrix
                        print(f"DEBUG: Using formula-based prediction")
                        pred_probs = fitted_model.predict(grid)
                    else:
                        # Manually parsed model: need to build design matrix manually
                        print(f"DEBUG: Using manual design matrix construction")
                        
                        # Build the design matrix in the same format as the model
                        grid_for_pred = pd.DataFrame()
                        
                        # Add constant term if present
                        if 'const' in fitted_model.model.exog_names:
                            grid_for_pred['const'] = 1.0
                        
                        # Add variables in the same order as the model
                        for var_name in fitted_model.model.exog_names:
                            if var_name == 'const':
                                continue
                            
                            # Check if this is an interaction term
                            if ':' in var_name:
                                # This is an interaction term - create it by multiplying component variables
                                parts = var_name.split(':')
                                print(f"DEBUG: Creating interaction term {var_name} from parts: {parts}")
                                
                                # Check if all parts are available
                                if all(part in grid.columns for part in parts):
                                    # Create interaction by multiplying component variables
                                    interaction_value = grid[parts[0]]
                                    for part in parts[1:]:
                                        # Check if both variables are numeric
                                        if pd.api.types.is_numeric_dtype(grid[parts[0]]) and pd.api.types.is_numeric_dtype(grid[part]):
                                            # Both numeric - can multiply
                                            val1 = pd.to_numeric(interaction_value, errors='coerce').fillna(0.0)
                                            val2 = pd.to_numeric(grid[part], errors='coerce').fillna(0.0)
                                            interaction_value = val1 * val2
                                        else:
                                            # At least one is categorical - use string concatenation for interaction
                                            interaction_value = interaction_value.astype(str) + "_" + grid[part].astype(str)
                                    grid_for_pred[var_name] = interaction_value
                                    print(f"DEBUG: Created interaction {var_name} = {' * '.join(parts)}")
                                else:
                                    print(f"DEBUG: Warning - Cannot create interaction {var_name}, missing parts: {[p for p in parts if p not in grid.columns]}")
                                    grid_for_pred[var_name] = 0.0
                            elif var_name in grid.columns:
                                # Use values from grid, but handle categorical variables properly
                                values = grid[var_name]
                                
                                # For categorical variables, keep them as-is since C() wrapper handles them
                                if not pd.api.types.is_numeric_dtype(values):
                                    # Keep categorical variables as their original values
                                    # The C() wrapper in the formula will handle the encoding
                                    print(f"DEBUG: Keeping categorical variable '{var_name}' as-is: {values.iloc[0] if len(values) > 0 else 'empty'}")
                                
                                grid_for_pred[var_name] = values
                            elif var_name in df.columns:
                                # Use mean for missing variables
                                if pd.api.types.is_numeric_dtype(df[var_name]):
                                    grid_for_pred[var_name] = df[var_name].mean()
                                else:
                                    grid_for_pred[var_name] = df[var_name].mode().iloc[0]
                            else:
                                # Variable not found, use 0
                                grid_for_pred[var_name] = 0.0
                        
                        # Ensure the order matches the model
                        grid_for_pred = grid_for_pred[fitted_model.model.exog_names]
                        
                        print(f"DEBUG: Grid for prediction shape: {grid_for_pred.shape}")
                        print(f"DEBUG: Grid for prediction columns: {grid_for_pred.columns.tolist()}")
                        
                        pred_probs = fitted_model.predict(grid_for_pred)
                    
                    # Check for NaNs and raise error if found
                    if hasattr(pred_probs, 'isnull') and pred_probs.isnull().any().any():
                        raise ValueError(
                            f"Multinomial predict produced NaNs for {interaction} at {m}={mval}. "
                            "This usually means the grid is missing required variables or has invalid values. "
                            f"Grid columns: {grid.columns.tolist()}, "
                            f"Grid shape: {grid.shape}, "
                            f"Any NaN in grid: {grid.isnull().any().any()}"
                        )
                    
                    print(f"DEBUG: pred_probs shape: {pred_probs.shape}")
                    print(f"DEBUG: pred_probs columns: {pred_probs.columns.tolist() if hasattr(pred_probs, 'columns') else 'No columns'}")
                    print(f"DEBUG: pred_probs sample (first row): {pred_probs.iloc[0].tolist() if hasattr(pred_probs, 'iloc') else pred_probs[0]}")
                    print(f"DEBUG: pred_probs sum (first row): {pred_probs.iloc[0].sum() if hasattr(pred_probs, 'iloc') else pred_probs[0].sum()}")
                    
                    # Store predictions for each category
                    level_predictions = {}
                    
                    # For multinomial regression, pred_probs is a DataFrame with columns for each category
                    if hasattr(pred_probs, 'columns'):
                        # Map each category to its predictions
                        for i, category in enumerate(categories):
                            if i < pred_probs.shape[1]:
                                # Ensure all values are JSON-serializable
                                x_values = x_grid.tolist() if hasattr(x_grid, 'tolist') else list(x_grid)
                                probabilities = pred_probs.iloc[:, i].tolist() if hasattr(pred_probs.iloc[:, i], 'tolist') else list(pred_probs.iloc[:, i])
                                
                                # Convert numpy types to Python types, but preserve NaN values
                                x_values = [float(x) if np.isfinite(x) else None for x in x_values]
                                probabilities = [float(p) if np.isfinite(p) else None for p in probabilities]
                                
                                level_predictions[category] = {
                                    'x_values': x_values,
                                    'probabilities': probabilities
                                }
                                print(f"DEBUG: Stored predictions for category {category} (index {i}): {len(probabilities)} values")
                    else:
                        # If pred_probs is not a DataFrame, treat as array
                        for i, category in enumerate(categories):
                            if i < pred_probs.shape[1]:
                                # Ensure all values are JSON-serializable
                                x_values = x_grid.tolist() if hasattr(x_grid, 'tolist') else list(x_grid)
                                probabilities = pred_probs[:, i].tolist() if hasattr(pred_probs[:, i], 'tolist') else list(pred_probs[:, i])
                                
                                # Convert numpy types to Python types, but preserve NaN values
                                x_values = [float(x) if np.isfinite(x) else None for x in x_values]
                                probabilities = [float(p) if np.isfinite(p) else None for p in probabilities]
                                
                                level_predictions[category] = {
                                    'x_values': x_values,
                                    'probabilities': probabilities
                                }
                                print(f"DEBUG: Stored predictions for category {category} (index {i}): {len(probabilities)} values")
                    
                    interaction_predictions[str(mval)] = level_predictions
                    
                except Exception as e:
                    print(f"Error generating predictions for {interaction} at {m}={mval}: {e}")
                    continue
            
            predictions[interaction] = interaction_predictions
            
        # Final JSON serialization check
        try:
            import json
            json.dumps(predictions)  # Test if predictions are JSON-serializable
            print(f"DEBUG: Predictions are JSON-serializable")
        except Exception as e:
            print(f"DEBUG: Predictions are NOT JSON-serializable: {e}")
            # Convert any remaining non-serializable objects
            predictions = RegressionModule._ensure_json_serializable(predictions)
            
        return predictions

    @staticmethod
    def _ensure_json_serializable(obj):
        """Recursively convert numpy types and other non-JSON-serializable objects to Python types."""
        if isinstance(obj, dict):
            return {key: RegressionModule._ensure_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [RegressionModule._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, 'tolist'):  # numpy arrays
            return obj.tolist()
        elif hasattr(obj, 'item'):  # numpy scalars
            return obj.item()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj) if np.isfinite(obj) else None
        else:
            return obj

    @staticmethod
    def _pre_generate_ordinal_predictions(fitted_model, df, interactions):
        """Pre-generate probability predictions for all ordinal regression level/interaction combinations."""
        print(f"DEBUG: _pre_generate_ordinal_predictions called")
        print(f"DEBUG: interactions = {interactions}")
        print(f"DEBUG: fitted_model type = {type(fitted_model)}")
        print(f"DEBUG: fitted_model str = {str(type(fitted_model))}")
        
        if not interactions:
            print(f"DEBUG: No interactions provided, returning None")
            return None
            
        if 'OrderedModel' not in str(type(fitted_model.model)):
            print(f"DEBUG: Not an OrderedModel, returning None")
            return None
            
        # Get the dependent variable and its categories
        y_var = fitted_model.model.endog_names
        print(f"DEBUG: y_var = {y_var}")
        if y_var not in df.columns:
            print(f"DEBUG: y_var {y_var} not in df.columns, returning None")
            return None
            
        categories = sorted(df[y_var].dropna().unique())
        print(f"DEBUG: categories = {categories}")
        predictions = {}
        
        for interaction in interactions:
            print(f"DEBUG: Processing interaction: {interaction}")
            if "*" in interaction:
                x, m = [p.strip() for p in interaction.split("*", 1)]
            else:
                parts = interaction.split(":")
                if len(parts) == 2:
                    x, m = parts[0].strip(), parts[1].strip()
                else:
                    print(f"DEBUG: Invalid interaction format: {interaction}")
                    continue
                    
            print(f"DEBUG: x = {x}, m = {m}")
            if x not in df.columns or m not in df.columns:
                print(f"DEBUG: Variables not found - x in df: {x in df.columns}, m in df: {m in df.columns}")
                continue
                
            # Generate predictions for this interaction
            interaction_predictions = {}
            
            # Create grid for predictions (similar to spotlight plot logic)
            x_vals = df[x].dropna()
            m_vals = df[m].dropna()
            
            if pd.api.types.is_numeric_dtype(x_vals):
                x_grid = np.linspace(x_vals.min(), x_vals.max(), 50)
            else:
                x_grid = x_vals.unique()
                
            if pd.api.types.is_numeric_dtype(m_vals):
                # Use mean ± 1sd for low/high moderator levels
                mean_val = m_vals.mean()
                std_val = m_vals.std()
                mod_levels = [mean_val - std_val, mean_val + std_val]  # low and high
            else:
                # For categorical, use first and last unique values
                unique_vals = m_vals.unique()
                if len(unique_vals) >= 2:
                    mod_levels = [unique_vals[0], unique_vals[-1]]
                else:
                    mod_levels = unique_vals
            
            # Generate predictions for each moderator level
            for mval in mod_levels:
                grid = pd.DataFrame({x: x_grid, m: mval}, index=range(len(x_grid)))
                
                # Build the grid properly for ordinal models (same as spotlight plot logic)
                # Only include variables that are actually in the model parameters
                param_vars = []
                for param_name in fitted_model.params.index:
                    # Skip threshold parameters (they don't correspond to variables)
                    if not any(char.isdigit() for char in str(param_name)):
                        param_vars.append(param_name)
                
                print(f"DEBUG: Variables from model params: {param_vars}")
                
                # Add missing regressors at default values
                for nm in param_vars:
                    if nm not in grid.columns:
                        if nm in df.columns:
                            if pd.api.types.is_numeric_dtype(df[nm]):
                                grid[nm] = df[nm].mean()
                                print(f"DEBUG: Used mean value for numeric '{nm}': {df[nm].mean()}")
                            else:
                                # For categorical variables, use the mode (most frequent value) as-is
                                mode_val = df[nm].mode().iloc[0]
                                grid[nm] = mode_val
                                print(f"DEBUG: Used categorical value '{nm}' in ordinal grid: {mode_val}")
                        else:
                            # Check if this is actually a dummy variable by looking for patterns
                            # Dummy variables typically have patterns like "VariableName[T.Category]"
                            if '[' in nm and ']' in nm:
                                # This is likely a dummy variable from categorical encoding
                                grid[nm] = 0
                                print(f"DEBUG: Set dummy variable '{nm}' to 0 in ordinal grid (categorical encoding)")
                            else:
                                # This might be a missing variable, try to find it in the dataframe
                                # Check if there's a similar variable name (case-insensitive)
                                similar_vars = [col for col in df.columns if col.lower() == nm.lower()]
                                if similar_vars:
                                    actual_var = similar_vars[0]
                                    if pd.api.types.is_numeric_dtype(df[actual_var]):
                                        mean_val = df[actual_var].mean()
                                        grid[nm] = mean_val
                                        print(f"DEBUG: Found similar variable '{actual_var}' for '{nm}', used mean: {mean_val}")
                                    else:
                                        mode_val = df[actual_var].mode().iloc[0]
                                        grid[nm] = mode_val
                                        print(f"DEBUG: Found similar variable '{actual_var}' for '{nm}', used mode: {mode_val}")
                                else:
                                    # No similar variable found, set to 0
                                    grid[nm] = 0
                                    print(f"DEBUG: Set missing variable '{nm}' to 0 in ordinal grid (no similar variable found)")
            
                # Create interaction terms in the grid
                if f"{x}:{m}" in param_vars:
                    grid[f"{x}:{m}"] = grid[x] * grid[m]
                    print(f"DEBUG: Created interaction {x}:{m} in grid")
                
                print(f"DEBUG: Grid columns before prediction: {grid.columns.tolist()}")
                print(f"DEBUG: Grid shape before prediction: {grid.shape}")
                
                try:
                    # Get probability predictions for all categories
                    pred_probs = fitted_model.predict(grid)
                    
                    # Store predictions for each category
                    level_predictions = {}
                    for i, category in enumerate(categories):
                        if hasattr(pred_probs, 'iloc'):
                            if i < pred_probs.shape[1]:
                                level_predictions[category] = {
                                    'x_values': x_grid.tolist(),
                                    'probabilities': pred_probs.iloc[:, i].tolist()
                                }
                        else:
                            if i < pred_probs.shape[1]:
                                level_predictions[category] = {
                                    'x_values': x_grid.tolist(),
                                    'probabilities': pred_probs[:, i].tolist()
                                }
                    
                    interaction_predictions[str(mval)] = level_predictions
                    
                except Exception as e:
                    print(f"Error generating predictions for {interaction} at {m}={mval}: {e}")
                    continue
            
            predictions[interaction] = interaction_predictions
            
        print(f"DEBUG: Final predictions: {predictions}")
        return predictions

    @staticmethod
    def _unpack_fit_result(fit_result):
        """Unpack fit result handling both old and new return formats."""
        if len(fit_result) == 5:
            return fit_result + (None,)
        elif len(fit_result) == 6:
            return fit_result
        else:
            return fit_result[:5] + (None,)
    
    @staticmethod
    def _generate_predictions(fitted_model, regression_type, df, interactions):
        """Generate ordinal/multinomial predictions if applicable."""
        ordinal_predictions = None
        multinomial_predictions = None
        
        if fitted_model is not None:
            if 'Ordinal regression' in regression_type:
                ordinal_predictions = RegressionModule._pre_generate_ordinal_predictions(fitted_model, df, interactions)
            elif 'Multinomial regression' in regression_type:
                multinomial_predictions = RegressionModule._pre_generate_multinomial_predictions(fitted_model, df, interactions)
        
        return ordinal_predictions, multinomial_predictions
    
    def run(df, formula, analysis_type, outdir, options, schema_types=None, schema_orders=None):
        # Check if this is a multi-equation format (multiple lines with ~)
        lines = [line.strip() for line in formula.split('\n') if line.strip()]
        equation_lines = [line for line in lines if '~' in line]
        
        print(f"=== REGRESSION MODULE DIAGNOSTICS ===")
        print(f"Formula: {formula}")
        print(f"Total lines (non-empty): {len(lines)}")
        print(f"Equation lines (with ~): {len(equation_lines)}")
        print(f"Equation lines: {equation_lines}")
        
        # If multiple equations, use multi-equation handler
        if len(equation_lines) > 1:
            print(f"✓ MULTI-EQUATION DETECTED: Routing to _run_multi_equation with {len(equation_lines)} equations")
            print(f"=== END REGRESSION MODULE DIAGNOSTICS ===")
            return RegressionModule._run_multi_equation(df, equation_lines, analysis_type, outdir, options, schema_types, schema_orders)
        
        print(f"Single equation detected - using standard fit_models")
        print(f"=== END REGRESSION MODULE DIAGNOSTICS ===")
        
        # 1) Fit model + table (single equation)
        fit_result = RegressionModule._fit_models(df, formula, options, schema_types, schema_orders)
        model_cols, model_rows, model_stats, fitted_model, regression_type, diagnostics = RegressionModule._unpack_fit_result(fit_result)

        # 2) Parse formula to get interactions
        _, _, interactions = _parse_formula(formula)

        # 2.5) Pre-generate predictions if applicable
        ordinal_predictions, multinomial_predictions = RegressionModule._generate_predictions(fitted_model, regression_type, df, interactions)

        # 3) Interactive spotlight (generate for all interactions)
        spotlight_json = None
        if interactions and fitted_model is not None:
            # Use the first interaction for the default spotlight plot
            # Individual interactions will be handled dynamically
            for inter in interactions:
                if "*" in inter:
                    x, m = [p.strip() for p in inter.split("*", 1)]
                else:
                    # Handle explicit interactions (x:y format)
                    parts = inter.split(":")
                    if len(parts) == 2:
                        x, m = parts[0].strip(), parts[1].strip()
                    else:
                        continue
                
                if x in df.columns and m in df.columns:
                    spotlight_json = _build_spotlight_json(fitted_model, df, x, m, options)
                    break  # Use the first valid interaction

        # 4) Summary statistics (always generate)
        summary_stats = _generate_summary_stats(df, formula, fitted_model)

        # 5) Get continuous variables for correlation heatmap (from equation by default)
        continuous_vars = _get_continuous_variables_from_formula(df, formula)
        
        # If no continuous variables in equation, fall back to all continuous variables
        if len(continuous_vars) < 2:
            continuous_vars = _get_continuous_variables(df)
        
        # 6) Get all numeric variables for summary table editing
        all_numeric_vars = _get_all_numeric_variables(df)

        # VIF is now included in summary_stats

        # Convert diagnostics DataFrame to list of dicts for template
        diagnostics_list = None
        if diagnostics is not None:
            try:
                if hasattr(diagnostics, 'to_dict'):
                    diagnostics_list = diagnostics.to_dict('records')
                else:
                    # Already a list
                    diagnostics_list = diagnostics if isinstance(diagnostics, list) else None
            except Exception as e:
                print(f"DEBUG: Error converting diagnostics to list: {e}")
                diagnostics_list = None

        return {
            # interactive figures as JSON blobs
            "spotlight_json": spotlight_json,

            # ordinal regression pre-generated predictions
            "ordinal_predictions": ordinal_predictions,
            
            # multinomial regression pre-generated predictions
            "multinomial_predictions": multinomial_predictions,

            # regression table
            "model_table_cols": model_cols,
            "model_table_rows": model_rows,
            "model_stats": model_stats,

            # summary tables
            "summary_stats": summary_stats,

            # interactions
            "interactions": interactions,

            # continuous variables for correlation heatmap
            "continuous_vars": continuous_vars,
            
            # all numeric variables for summary table editing
            "all_numeric_vars": all_numeric_vars,

            # fitted model for dynamic plot generation
            "fitted_model": fitted_model,

            # regression type
            "regression_type": regression_type,
            
            # OLS diagnostics (for all regression types)
            "diagnostics": diagnostics_list,

            # backward-compat keys (no images now)
            "spotlight_path": None, "spotlight_rel": None,
        }
    
    @staticmethod
    def _run_multi_equation(df, equation_lines, analysis_type, outdir, options, schema_types=None, schema_orders=None):
        """
        Handle multiple equations (one per line) for regression.
        Each equation is fitted separately, and results are organized in a grid format.
        """
        try:
            # DIAGNOSTICS: Log multi-equation processing
            print(f"=== MULTI-EQUATION PROCESSING DIAGNOSTICS ===")
            print(f"Processing {len(equation_lines)} equations")
            
            # Parse each equation
            equations_data = []
            all_rhs_vars = set()  # Collect all RHS variables across equations
            dependent_vars = []  # Collect all LHS (DV) variables
            
            for eq_line in equation_lines:
                if '~' not in eq_line:
                    continue
                
                lhs, rhs = eq_line.split('~', 1)
                dv = lhs.strip()
                rhs_vars = [v.strip() for v in rhs.split('+') if v.strip()]
                
                print(f"  Equation: '{eq_line}'")
                print(f"    DV: {dv}")
                print(f"    RHS vars ({len(rhs_vars)}): {', '.join(rhs_vars)}")
                
                dependent_vars.append(dv)
                # Add all RHS vars - a variable can be DV in one equation and IV in another
                all_rhs_vars.update(rhs_vars)
            
            print(f"Total unique dependent variables: {len(dependent_vars)} ({', '.join(dependent_vars)})")
            print(f"Total unique RHS variables: {len(all_rhs_vars)} ({', '.join(sorted(all_rhs_vars))})")
            print(f"Note: Variables can be DV in one equation and IV in another")
            
            # Fit each equation separately
            equation_results = []
            for i, eq_line in enumerate(equation_lines):
                if '~' not in eq_line:
                    continue
                
                # For multi-equation regression, ensure all columns are included
                # Create a copy of options with all display flags enabled
                multi_eq_options = options.copy() if options else {}
                multi_eq_options['show_se'] = True  # Always show standard errors
                multi_eq_options['show_p'] = True   # Always show p-values
                multi_eq_options['show_ci'] = True # Always show confidence intervals
                multi_eq_options['show_t'] = True  # Always show t/z statistics
                multi_eq_options['show_r2'] = True  # Always include R² for model fit stats
                multi_eq_options['show_aic'] = True  # Always include AIC for model fit stats
                multi_eq_options['show_bic'] = True  # Always include BIC for model fit stats
                multi_eq_options['show_n'] = True  # Always include N for model fit stats
                
                # Fit this equation
                fit_result = RegressionModule._fit_models(df, eq_line, multi_eq_options, schema_types, schema_orders)
                
                # Unpack results
                if len(fit_result) == 5:
                    model_cols, model_rows, model_stats, fitted_model, regression_type = fit_result
                    diagnostics = None
                elif len(fit_result) == 6:
                    model_cols, model_rows, model_stats, fitted_model, regression_type, diagnostics = fit_result
                else:
                    model_cols, model_rows, model_stats, fitted_model, regression_type = fit_result[:5]
                    diagnostics = None
                
                # Extract DV from equation
                lhs, _ = eq_line.split('~', 1)
                dv = lhs.strip()
                
                # Store results for this equation
                equation_results.append({
                    'dependent_var': dv,
                    'formula': eq_line,
                    'model_cols': model_cols,
                    'model_rows': model_rows,
                    'model_stats': model_stats,
                    'fitted_model': fitted_model,
                    'regression_type': regression_type,
                    'diagnostics': diagnostics
                })
            
            # Organize results in grid format: rows = RHS vars, cols = DVs
            # Build a nested dict: {rhs_var: {dv: {coef, se, ci_low, ci_high, t, p, sig}}}
            grid_data = {}  # {rhs_var: {dv: {coef, se, ci_low, ci_high, t, p, sig}}}
            
            for eq_result in equation_results:
                dv = eq_result['dependent_var']
                rows = eq_result['model_rows']
                model_cols = eq_result['model_cols']
                
                print(f"  Processing equation for DV: {dv}")
                print(f"    Model cols: {model_cols}")
                print(f"    Number of rows: {len(rows)}")
                
                # Process each row to extract parameter info
                for row_idx, row in enumerate(rows):
                    print(f"    Row {row_idx}: {row}")
                    
                    # Find the term name (first column)
                    term = None
                    if model_cols and len(model_cols) > 0:
                        first_col = model_cols[0]
                        if first_col in row:
                            term = row[first_col]
                            print(f"      Found term from first column '{first_col}': {term}")
                    
                    if term is None:
                        # Try to find any key that looks like a term name
                        for key in row.keys():
                            if key not in ['Estimate', 'Coefficient', 'coef', 'Std. Error', 'Std Error', 'std_err', 
                                         't', 'z', 't value', 'z value', 'p', 'p-value', 'pvalue', 
                                         'CI_low', '2.5%', 'ci_low', 'CI_high', '97.5%', 'ci_high']:
                                term = key
                                print(f"      Found term from key '{key}': {term}")
                                break
                    
                    if term is None or term in ['Intercept', '(Intercept)', 'Intercept:']:
                        # Handle intercept separately if needed
                        term = 'Intercept'
                        print(f"      Using default term: {term}")
                    
                    # Clean up term name - remove any extra formatting
                    # Handle cases like "Intercept", "(Intercept)", "Intercept:", etc.
                    if term and term.strip():
                        term_clean = term.strip()
                        if term_clean.startswith('(') and term_clean.endswith(')'):
                            term_clean = term_clean[1:-1]
                        if term_clean.endswith(':'):
                            term_clean = term_clean[:-1]
                        if term_clean in ['Intercept', '(Intercept)']:
                            term_clean = 'Intercept'
                        term = term_clean
                    
                    # Extract parameter values
                    coef_raw = row.get('Estimate') or row.get('Coefficient') or row.get('coef')
                    se = row.get('Std. Error') or row.get('Std Error') or row.get('std_err')
                    t_stat = row.get('t / z') or row.get('t') or row.get('z') or row.get('t value') or row.get('z value')
                    p_val = row.get('p') or row.get('p-value') or row.get('pvalue')
                    ci_str = row.get('95% CI') or row.get('CI') or row.get('ci')
                    ci_low = row.get('CI_low') or row.get('2.5%') or row.get('ci_low')
                    ci_high = row.get('CI_high') or row.get('97.5%') or row.get('ci_high')
                    
                    # Parse coefficient - it may include significance stars (e.g., "1.667**")
                    coef = None
                    sig = ""
                    if coef_raw:
                        import re
                        # Extract numeric value and stars separately
                        # Pattern: optional minus, digits, decimal point, digits, optional stars
                        match = re.match(r'([-]?\d+\.?\d*)(\**)?', str(coef_raw))
                        if match:
                            coef = match.group(1)
                            sig = match.group(2) or ""
                        else:
                            # Fallback: try to extract just the number
                            coef = str(coef_raw).strip()
                    
                    # Parse CI string if provided (format: "[low, high]")
                    if ci_str and not ci_low and not ci_high:
                        import re
                        ci_match = re.match(r'\[([-]?\d+\.?\d*),\s*([-]?\d+\.?\d*)\]', str(ci_str))
                        if ci_match:
                            ci_low = ci_match.group(1)
                            ci_high = ci_match.group(2)
                    
                    # Convert string values to appropriate types
                    try:
                        if coef:
                            coef = float(coef)
                    except (ValueError, TypeError):
                        coef = None
                    
                    try:
                        if se:
                            se = float(se) if isinstance(se, str) else se
                    except (ValueError, TypeError):
                        se = None
                    
                    try:
                        if p_val:
                            p_val = float(p_val) if isinstance(p_val, str) else p_val
                    except (ValueError, TypeError):
                        p_val = None
                    
                    try:
                        if ci_low:
                            ci_low = float(ci_low) if isinstance(ci_low, str) else ci_low
                    except (ValueError, TypeError):
                        ci_low = None
                    
                    try:
                        if ci_high:
                            ci_high = float(ci_high) if isinstance(ci_high, str) else ci_high
                    except (ValueError, TypeError):
                        ci_high = None
                    
                    try:
                        if t_stat:
                            t_stat = float(t_stat) if isinstance(t_stat, str) else t_stat
                    except (ValueError, TypeError):
                        t_stat = None
                    
                    # If we don't have significance stars from parsing, calculate them from p_val
                    if not sig and p_val is not None:
                        sig = _stars(p_val)
                    
                    print(f"      Final term: {term}, coef: {coef}, se: {se}, p_val: {p_val}, sig: {sig}")
                    
                    # Store in grid (nested dict structure)
                    if term not in grid_data:
                        grid_data[term] = {}
                    grid_data[term][dv] = {
                        'coef': coef,
                        'se': se,
                        't_stat': t_stat,
                        'p_val': p_val,
                        'ci_low': ci_low,
                        'ci_high': ci_high,
                        'sig': sig
                    }
            
            # Get all unique RHS variables (terms) for rows
            # Use terms from grid_data (actual model results) as the source of truth
            # IMPORTANT: A variable can be DV in one equation and IV in another, so include ALL terms
            all_rhs_vars_list = []
            
            # First, add all terms from grid_data (these are the actual terms from model results)
            # Don't exclude DVs - they can be IVs in other equations
            for term in grid_data.keys():
                if term not in all_rhs_vars_list:
                    all_rhs_vars_list.append(term)
            
            # Then, add any RHS vars from original equations that aren't in grid_data yet
            # (This handles cases where a variable might be in the formula but not in results)
            # Don't exclude DVs - they can be IVs in other equations
            for rhs_var in sorted(all_rhs_vars):
                if rhs_var not in all_rhs_vars_list:
                    all_rhs_vars_list.append(rhs_var)
            
            # Sort the list, but keep Intercept first if it exists
            if 'Intercept' in all_rhs_vars_list:
                all_rhs_vars_list.remove('Intercept')
                all_rhs_vars_list.insert(0, 'Intercept')
            else:
                all_rhs_vars_list = sorted(all_rhs_vars_list)
            
            print(f"  Grid data keys (terms): {list(grid_data.keys())}")
            print(f"  Dependent vars: {dependent_vars}")
            print(f"  Final RHS vars list (can include DVs from other equations): {all_rhs_vars_list}")
            
            print(f"✓ Multi-equation processing complete")
            print(f"  Grid data entries: {len(grid_data)}")
            print(f"  RHS vars for grid rows: {len(all_rhs_vars_list)} ({', '.join(all_rhs_vars_list)})")
            print(f"  Dependent vars for grid cols: {len(dependent_vars)} ({', '.join(dependent_vars)})")
            print(f"=== END MULTI-EQUATION PROCESSING DIAGNOSTICS ===")
            
            # Generate summary statistics for all variables (RHS and LHS from all equations)
            all_vars = list(set(dependent_vars + all_rhs_vars_list))
            # Remove 'Intercept' from variables list for summary stats (it's not a real variable)
            all_vars = [v for v in all_vars if v != 'Intercept']
            
            # Create a combined formula string for summary stats generation
            # _generate_summary_stats expects a formula with ~, so we create a dummy formula
            # Use the first variable as DV and the rest as predictors (or just the first if only one)
            combined_formula = ''
            if all_vars:
                if len(all_vars) == 1:
                    # If only one variable, use it as both DV and predictor
                    combined_formula = f"{all_vars[0]} ~ {all_vars[0]}"
                else:
                    # Use first variable as DV, rest as predictors
                    combined_formula = f"{all_vars[0]} ~ {' + '.join(all_vars[1:])}"
                summary_stats = _generate_summary_stats(df, combined_formula, None)
            else:
                summary_stats = {}
            
            # Get continuous variables for correlation heatmap (all numeric variables from equations)
            if combined_formula:
                continuous_vars = _get_continuous_variables_from_formula(df, combined_formula)
                # If no continuous variables in equation, fall back to all continuous variables
                if len(continuous_vars) < 2:
                    continuous_vars = _get_continuous_variables(df)
            else:
                # If no formula, just get all continuous variables
                continuous_vars = _get_continuous_variables(df)
            
            # Calculate correlation matrix for continuous variables
            correlation_matrix = {}
            if len(continuous_vars) >= 2:
                try:
                    # Get numeric columns that exist in the dataframe
                    available_vars = [v for v in continuous_vars if v in df.columns and pd.api.types.is_numeric_dtype(df[v])]
                    if len(available_vars) >= 2:
                        corr_df = df[available_vars].corr()
                        # Convert to dictionary format for template
                        for i, var_row in enumerate(available_vars):
                            for j, var_col in enumerate(available_vars):
                                correlation_matrix[f"{var_row}_{var_col}"] = float(corr_df.loc[var_row, var_col])
                except Exception as e:
                    print(f"DEBUG: Error calculating correlation matrix: {e}")
                    correlation_matrix = {}
            
            # Get all numeric variables for summary table editing
            all_numeric_vars = _get_all_numeric_variables(df)
            
            return {
                'has_results': True,
                'is_multi_equation': True,
                'dependent_vars': dependent_vars,
                'rhs_vars': all_rhs_vars_list,
                'grid_data': grid_data,
                'equation_results': equation_results,  # Store full results for each equation
                'formula': '\n'.join(equation_lines),
                'regression_type': 'Multi-equation regression',
                'summary_stats': summary_stats,
                'continuous_vars': continuous_vars,
                'correlation_matrix': correlation_matrix,
                'all_numeric_vars': all_numeric_vars,
                'error': None
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'has_results': False,
                'is_multi_equation': True,
                'error': f'Error running multi-equation regression: {str(e)}'
            }
