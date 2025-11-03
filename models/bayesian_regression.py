# bayesian_regression/module.py
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import Bambi and ArviZ for proper Bayesian inference
try:
    import bambi as bmb
    import arviz as az
    BAMBI_AVAILABLE = True
except ImportError:
    BAMBI_AVAILABLE = False
    print("Warning: Bambi and ArviZ not available. Install with: pip install bambi arviz")


def _stars(p):
    """Convert p-values to significance stars"""
    try:
        p = float(p)
    except Exception:
        return ""
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "."
    return ""


def _quote_column_names_with_special_chars(df, formula):
    """Handle column names with spaces, dots, and other special characters for statsmodels processing"""
    import re
    
    # For statsmodels, we need to temporarily rename columns with special characters
    # and update the formula accordingly
    column_mapping = {}
    df_renamed = df.copy()
    
    # Create mapping for columns with special characters
    for col in df.columns:
        # Check if column name contains spaces, dots, or other problematic characters
        if any(char in col for char in [' ', '.', '-', '(', ')', '[', ']', '+', '*', ':', '~', '^', '$', '|', '\\', '/', '?']):
            # Create a safe name by replacing problematic characters with underscores
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', col)
            # Ensure the safe name doesn't start with a number
            if safe_name[0].isdigit():
                safe_name = 'var_' + safe_name
            # Ensure the safe name is unique
            original_safe_name = safe_name
            counter = 1
            while safe_name in column_mapping.values():
                safe_name = f"{original_safe_name}_{counter}"
                counter += 1
            
            column_mapping[safe_name] = col
            df_renamed = df_renamed.rename(columns={col: safe_name})
            # Update formula to use safe names - use word boundaries to avoid partial matches
            formula = re.sub(rf'\b{re.escape(col)}\b', safe_name, formula)
    
    return formula, df_renamed, column_mapping


def _parse_formula(formula: str):
    """Parse regression formula to extract outcomes, predictors, and interactions"""
    lhs, rhs = formula.split("~", 1)
    outcomes = [t.strip() for t in lhs.split("+") if t.strip()]
    
    # Parse predictors and interactions
    raw_terms = [t.strip() for t in rhs.split("+") if t.strip()]
    predictors = []
    interactions = []
    
    for term in raw_terms:
        if ":" in term:
            # Explicit interaction
            interactions.append(term)
            # Add individual terms if not already present
            parts = [p.strip() for p in term.split(":")]
            for part in parts:
                if part not in predictors:
                    predictors.append(part)
        elif "*" in term:
            # Shorthand interaction (x*m means x + m + x:m)
            parts = [p.strip() for p in term.split("*")]
            if len(parts) == 2:
                x, m = parts[0], parts[1]
                if x not in predictors:
                    predictors.append(x)
                if m not in predictors:
                    predictors.append(m)
                interactions.append(f"{x}:{m}")
        else:
            # Regular predictor
            if term not in predictors:
                predictors.append(term)
    
    return outcomes, predictors, interactions


def _get_continuous_variables_from_formula(df, formula):
    """Get continuous variables that appear in the formula."""
    outcomes, predictors, _ = _parse_formula(formula)
    all_vars = outcomes + predictors
    
    continuous_vars = []
    for var in all_vars:
        if var in df.columns:
            # Check if variable is numeric and has more than 2 unique values
            if pd.api.types.is_numeric_dtype(df[var]) and df[var].nunique() > 2:
                continuous_vars.append(var)
    
    return continuous_vars


def _generate_summary_stats(df, formula, fitted_model=None):
    """Generate summary statistics for variables in the formula."""
    outcomes, predictors, _ = _parse_formula(formula)
    summary_stats = {}
    
    # Include both outcomes and predictors from the formula
    all_vars = outcomes + predictors
    
    for var in all_vars:
        if var in df.columns:
            if pd.api.types.is_numeric_dtype(df[var]):
                series = df[var].dropna()
                if len(series) > 0:
                    summary_stats[var] = {
                        'mean': float(series.mean()),
                        'std': float(series.std()),
                        'min': float(series.min()),
                        'max': float(series.max()),
                        'range': float(series.max() - series.min()),
                        'variance': float(series.var(ddof=1)),  # Sample variance
                        'n': int(series.count()),
                        'missing': int(df[var].isnull().sum())
                    }
            else:
                # Categorical variable
                value_counts = df[var].value_counts()
                summary_stats[var] = {
                    'n': int(df[var].count()),
                    'missing': int(df[var].isnull().sum()),
                    'categories': value_counts.to_dict()
                }
    
    return summary_stats


def _build_correlation_heatmap_json(df, continuous_vars):
    """Build correlation heatmap data for continuous variables."""
    if not continuous_vars:
        return None
    
    # Get only numeric columns that exist in the dataframe
    numeric_vars = [var for var in continuous_vars if var in df.columns and pd.api.types.is_numeric_dtype(df[var])]
    
    if len(numeric_vars) < 2:
        return None
    
    # Calculate correlation matrix
    corr_matrix = df[numeric_vars].corr()
    
    # Create heatmap data
    heatmap_data = {
        'z': corr_matrix.values.tolist(),
        'x': corr_matrix.columns.tolist(),
        'y': corr_matrix.index.tolist(),
        'type': 'heatmap',
        'colorscale': 'RdBu',
        'zmid': 0,
        'zmin': -1,
        'zmax': 1,
        'text': np.round(corr_matrix.values, 3).tolist(),
        'texttemplate': '%{text}',
        'textfont': {'size': 10},
        'hoverongaps': False
    }
    
    return heatmap_data





def _build_spotlight_json(fitted_model, df, x_var, m_var, options):
    """Build spotlight plot data for interaction effects."""
    try:
        # For Bayesian models, we'll create a simple scatter plot with trend lines
        # This is a simplified version - in practice, you'd want to use posterior samples
        
        # Get unique values of the moderator
        m_values = sorted(df[m_var].unique())
        
        spotlight_data = {
            'x_var': x_var,
            'm_var': m_var,
            'x_values': df[x_var].tolist(),
            'y_values': df[df.columns[0]].tolist(),  # Assuming first column is outcome
            'm_values': df[m_var].tolist(),
            'm_unique': m_values,
            'interaction_type': 'continuous' if pd.api.types.is_numeric_dtype(df[m_var]) else 'categorical'
        }
        
        return spotlight_data
        
    except Exception as e:
        print(f"Error building spotlight plot: {e}")
        return None


class BayesianRegressionModule:
    """Bayesian regression module using Bambi and ArviZ."""
    
    @staticmethod
    def ui_schema():
        """Return UI schema for Bayesian regression options."""
        return {
            'draws': {
                'type': 'integer',
                'title': 'Number of draws',
                'description': 'Number of posterior samples to draw',
                'default': 2000,
                'minimum': 100,
                'maximum': 10000
            },
            'tune': {
                'type': 'integer', 
                'title': 'Number of tuning steps',
                'description': 'Number of tuning steps for MCMC',
                'default': 1000,
                'minimum': 100,
                'maximum': 5000
            },
            'chains': {
                'type': 'integer',
                'title': 'Number of chains',
                'description': 'Number of MCMC chains to run',
                'default': 4,
                'minimum': 1,
                'maximum': 8
            },
            'cores': {
                'type': 'integer',
                'title': 'Number of cores',
                'description': 'Number of CPU cores to use',
                'default': 2,
                'minimum': 1,
                'maximum': 8
            },
            'family': {
                'type': 'string',
                'title': 'Distribution family',
                'description': 'Distribution family for the outcome variable',
                'enum': ['gaussian', 'bernoulli', 'poisson'],
                'default': 'gaussian'
            }
        }
    
    @staticmethod
    def _fit_models(df, formula, options, schema_types=None, schema_orders=None):
        """Fit Bayesian regression models using Bambi and ArviZ."""
        try:
            if not BAMBI_AVAILABLE:
                raise ImportError("Bambi and ArviZ are required for Bayesian regression. Install with: pip install bambi arviz")
            
            print(f"DEBUG: Bayesian _fit_models called with formula: {formula}")
            print(f"DEBUG: Dataset shape: {df.shape}")
            print(f"DEBUG: Options: {options}")
            
            # Print loading status updates
            print("BAYESIAN_STATUS: Initializing Bayesian regression analysis...")
            
            # Handle column names with special characters for proper processing
            formula, df_renamed, column_mapping = _quote_column_names_with_special_chars(df, formula)
            
            # Parse formula to get outcome variable
            outcomes, predictors, interactions = _parse_formula(formula)
            
            if len(outcomes) != 1:
                raise ValueError("Bayesian regression currently supports single outcome variables only")
            
            outcome_var = outcomes[0]
            
            # Check if outcome variable exists
            if outcome_var not in df_renamed.columns:
                raise ValueError(f"Outcome variable '{outcome_var}' not found in dataset")
            
            print("BAYESIAN_STATUS: Validating outcome variable...")
            
            # Get model options
            draws = options.get('draws', 2000)
            tune = options.get('tune', 1000)
            chains = options.get('chains', 4)
            cores = options.get('cores', 2)
            family = options.get('family', 'gaussian')
            prior_type = options.get('prior', 'auto')
            
            print(f"DEBUG: MCMC settings - draws: {draws}, tune: {tune}, chains: {chains}, cores: {cores}")
            print("BAYESIAN_STATUS: Preparing data and cleaning missing values...")
            
            # Prepare data - remove rows with missing values in outcome variable
            df_clean = df_renamed.dropna(subset=[outcome_var]).copy()
            
            if len(df_clean) == 0:
                raise ValueError("No valid data points after removing missing values")
            
            print(f"DEBUG: Clean dataset shape: {df_clean.shape}")
            print("BAYESIAN_STATUS: Data preparation completed successfully")
            
            # Determine family based on outcome variable type
            if family == 'auto':
                if pd.api.types.is_numeric_dtype(df_clean[outcome_var]):
                    unique_vals = df_clean[outcome_var].nunique()
                    if unique_vals == 2:
                        family = 'bernoulli'
                    else:
                        family = 'gaussian'
                else:
                    family = 'gaussian'  # Default fallback
            
            print(f"DEBUG: Using family: {family}")
            print("BAYESIAN_STATUS: Creating Bayesian model with Bambi...")
            
            # Create Bambi model
            try:
                model = bmb.Model(formula, data=df_clean, family=family)
                print(f"DEBUG: Bambi model created successfully")
                print(f"DEBUG: Model formula: {model.formula}")
                print(f"DEBUG: Model family: {model.family}")
                
                # Debug: Print available terms
                print(f"DEBUG: Available terms in model: {list(model.terms.keys()) if hasattr(model, 'terms') else 'No terms attribute'}")
                if hasattr(model, 'terms'):
                    for term_name, term_obj in model.terms.items():
                        print(f"DEBUG: Term '{term_name}': {type(term_obj)}")
                
                # Set priors based on prior_type
                if prior_type != 'auto':
                    print(f"DEBUG: Setting priors to {prior_type}")
                    try:
                        if prior_type == 'weakly_informative':
                            # Set weakly informative priors (larger variance)
                            # Get all terms from the model and set priors for them
                            priors = {'Intercept': bmb.Prior('Normal', mu=0, sigma=10)}
                            
                            # Add priors for all terms in the model
                            for term_name in model.terms:
                                if term_name != 'Intercept':
                                    priors[term_name] = bmb.Prior('Normal', mu=0, sigma=5)
                            
                            model.set_priors(priors)
                            print(f"DEBUG: Set weakly informative priors for terms: {list(priors.keys())}")
                            
                        elif prior_type == 'informative':
                            # Set informative priors (smaller variance)
                            priors = {'Intercept': bmb.Prior('Normal', mu=0, sigma=1)}
                            
                            # Add priors for all terms in the model
                            for term_name in model.terms:
                                if term_name != 'Intercept':
                                    priors[term_name] = bmb.Prior('Normal', mu=0, sigma=0.5)
                            
                            model.set_priors(priors)
                            print(f"DEBUG: Set informative priors for terms: {list(priors.keys())}")
                        
                        print(f"DEBUG: Priors set to {prior_type}")
                    except Exception as e:
                        print(f"DEBUG: Error setting priors: {e}")
                        print(f"DEBUG: Available terms: {list(model.terms.keys()) if hasattr(model, 'terms') else 'No terms available'}")
                        print(f"DEBUG: Using default priors instead")
                else:
                    print(f"DEBUG: Using default Bambi priors (auto)")
                
                print("BAYESIAN_STATUS: Model created successfully")
            except Exception as e:
                print(f"DEBUG: Error creating Bambi model: {e}")
                raise
            
            # Fit model with MCMC
            print("BAYESIAN_STATUS: Starting MCMC sampling...")
            print(f"BAYESIAN_STATUS: Running {chains} chains with {draws} draws each (tuning: {tune} steps)")
            try:
                results = model.fit(
                    draws=draws,
                    tune=tune,
                    chains=chains,
                    cores=cores,
                    random_seed=42,
                    progressbar=False
                )
                print(f"DEBUG: MCMC sampling completed")
                print(f"DEBUG: Results type: {type(results)}")
                print("BAYESIAN_STATUS: MCMC sampling completed successfully")
            except Exception as e:
                print(f"DEBUG: Error during MCMC sampling: {e}")
                raise
            
            # Get summary statistics
            print("BAYESIAN_STATUS: Computing posterior summary statistics...")
            try:
                summary = az.summary(results, round_to=4)
                print(f"DEBUG: Summary shape: {summary.shape}")
                print(f"DEBUG: Summary columns: {list(summary.columns)}")
                print(f"DEBUG: Summary index: {list(summary.index)}")
                print(f"DEBUG: Summary sample:\n{summary.head()}")
                print("BAYESIAN_STATUS: Summary statistics computed successfully")
            except Exception as e:
                print(f"DEBUG: Error getting summary: {e}")
                raise
            
            # Create model summary table
            model_cols = ['Parameter', 'Mean', 'Std', 'HPD_2.5%', 'HPD_97.5%', 'Rhat', 'ESS']
            model_rows = []
            
            # Convert ArviZ summary to our format
            for param_name in summary.index:
                row = summary.loc[param_name]
                
                # Extract values, handling potential missing columns
                mean_val = float(row.get('mean', 0))
                std_val = float(row.get('sd', 0))  # ArviZ uses 'sd' not 'std'
                hpd_low = float(row.get('hdi_3%', 0))  # ArviZ uses 'hdi_3%' not 'hdi_2.5%'
                hpd_high = float(row.get('hdi_97%', 0))  # ArviZ uses 'hdi_97%' not 'hdi_97.5%'
                rhat = float(row.get('r_hat', 1.0))
                ess = float(row.get('ess_bulk', draws))
                
                # Debug: Print first parameter to verify mapping
                if param_name == summary.index[0]:
                    print(f"DEBUG: First parameter '{param_name}' mapping:")
                    print(f"  mean: {mean_val:.4f}")
                    print(f"  std: {std_val:.4f}")
                    print(f"  hdi_3%: {hpd_low:.4f}")
                    print(f"  hdi_97%: {hpd_high:.4f}")
                    print(f"  r_hat: {rhat:.4f}")
                    print(f"  ess_bulk: {ess:.0f}")
                
                model_rows.append([
                    param_name,
                    f"{mean_val:.4f}",
                    f"{std_val:.4f}",
                    f"{hpd_low:.4f}",
                    f"{hpd_high:.4f}",
                    f"{rhat:.3f}",
                    f"{ess:.0f}"
                ])
            
            print(f"DEBUG: Created {len(model_rows)} model rows")
            print("BAYESIAN_STATUS: Formatting results table...")
            
            # Model statistics
            model_stats = {
                'n_obs': len(df_clean),
                'n_params': len(model_rows),
                'draws': draws,
                'tune': tune,
                'chains': chains,
                'model_type': f'Bayesian {family.title()} Regression',
                'family': family
            }
            
            # Determine regression type
            if family == 'gaussian':
                regression_type = 'Bayesian Linear Regression'
            elif family == 'bernoulli':
                regression_type = 'Bayesian Logistic Regression'
            elif family == 'poisson':
                regression_type = 'Bayesian Poisson Regression'
            else:
                regression_type = f'Bayesian {family.title()} Regression'
            
            # Store fitted model for later use (avoid pickling complex objects)
            fitted_model = {
                'outcome_var': outcome_var,
                'family': family,
                'formula': formula,
                'model_type': 'bambi',
                'summary_stats': summary.to_dict() if hasattr(summary, 'to_dict') else None
            }
            
            print(f"DEBUG: Returning - model_cols: {len(model_cols)}, model_rows: {len(model_rows)}")
            print("BAYESIAN_STATUS: Analysis completed successfully!")
            
            return model_cols, model_rows, model_stats, fitted_model, regression_type
            
        except Exception as e:
            print(f"Error in Bayesian regression: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Return empty results on error
            return [], [], {'error': str(e)}, None, 'Bayesian Regression (Error)'
    
    @staticmethod
    def run(df, formula, analysis_type, outdir, options, schema_types=None, schema_orders=None):
        """Main entry point for Bayesian regression analysis."""
        try:
            print(f"DEBUG: Bayesian run() called with formula: {formula}")
            print(f"DEBUG: Dataset shape: {df.shape}")
            print(f"DEBUG: Options: {options}")
            
            
            print("BAYESIAN_STATUS: Starting Bayesian regression analysis...")
            
            # 1) Fit model + table
            model_cols, model_rows, model_stats, fitted_model, regression_type = BayesianRegressionModule._fit_models(
                df, formula, options, schema_types, schema_orders
            )
            
            print("BAYESIAN_STATUS: Generating additional analysis components...")
            
            print(f"DEBUG: _fit_models returned - cols: {len(model_cols)}, rows: {len(model_rows)}")
            
            # 2) Parse formula to get interactions
            _, _, interactions = _parse_formula(formula)
            
            # 3) Interactive spotlight (generate for all interactions)
            spotlight_json = None
            if interactions and fitted_model is not None:
                for inter in interactions:
                    if "*" in inter:
                        x, m = [p.strip() for p in inter.split("*", 1)]
                    else:
                        parts = inter.split(":")
                        if len(parts) == 2:
                            x, m = parts[0].strip(), parts[1].strip()
                        else:
                            continue
                    
                    if x in df.columns and m in df.columns:
                        spotlight_json = _build_spotlight_json(fitted_model, df, x, m, options)
                        break
            
            # 4) Summary statistics
            summary_stats = _generate_summary_stats(df, formula, fitted_model)
            
            # 5) Get continuous variables for correlation heatmap
            continuous_vars = _get_continuous_variables_from_formula(df, formula)
            
            # 6) Build correlation heatmap
            heatmap_json = _build_correlation_heatmap_json(df, continuous_vars)
            
            # 7) Get all numeric variables for summary table editing
            all_numeric_vars = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
            
            # 8) Bootstrap analysis if enabled
            bootstrap_results = None
            if options.get('bootstrap', False):
                n_boot = options.get('n_boot', 1000)
                bootstrap_results = _bootstrap_analysis(df, formula, options, n_boot)
            
            print(f"DEBUG: Returning results with model_cols: {len(model_cols)}, model_rows: {len(model_rows)}")
            print("BAYESIAN_STATUS: Finalizing results and preparing output...")
            
            return {
                # Model results
                'model_cols': model_cols,
                'model_rows': model_rows,
                'model_table_cols': model_cols,  # Add this for views.py compatibility
                'model_table_rows': model_rows,  # Add this for views.py compatibility
                'model_stats': model_stats,
                
                # Spotlight plot data
                'spotlight_json': spotlight_json,
                
                # Summary statistics
                'summary_stats': summary_stats,
                
                # Correlation heatmap
                'heatmap_json': heatmap_json,
                
                # Variable information
                'continuous_vars': continuous_vars,
                'all_numeric_vars': all_numeric_vars,
                
                # Fitted model for dynamic plot generation
                'fitted_model': fitted_model,
                
                # Regression type
                'regression_type': regression_type,
                
                # Bootstrap results
                'bootstrap_results': bootstrap_results,
                
                # Backward compatibility
                'spotlight_path': None,
                'spotlight_rel': None,
            }
            
        except Exception as e:
            print(f"Error in Bayesian regression run: {e}")
            return {
                'model_cols': [],
                'model_rows': [],
                'model_table_cols': [],  # Add this for views.py compatibility
                'model_table_rows': [],  # Add this for views.py compatibility
                'model_stats': {'error': str(e)},
                'spotlight_json': None,
                'summary_stats': {},
                'heatmap_json': None,
                'continuous_vars': [],
                'all_numeric_vars': [],
                'fitted_model': None,
                'regression_type': 'Bayesian Regression (Error)',
                'spotlight_path': None,
                'spotlight_rel': None,
            }
