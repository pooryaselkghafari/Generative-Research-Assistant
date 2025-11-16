"""
Service for retrieving fitted models from sessions.
"""
import pickle
from typing import List, Dict, Any
from engine.models import AnalysisSession, Dataset
from data_prep.file_handling import _read_dataset_file


class ModelService:
    """Service for model-related operations."""
    
    @staticmethod
    def get_equation_results(
        session: AnalysisSession,
        dataset: Dataset
    ) -> List[Dict[str, Any]]:
        """
        Get fitted models for all equations in a session.
        
        For multi-equation regression, re-runs the analysis to get fitted models.
        For single-equation, unpickles the stored fitted model.
        
        Args:
            session: AnalysisSession object
            dataset: Dataset object
            
        Returns:
            List of equation result dictionaries
        """
        # Load the dataset
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Check if this is a multi-equation regression
        is_multi_equation = ModelService._check_multi_equation(session)
        
        if is_multi_equation:
            return ModelService._get_multi_equation_results(
                session, df, column_types, schema_orders
            )
        else:
            return ModelService._get_single_equation_result(session)
    
    @staticmethod
    def _check_multi_equation(session: AnalysisSession) -> bool:
        """Check if session contains multi-equation regression."""
        formula = session.formula
        equation_lines = [line.strip() for line in formula.split('\n') 
                         if line.strip() and '~' in line]
        is_multi_equation = len(equation_lines) > 1 and session.module == 'regression'
        
        print(f"DEBUG: Checking for multi-equation regression")
        print(f"DEBUG: Formula: {formula}")
        print(f"DEBUG: Equation lines count: {len(equation_lines)}")
        print(f"DEBUG: Module: {session.module}")
        print(f"DEBUG: Is multi-equation: {is_multi_equation}")
        
        return is_multi_equation
    
    @staticmethod
    def _get_multi_equation_results(session: AnalysisSession, df, column_types, schema_orders) -> List[Dict[str, Any]]:
        """Get results for multi-equation regression by re-running analysis."""
        from models.regression import RegressionModule
        
        print(f"DEBUG: Re-running multi-equation analysis to get fitted models")
        try:
            # Prepare options
            options = ModelService._prepare_multi_equation_options(session)
            
            # Parse equation lines
            formula = session.formula
            equation_lines = [line.strip() for line in formula.split('\n') 
                             if line.strip() and '~' in line]
            
            # Run the multi-equation analysis
            results = RegressionModule._run_multi_equation(
                df, equation_lines, session.analysis_type, None, options,
                schema_types=column_types, schema_orders=schema_orders
            )
            
            if not results or 'equation_results' not in results:
                raise ValueError('Failed to re-run multi-equation analysis')
            
            equation_results = results.get('equation_results', [])
            print(f"DEBUG: Got {len(equation_results)} equation results")
            return equation_results
            
        except Exception as e:
            import traceback
            print(f"DEBUG: Error re-running multi-equation analysis: {e}")
            print(traceback.format_exc())
            raise ValueError(f'Failed to re-run analysis: {str(e)}')
    
    @staticmethod
    def _prepare_multi_equation_options(session: AnalysisSession) -> Dict[str, Any]:
        """Prepare options for multi-equation regression with all display flags enabled."""
        options = session.options if session.options else {}
        multi_eq_options = options.copy()
        multi_eq_options['show_se'] = True
        multi_eq_options['show_p'] = True
        multi_eq_options['show_ci'] = True
        multi_eq_options['show_t'] = True
        return multi_eq_options
    
    @staticmethod
    def _get_single_equation_result(session: AnalysisSession) -> List[Dict[str, Any]]:
        """Get result for single-equation regression from stored fitted model."""
        if not session.fitted_model:
            raise ValueError('No fitted model found for this session')
        
        # Unpickle the fitted model
        try:
            fitted_model = pickle.loads(session.fitted_model)
        except Exception as e:
            raise ValueError(f'Failed to load fitted model: {str(e)}')
        
        # Extract dependent variable from formula
        formula = session.formula
        dependent_var = formula.split('~')[0].strip() if '~' in formula else 'y'
        
        # Create a single-item list for consistent processing
        return [{
            'dependent_var': dependent_var,
            'formula': formula,
            'fitted_model': fitted_model,
            'regression_type': 'Unknown'
        }]
