"""
Service for generating Impulse Response Functions (IRF) for VARX/VARMAX models.

This service encapsulates IRF generation logic to keep views thin.
"""
import pickle
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import json
from typing import Dict, Any, List, Optional, Tuple
from engine.models import AnalysisSession
from data_prep.file_handling import _read_dataset_file


class IRFService:
    """Service for IRF generation."""
    
    @staticmethod
    def validate_session_for_irf(session: AnalysisSession) -> Tuple[bool, Optional[str]]:
        """
        Validate that session is suitable for IRF generation.
        
        Args:
            session: AnalysisSession object
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if session.module not in ['varx', 'varmax']:
            return False, 'This endpoint is only for VARX/VARMAX sessions'
        
        if not session.dataset:
            return False, 'Dataset not found for this session'
        
        return True, None
    
    @staticmethod
    def _load_varx_model_results(session: AnalysisSession, df: pd.DataFrame):
        """
        Load VARX model results from session or regenerate if needed.
        
        Args:
            session: AnalysisSession object
            df: DataFrame with the dataset
            
        Returns:
            Tuple of (model_results, endog_data, dependent_vars) or (None, None, None) on error
        """
        # Try to load from fitted_model field
        if hasattr(session, 'fitted_model') and session.fitted_model:
            try:
                fitted_data = pickle.loads(session.fitted_model)
                if isinstance(fitted_data, dict):
                    model_results = fitted_data.get('model_results')
                    endog_data = fitted_data.get('endog_data')
                    dependent_vars = fitted_data.get('dependent_vars', [])
                    if model_results is not None and endog_data is not None:
                        print("Successfully loaded VARX model from session")
                        return model_results, endog_data, dependent_vars
            except Exception as e:
                print(f"Failed to load stored VARX model: {e}")
        
        # If not available, re-run analysis
        return IRFService._rerun_varx_analysis(session, df)
    
    @staticmethod
    def _rerun_varx_analysis(session: AnalysisSession, df: pd.DataFrame):
        """Re-run VARX analysis to get model results."""
        print("VARX model results not found in session, re-running analysis...")
        try:
            from engine.modules import get_module
            from django.conf import settings
            
            module = get_module(session.module)
            if not module:
                return None, None, None
            
            results = module.run(
                df, 
                session.formula, 
                session.analysis_type, 
                settings.MEDIA_ROOT, 
                session.options or {}
            )
            
            if not results:
                return None, None, None
            
            model_results = results.get('model_results')
            endog_data = results.get('endog_data')
            dependent_vars = results.get('dependent_vars', [])
            
            # Try to store for future use
            if model_results is not None and endog_data is not None:
                IRFService._store_model_results(session, model_results, endog_data, dependent_vars)
            
            return model_results, endog_data, dependent_vars
            
        except Exception as e:
            print(f"ERROR: Failed to re-run VARX analysis: {e}")
            return None, None, None
    
    @staticmethod
    def _store_model_results(session: AnalysisSession, model_results, endog_data, dependent_vars):
        """Store model results in session for future use."""
        try:
            fitted_data = {
                'model_results': model_results,
                'endog_data': endog_data,
                'dependent_vars': dependent_vars
            }
            session.fitted_model = pickle.dumps(fitted_data)
            session.save()
            print("Stored VARX model results for future use")
        except Exception as e:
            print(f"Note: Could not store VARX model: {e}")
    
    @staticmethod
    def generate_irf_plot(session: AnalysisSession, periods: int, shock_var: Optional[str], 
                         response_vars: List[str], shock_type: str = 'orthogonal', 
                         show_ci: bool = True) -> Dict[str, Any]:
        """
        Generate IRF plot for VARX analysis using simple prediction-based approach.
        
        Args:
            session: AnalysisSession object
            periods: Number of periods for IRF
            shock_var: Variable to shock (None for all)
            response_vars: Variables to measure response (empty for all)
            shock_type: Type of shock ('orthogonal' or 'structural')
            show_ci: Whether to show confidence intervals
            
        Returns:
            Result dictionary with plot data or error
        """
        try:
            # Load dataset and model
            user_id = session.dataset.user.id if session.dataset.user else None
            df, column_types, schema_orders = _read_dataset_file(session.dataset.file_path, user_id=user_id)
            model_results, endog_data, dependent_vars = IRFService._load_varx_model_results(session, df)
            
            if model_results is None or endog_data is None:
                return {
                    'success': False,
                    'error': 'Could not load VARX model results. Please re-run the analysis.'
                }
            
            # Get variable names and indices
            var_names = list(endog_data.columns) if hasattr(endog_data, 'columns') else dependent_vars
            shock_indices, response_indices = IRFService._get_shock_response_indices(
                var_names, shock_var, response_vars
            )
            
            # Generate IRF DataFrame
            irf_df = IRFService._generate_irf_dataframe(
                model_results, endog_data, var_names, periods, 
                shock_indices, response_indices, show_ci
            )
            
            if irf_df is None or irf_df.empty:
                return {
                    'success': False,
                    'error': 'Failed to generate IRF data'
                }
            
            # Generate plot from DataFrame
            plot_data = IRFService._create_plot_from_dataframe(irf_df, show_ci)
            
            return {
                'success': True,
                'plot_data': plot_data
            }
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"IRF ERROR: {error_msg}")
            print(traceback.format_exc())
            
            return {
                'success': False,
                'error': f'Error generating IRF plot: {error_msg}'
            }
    
    @staticmethod
    def _get_shock_response_indices(var_names: List[str], shock_var: Optional[str], 
                                    response_vars: List[str]) -> Tuple[List[int], List[int]]:
        """Get indices for shock and response variables."""
        if shock_var:
            shock_indices = [var_names.index(shock_var)]
        else:
            shock_indices = list(range(len(var_names)))
        
        if response_vars:
            response_indices = [var_names.index(v) for v in response_vars if v in var_names]
        else:
            response_indices = list(range(len(var_names)))
        
        return shock_indices, response_indices
    
    @staticmethod
    def _generate_irf_dataframe(model_results, endog_data: pd.DataFrame, var_names: List[str],
                                periods: int, shock_indices: List[int], response_indices: List[int],
                                show_ci: bool) -> Optional[pd.DataFrame]:
        """
        Generate IRF DataFrame with columns: shock, response, prediction, lower_ci, upper_ci.
        
        Args:
            model_results: Fitted VARX model results
            endog_data: Endogenous data used for fitting
            var_names: List of variable names
            periods: Number of periods
            shock_indices: Indices of variables to shock
            response_indices: Indices of variables to measure response
            show_ci: Whether to compute confidence intervals
            
        Returns:
            DataFrame with IRF data or None on error
        """
        try:
            rows = []
            baseline = endog_data.mean().values
            
            for shock_idx in shock_indices:
                shock_name = var_names[shock_idx]
                
                for resp_idx in response_indices:
                    resp_name = var_names[resp_idx]
                    
                    # Generate IRF by applying shock and predicting forward
                    predictions, lower_ci, upper_ci = IRFService._compute_irf_predictions(
                        model_results, endog_data, baseline, shock_idx, resp_idx, periods, show_ci
                    )
                    
                    # Create rows for each period
                    rows.extend(IRFService._create_irf_rows(
                        shock_name, resp_name, periods, predictions, lower_ci, upper_ci, show_ci
                    ))
            
            return pd.DataFrame(rows)
            
        except Exception as e:
            import traceback
            print(f"Error generating IRF DataFrame: {e}")
            print(traceback.format_exc())
            return None
    
    @staticmethod
    def _create_irf_rows(shock_name: str, resp_name: str, periods: int, 
                        predictions: List[float], lower_ci: Optional[List[float]], 
                        upper_ci: Optional[List[float]], show_ci: bool) -> List[Dict]:
        """Create list of row dictionaries for IRF DataFrame."""
        rows = []
        for period in range(periods):
            pred_val = float(predictions[period]) if period < len(predictions) else 0.0
            lower_val = (float(lower_ci[period]) if show_ci and lower_ci is not None 
                        and period < len(lower_ci) else None)
            upper_val = (float(upper_ci[period]) if show_ci and upper_ci is not None 
                        and period < len(upper_ci) else None)
            
            rows.append({
                'shock': shock_name,
                'response': resp_name,
                'period': period,
                'prediction': pred_val,
                'lower_ci': lower_val,
                'upper_ci': upper_val
            })
        return rows
    
    @staticmethod
    def _compute_irf_predictions(model_results, endog_data: pd.DataFrame, baseline: np.ndarray,
                                 shock_idx: int, resp_idx: int, periods: int, show_ci: bool):
        """
        Compute IRF predictions by applying shock and forecasting forward.
        
        Args:
            model_results: Fitted VARX model results
            endog_data: Endogenous data
            baseline: Baseline values for all variables
            shock_idx: Index of variable to shock
            resp_idx: Index of variable to measure response
            periods: Number of periods to forecast
            show_ci: Whether to compute confidence intervals
            
        Returns:
            Tuple of (predictions, lower_ci, upper_ci)
        """
        try:
            # Get IRF predictions
            if show_ci:
                predictions, lower_ci, upper_ci = IRFService._get_irf_with_ci(
                    model_results, resp_idx, shock_idx, periods
                )
            else:
                predictions = IRFService._get_irf_without_ci(
                    model_results, resp_idx, shock_idx, periods
                )
                lower_ci, upper_ci = None, None
            
            # If CIs weren't computed, try to get them from irf_result
            if show_ci and (lower_ci is None or upper_ci is None):
                irf_result = model_results.irf(periods)
                lower_ci, upper_ci = IRFService._compute_ci_from_irf_result(
                    irf_result, predictions, resp_idx, shock_idx, periods
                )
            
            return predictions, lower_ci, upper_ci
            
        except Exception as e:
            import traceback
            print(f"Error computing IRF predictions: {e}")
            print(traceback.format_exc())
            return [0.0] * periods, None, None
    
    @staticmethod
    def _get_irf_with_ci(model_results, resp_idx: int, shock_idx: int, periods: int):
        """Get IRF predictions with confidence intervals using irf_resim."""
        try:
            irf_resim_result = model_results.irf_resim(orth=True, repl=200, steps=periods, seed=None)
            
            if isinstance(irf_resim_result, np.ndarray) and irf_resim_result.ndim == 4:
                # Shape: (replications, periods, n_vars, n_vars)
                irf_replications = irf_resim_result[:, :, resp_idx, shock_idx]
                
                # Mean across replications for predictions
                predictions = [float(np.mean(irf_replications[:, h])) for h in range(periods)]
                
                # Compute percentiles for CIs
                lower_ci, upper_ci = IRFService._compute_percentile_cis(irf_replications, periods)
                
                print(f"DEBUG CI COMPUTE: Using irf_resim with {irf_replications.shape[0]} replications")
                return predictions, lower_ci, upper_ci
            else:
                raise ValueError("irf_resim returned unexpected format")
                
        except Exception as e:
            print(f"DEBUG CI COMPUTE: irf_resim failed: {e}, falling back")
            raise
    
    @staticmethod
    def _compute_percentile_cis(irf_replications: np.ndarray, periods: int) -> Tuple[List[float], List[float]]:
        """Compute confidence intervals from replications using percentiles."""
        lower_ci = []
        upper_ci = []
        for h in range(periods):
            period_values = irf_replications[:, h]
            lower_val = float(np.percentile(period_values, 2.5))
            upper_val = float(np.percentile(period_values, 97.5))
            lower_ci.append(lower_val)
            upper_ci.append(upper_val)
        return lower_ci, upper_ci
    
    @staticmethod
    def _get_irf_without_ci(model_results, resp_idx: int, shock_idx: int, periods: int) -> List[float]:
        """Get IRF predictions without confidence intervals."""
        try:
            irf_result = model_results.irf(periods)
            if hasattr(irf_result, 'irfs'):
                irf_array = irf_result.irfs
                return [float(irf_array[h, resp_idx, shock_idx]) for h in range(periods)]
            return [0.0] * periods
        except Exception as e:
            print(f"DEBUG IRF: Error getting IRF: {e}")
            return [0.0] * periods
    
    @staticmethod
    def _compute_ci_from_irf_result(irf_result, predictions: List[float], 
                                   resp_idx: int, shock_idx: int, periods: int):
        """Compute confidence intervals from irf_result object."""
        try:
            # Try errband_mc first
            if hasattr(irf_result, 'errband_mc'):
                errband = irf_result.errband_mc
                if errband is not None and errband.ndim == 4:
                    lower_ci = [float(errband[0, h, resp_idx, shock_idx]) for h in range(periods)]
                    upper_ci = [float(errband[1, h, resp_idx, shock_idx]) for h in range(periods)]
                    print(f"DEBUG CI COMPUTE: Using errband_mc from irf_result")
                    return lower_ci, upper_ci
            
            # Try stderr
            if hasattr(irf_result, 'stderr'):
                stderr_array = irf_result.stderr
                if stderr_array is not None and stderr_array.ndim == 3:
                    lower_ci = [float(predictions[h] - 1.96 * stderr_array[h, resp_idx, shock_idx]) 
                               for h in range(periods)]
                    upper_ci = [float(predictions[h] + 1.96 * stderr_array[h, resp_idx, shock_idx]) 
                               for h in range(periods)]
                    print(f"DEBUG CI COMPUTE: Using stderr from irf_result")
                    return lower_ci, upper_ci
            
            # Fallback
            raise ValueError("irf_result has no CI attributes")
            
        except Exception as e:
            print(f"DEBUG CI COMPUTE: Could not get CIs from irf_result: {e}")
            return IRFService._compute_ci_fallback(predictions)
    
    @staticmethod
    def _compute_ci_fallback(predictions: List[float]) -> Tuple[List[float], List[float]]:
        """Fallback CI computation using standard error approximation."""
        se_base = (np.std(predictions) if len(predictions) > 1 and np.std(predictions) > 0 
                  else (abs(max(predictions, key=abs)) * 0.15 if predictions else 0.1))
        lower_ci = [float(p - 1.96 * se_base) for p in predictions]
        upper_ci = [float(p + 1.96 * se_base) for p in predictions]
        print(f"DEBUG CI COMPUTE: Using fallback SE approximation: se_base={se_base}")
        return lower_ci, upper_ci
    
    @staticmethod
    def _create_plot_from_dataframe(irf_df: pd.DataFrame, show_ci: bool) -> Dict[str, Any]:
        """
        Create Plotly plot from IRF DataFrame.
        
        Args:
            irf_df: DataFrame with columns: shock, response, period, prediction, lower_ci, upper_ci
            show_ci: Whether to show confidence intervals
            
        Returns:
            Dictionary with Plotly data and layout (JSON-serializable)
        """
        traces = []
        
        # Group by shock and response
        for (shock, response), group in irf_df.groupby(['shock', 'response']):
            periods = group['period'].values
            predictions = group['prediction'].values
            
            # Add CI traces if requested
            if show_ci:
                ci_traces = IRFService._create_ci_traces(group, shock, response)
                traces.extend(ci_traces)
            
            # Add main IRF line
            trace = IRFService._create_irf_trace(periods, predictions, shock, response)
            traces.append(trace)
        
        # Create figure and convert to JSON
        fig = IRFService._create_figure(traces)
        plot_json = pio.to_json(fig)
        return json.loads(plot_json)
    
    @staticmethod
    def _create_ci_traces(group: pd.DataFrame, shock: str, response: str) -> List[go.Scatter]:
        """Create confidence interval traces for plotting."""
        if 'lower_ci' not in group.columns or 'upper_ci' not in group.columns:
            return []
        
        lower_ci = group['lower_ci'].values
        upper_ci = group['upper_ci'].values
        periods = group['period'].values
        
        # Filter out None values
        valid_mask = ~(pd.isna(lower_ci) | pd.isna(upper_ci))
        if not valid_mask.any():
            return []
        
        valid_periods = periods[valid_mask]
        valid_lower = lower_ci[valid_mask]
        valid_upper = upper_ci[valid_mask]
        
        # Create upper and lower traces for filled area
        ci_upper_trace = go.Scatter(
            x=valid_periods,
            y=valid_upper,
            mode='lines',
            name=f'{response} | {shock} (95% CI)',
            line=dict(width=0, color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip'
        )
        
        ci_lower_trace = go.Scatter(
            x=valid_periods,
            y=valid_lower,
            mode='lines',
            name=f'{response} | {shock} (95% CI)',
            fill='tonexty',
            fillcolor='rgba(200, 200, 200, 0.5)',
            line=dict(width=0, color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip'
        )
        
        return [ci_upper_trace, ci_lower_trace]
    
    @staticmethod
    def _create_irf_trace(periods: np.ndarray, predictions: np.ndarray, 
                         shock: str, response: str) -> go.Scatter:
        """Create main IRF trace."""
        return go.Scatter(
            x=periods,
            y=predictions,
            mode='lines+markers',
            name=f'{response} | {shock}',
            line=dict(width=3, color='#1A85FF'),
            marker=dict(size=4, color='#1A85FF')
        )
    
    @staticmethod
    def _create_figure(traces: List[go.Scatter]) -> go.Figure:
        """Create Plotly figure with traces."""
        fig = go.Figure(data=traces)
        fig.update_layout(
            title='Impulse Response Functions',
            xaxis_title='Period',
            yaxis_title='Response',
            hovermode='closest',
            showlegend=True,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='lightgray', gridwidth=1),
            yaxis=dict(showgrid=True, gridcolor='lightgray', gridwidth=1)
        )
        return fig
    
    @staticmethod
    def generate_irf_data(session: AnalysisSession, periods: int, shock_var: Optional[str], 
                         response_vars: List[str]) -> Dict[str, Any]:
        """
        Generate IRF data (not plot) for VARX analysis.
        
        Args:
            session: AnalysisSession object
            periods: Number of periods for IRF
            shock_var: Variable to shock (None for all)
            response_vars: Variables to measure response (empty for all)
            
        Returns:
            Result dictionary with IRF data or error
        """
        try:
            # Load dataset and model
            user_id = session.dataset.user.id if session.dataset.user else None
            df, column_types, schema_orders = _read_dataset_file(session.dataset.file_path, user_id=user_id)
            model_results, endog_data, dependent_vars = IRFService._load_varx_model_results(session, df)
            
            if model_results is None or endog_data is None:
                return {
                    'success': False,
                    'error': 'Could not load VARX model results. Please re-run the analysis.'
                }
            
            # Get variable names and indices
            var_names = list(endog_data.columns) if hasattr(endog_data, 'columns') else dependent_vars
            shock_indices, response_indices = IRFService._get_shock_response_indices(
                var_names, shock_var, response_vars
            )
            
            # Generate IRF DataFrame
            irf_df = IRFService._generate_irf_dataframe(
                model_results, endog_data, var_names, periods, 
                shock_indices, response_indices, show_ci=True
            )
            
            if irf_df is None or irf_df.empty:
                return {
                    'success': False,
                    'error': 'Failed to generate IRF data'
                }
            
            # Convert DataFrame to list of dicts
            irf_data = irf_df.to_dict('records')
            
            return {
                'success': True,
                'data': irf_data
            }
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"IRF DATA ERROR: {error_msg}")
            print(traceback.format_exc())
            
            return {
                'success': False,
                'error': f'Error generating IRF data: {error_msg}'
            }
