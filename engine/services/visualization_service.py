"""
Service for generating various visualizations including correlation heatmaps
and ANOVA plots.

This service encapsulates visualization logic to keep views thin and
improve maintainability.
"""
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from engine.models import AnalysisSession
from data_prep.file_handling import _read_dataset_file
from models.regression import (
    _build_correlation_heatmap_json,
    _get_continuous_variables,
    _get_continuous_variables_from_formula
)


class VisualizationService:
    """Service for generating visualizations."""
    
    @staticmethod
    def get_dataset_columns(dataset) -> Dict[str, List[str]]:
        """
        Get column information from dataset for visualization.
        
        Args:
            dataset: Dataset model instance
            
        Returns:
            Dictionary with numeric_columns, categorical_columns, and all_columns
        """
        import numpy as np
        
        user_id = dataset.user.id if dataset.user else None
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=user_id)
        
        # Get column information
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        
        # Add low-cardinality numeric columns as categorical
        try:
            max_categories = 20
            row_count = len(df)
            threshold = max_categories if row_count > 0 else max_categories
            for col in numeric_columns:
                if col not in categorical_columns:
                    unique_count = int(df[col].nunique(dropna=True))
                    if unique_count <= threshold:
                        categorical_columns.append(col)
        except Exception:
            pass
        
        # Preserve the original column order
        all_columns = df.columns.tolist()
        categorical_columns = [c for c in all_columns if c in set(categorical_columns)]
        
        return {
            'numeric_columns': numeric_columns,
            'categorical_columns': categorical_columns,
            'all_columns': all_columns,
        }
    
    @staticmethod
    def prepare_correlation_heatmap_variables(
        session: AnalysisSession,
        request_vars: Dict[str, List[str]]
    ) -> Tuple[List[str], List[str]]:
        """
        Prepare variables for correlation heatmap generation.
        
        Args:
            session: AnalysisSession object
            request_vars: Dictionary with 'x_vars' and 'y_vars' from request
            
        Returns:
            Tuple of (x_vars, y_vars) lists
        """
        user_id = session.dataset.user.id if session.dataset.user else None
        df, schema_types, schema_orders = _read_dataset_file(session.dataset.file_path, user_id=user_id)
        
        # Get continuous variables from the equation (default behavior)
        continuous_vars = _get_continuous_variables_from_formula(df, session.formula)
        
        # If no continuous variables in equation, fall back to all continuous variables
        if len(continuous_vars) < 2:
            continuous_vars = _get_continuous_variables(df)
            if len(continuous_vars) < 2:
                raise ValueError('Need at least 2 continuous variables for correlation heatmap')
        
        # Get selected variables from request
        x_vars = request_vars.get('x_vars', [])
        y_vars = request_vars.get('y_vars', [])
        
        # If no variables selected, use all continuous variables
        if not x_vars:
            x_vars = continuous_vars.copy()
        if not y_vars:
            y_vars = continuous_vars.copy()
        
        # Filter to only include variables that exist in the dataset
        x_vars = [
            var for var in x_vars 
            if var in df.columns and pd.api.types.is_numeric_dtype(df[var])
        ]
        y_vars = [
            var for var in y_vars 
            if var in df.columns and pd.api.types.is_numeric_dtype(df[var])
        ]
        
        if len(x_vars) < 1 or len(y_vars) < 1:
            raise ValueError('Need at least 1 variable for each axis')
        
        return x_vars, y_vars
    
    @staticmethod
    def generate_correlation_heatmap(
        session: AnalysisSession,
        x_vars: List[str],
        y_vars: List[str],
        options: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate correlation heatmap JSON.
        
        Args:
            session: AnalysisSession object
            x_vars: List of x-axis variables
            y_vars: List of y-axis variables
            options: Options dictionary (show_significance, color_scheme)
            
        Returns:
            Heatmap JSON string or None on error
        """
        user_id = session.dataset.user.id if session.dataset.user else None
        df, schema_types, schema_orders = _read_dataset_file(session.dataset.file_path, user_id=user_id)
        return _build_correlation_heatmap_json(df, x_vars, y_vars, options)
    
    @staticmethod
    def prepare_heatmap_options(request) -> Dict[str, Any]:
        """
        Prepare options for correlation heatmap from request.
        
        Args:
            request: Django request object
            
        Returns:
            Options dictionary
        """
        return {
            'show_significance': request.POST.get('show_significance', 'true').lower() == 'true',
            'color_scheme': request.POST.get('color_scheme', 'RdBu')
        }
    
    @staticmethod
    def generate_anova_plot_data(
        session: AnalysisSession,
        plot_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate ANOVA plot data.
        
        Args:
            session: AnalysisSession object
            plot_params: Dictionary with x_var, y_var, group_var, x_std, group_std, sig_level
            
        Returns:
            Result dictionary from ANOVA plot generation
        """
        from models.ANOVA import generate_anova_plot
        
        df, column_types, schema_orders = _read_dataset_file(session.dataset.file_path)
        
        return generate_anova_plot(
            df,
            plot_params['x_var'],
            plot_params['y_var'],
            plot_params.get('group_var'),
            plot_params.get('x_std', 1.0),
            plot_params.get('group_std', 1.0),
            plot_params.get('sig_level', 0.05)
        )

