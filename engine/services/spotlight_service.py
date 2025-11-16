"""
Service for generating spotlight plots for regression interactions.

This service encapsulates all logic related to spotlight plot generation,
including model loading, options preparation, and plot generation for
different regression types (standard, ordinal, multinomial).
"""
import pickle
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from django.conf import settings
from engine.models import AnalysisSession
from engine.modules import get_module
from data_prep.file_handling import _read_dataset_file
from models.regression import generate_spotlight_for_interaction


class SpotlightService:
    """Service for generating spotlight plots."""
    
    @staticmethod
    def load_fitted_model(session: AnalysisSession, df: pd.DataFrame) -> Optional[Any]:
        """
        Load fitted model from session or generate it if not available.
        
        Args:
            session: AnalysisSession object
            df: DataFrame with the dataset
            
        Returns:
            Fitted model object or None if unavailable
        """
        # Check if we have a stored fitted model in the session
        if hasattr(session, 'fitted_model') and session.fitted_model:
            try:
                fitted_model = pickle.loads(session.fitted_model)
                print("Using stored fitted model")
                return fitted_model
            except Exception as e:
                print(f"Failed to load stored model: {e}")
        
        # If no stored model, run the analysis to get the fitted model
        print("No stored model found, running analysis...")
        module = get_module(session.module)
        results = module.run(
            df, 
            session.formula, 
            session.analysis_type, 
            settings.MEDIA_ROOT, 
            session.options
        )
        fitted_model = results.get('fitted_model')
        
        # Store the fitted model in the session for future use
        if fitted_model:
            try:
                session.fitted_model = pickle.dumps(fitted_model)
                session.save()
                print("Stored fitted model in session")
            except Exception as e:
                print(f"Failed to store model: {e}")
        
        return fitted_model
    
    @staticmethod
    def prepare_spotlight_options(request, session: AnalysisSession) -> Dict[str, Any]:
        """
        Prepare options dictionary for spotlight plot from request and session.
        
        Args:
            request: Django request object
            session: AnalysisSession object
            
        Returns:
            Dictionary of options for spotlight plot generation
        """
        # Start with session options
        custom_options = session.options.copy()
        
        # Override with custom values from the form
        option_mappings = {
            'moderator_var': 'moderator_var',
            'x_name': 'x_name',
            'y_name': 'y_name',
            'legend_low': 'legend_low',
            'legend_high': 'legend_high',
            'color_low': 'color_low',
            'color_high': 'color_high',
            'line_style_low': 'line_style_low',
            'line_style_high': 'line_style_high',
            'background_color': 'background_color',
            'moderator_separation': 'moderator_separation',
            'moderator_std_dev_multiplier': 'moderator_std_dev_multiplier',
            'ordinal_category': 'ordinal_category',
            'multinomial_category': 'multinomial_category',
        }
        
        for request_key, option_key in option_mappings.items():
            value = request.POST.get(request_key)
            if value:
                if request_key in ['show_ci', 'show_grid']:
                    custom_options[option_key] = value == 'true'
                else:
                    custom_options[option_key] = value
                    if request_key == 'moderator_std_dev_multiplier':
                        print(f"Custom moderator_std_dev_multiplier: {custom_options[option_key]}")
                    elif request_key == 'multinomial_category':
                        print(f"Custom multinomial_category: {custom_options[option_key]}")
        
        print(f"Custom options: {custom_options}")
        return custom_options
    
    @staticmethod
    def detect_model_type(fitted_model: Any) -> Tuple[bool, bool]:
        """
        Detect if the fitted model is ordinal or multinomial regression.
        
        Args:
            fitted_model: The fitted model object
            
        Returns:
            Tuple of (is_ordinal, is_multinomial) booleans
        """
        is_ordinal = (
            'Ordinal regression' in str(type(fitted_model)) or 
            (hasattr(fitted_model, 'model') and 'OrderedModel' in str(type(fitted_model.model)))
        )
        
        is_multinomial = (
            'Multinomial regression' in str(type(fitted_model)) or 
            (hasattr(fitted_model, 'model') and 'mnlogit' in str(type(fitted_model.model)))
        )
        
        print(f"DEBUG: is_multinomial = {is_multinomial}")
        print(f"DEBUG: fitted_model type = {type(fitted_model)}")
        print(f"DEBUG: fitted_model str = {str(type(fitted_model))}")
        
        return is_ordinal, is_multinomial
    
    @staticmethod
    def parse_interaction(interaction: str) -> Tuple[str, str]:
        """
        Parse interaction string to extract x and moderator variables.
        
        Args:
            interaction: Interaction string (e.g., "x*y" or "x:y")
            
        Returns:
            Tuple of (x_var, moderator_var)
        """
        if "*" in interaction:
            parts = [p.strip() for p in interaction.split("*")]
            if len(parts) >= 2:
                return parts[0], parts[1]
        else:
            parts = interaction.split(":")
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()
        
        # Fallback
        return interaction, "Moderator"
    
    @staticmethod
    def prepare_ordinal_options(
        interaction: str, 
        custom_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare options for ordinal regression spotlight plot.
        
        Args:
            interaction: Interaction string
            custom_options: Base options dictionary
            
        Returns:
            Prepared options dictionary
        """
        x_var, moderator_var = SpotlightService.parse_interaction(interaction)
        ordinal_options = custom_options.copy()
        
        # Set default variable names if not provided
        if not ordinal_options.get('x_name'):
            ordinal_options['x_name'] = x_var
        if not ordinal_options.get('moderator_var'):
            ordinal_options['moderator_var'] = moderator_var
        if not ordinal_options.get('y_name'):
            ordinal_category = ordinal_options.get('ordinal_category', 'Category')
            ordinal_options['y_name'] = f'Probability of {ordinal_category}'
        if not ordinal_options.get('moderator_separation'):
            ordinal_options['moderator_separation'] = 'mean'
        
        return ordinal_options
    
    @staticmethod
    def should_use_precomputed_predictions(
        separation_method: str,
        std_dev_multiplier: float
    ) -> bool:
        """
        Check if precomputed predictions can be used.
        
        Precomputed predictions are only valid for default settings:
        - separation_method == 'mean'
        - std_dev_multiplier == 1.0
        
        Args:
            separation_method: Moderator separation method
            std_dev_multiplier: Standard deviation multiplier
            
        Returns:
            True if precomputed predictions can be used
        """
        return separation_method == 'mean' and std_dev_multiplier == 1.0
    
    @staticmethod
    def generate_spotlight_plot(
        fitted_model: Any,
        df: pd.DataFrame,
        interaction: str,
        options: Dict[str, Any],
        is_ordinal: bool = False,
        is_multinomial: bool = False
    ) -> Optional[str]:
        """
        Generate spotlight plot JSON for the given interaction.
        
        Args:
            fitted_model: The fitted model object
            df: DataFrame with the dataset
            interaction: Interaction string
            options: Options dictionary
            is_ordinal: Whether this is an ordinal regression
            is_multinomial: Whether this is a multinomial regression
            
        Returns:
            Plot JSON string or None on error
        """
        return generate_spotlight_for_interaction(
            fitted_model, 
            df, 
            interaction, 
            options, 
            is_ordinal=is_ordinal, 
            is_multinomial=is_multinomial
        )
    
    @staticmethod
    def format_error_response(
        interaction: str,
        df: pd.DataFrame,
        error_type: str = 'unknown'
    ) -> str:
        """
        Format error response for spotlight plot generation failures.
        
        Args:
            interaction: Interaction string that failed
            df: DataFrame with the dataset
            error_type: Type of error ('unknown', 'missing_x', 'missing_moderator')
            
        Returns:
            Error message string
        """
        x, m = SpotlightService.parse_interaction(interaction)
        
        if error_type == 'missing_x':
            return f'Variable "{x}" not found in dataset. Available columns: {list(df.columns)}'
        elif error_type == 'missing_moderator':
            return f'Moderator variable "{m}" not found in dataset. Available columns: {list(df.columns)}'
        elif error_type == 'invalid_format':
            return f'Invalid interaction format: {interaction}'
        else:
            return 'Failed to generate spotlight plot - unknown error'

