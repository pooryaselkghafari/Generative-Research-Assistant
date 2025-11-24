"""
Service class for calculating model residuals/errors.

This service extracts residual calculation logic from views to improve
maintainability and testability.
"""
import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any


class ResidualCalculationService:
    """Service for calculating residuals from fitted statistical models."""
    
    @staticmethod
    def calculate_all_residuals(
        equation_results: List[Dict[str, Any]],
        session_name: str,
        df: pd.DataFrame
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Calculate residuals for all equations in a multi-equation regression.
        
        Args:
            equation_results: List of equation result dictionaries, each containing
                             'fitted_model', 'dependent_var', 'formula', etc.
            session_name: Sanitized session name for column naming
            df: DataFrame containing the dataset (for category extraction)
            
        Returns:
            Tuple of (residual_columns dict, column_names list)
        """
        residual_columns = {}
        column_names = []
        
        for eq_result in equation_results:
            fitted_model = eq_result.get('fitted_model')
            dv_name = eq_result.get('dependent_var', 'y')
            eq_formula = eq_result.get('formula', '')
            
            if not fitted_model:
                print(f"DEBUG: Skipping equation for {dv_name} - no fitted model")
                continue
            
            print(f"DEBUG: Processing equation for {dv_name}")
            
            # Determine model type
            model_type_str = ResidualCalculationService._get_model_type_string(fitted_model)
            model_type_name = ResidualCalculationService._determine_model_type_name(
                model_type_str, fitted_model
            )
            
            print(f"DEBUG: Model type name for {dv_name}: {model_type_name}")
            
            # Sanitize dependent variable name
            dv_safe = ResidualCalculationService._sanitize_name(dv_name)
            
            # Calculate residuals based on model type
            eq_residuals, eq_names = ResidualCalculationService._calculate_residuals_for_model(
                fitted_model=fitted_model,
                dv_name=dv_name,
                dv_safe=dv_safe,
                model_type_str=model_type_str,
                model_type_name=model_type_name,
                eq_formula=eq_formula,
                session_name=session_name,
                df=df
            )
            
            residual_columns.update(eq_residuals)
            column_names.extend(eq_names)
        
        return residual_columns, column_names
    
    @staticmethod
    def _get_model_type_string(fitted_model: Any) -> str:
        """Get model type string from fitted model."""
        model_type_str = str(type(fitted_model))
        if hasattr(fitted_model, 'model'):
            model_type_str += ' ' + str(type(fitted_model.model))
        return model_type_str
    
    @staticmethod
    def _determine_model_type_name(model_type_str: str, fitted_model: Any) -> str:
        """Determine model type name for column naming."""
        if 'OrderedModel' in model_type_str:
            return 'ordinal_regression'
        elif 'MultinomialResults' in model_type_str:
            return 'multinomial_regression'
        elif 'GLMResults' in model_type_str:
            # Check if it's a binomial GLM (logistic regression)
            try:
                if hasattr(fitted_model, 'model') and hasattr(fitted_model.model, 'family'):
                    family_name = str(fitted_model.model.family).lower()
                    if 'binomial' in family_name:
                        return 'binomial_regression'
                    else:
                        return 'glm_regression'
                else:
                    return 'glm_regression'
            except Exception as e:
                print(f"DEBUG: Could not determine GLM family: {e}")
                return 'glm_regression'
        elif 'OLSResults' in model_type_str or 'RegressionResults' in model_type_str:
            return 'ols_regression'
        else:
            return 'model_regression'
    
    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize a name for use in column names."""
        name = name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        return re.sub(r'[^\w\-_]', '_', name)
    
    @staticmethod
    def _calculate_residuals_for_model(
        fitted_model: Any,
        dv_name: str,
        dv_safe: str,
        model_type_str: str,
        model_type_name: str,
        eq_formula: str,
        session_name: str,
        df: pd.DataFrame
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Calculate residuals for a single fitted model.
        
        Returns:
            Tuple of (residual_columns dict, column_names list)
        """
        residual_columns = {}
        column_names = []
        
        if 'OLSResults' in model_type_str or 'RegressionResults' in model_type_str:
            # OLS (Linear Regression)
            residuals, names = ResidualCalculationService._calculate_ols_residuals(
                fitted_model, dv_safe, model_type_name, session_name
            )
            residual_columns.update(residuals)
            column_names.extend(names)
            
        elif 'GLMResults' in model_type_str:
            # GLM (Binomial logistic regression or other GLM)
            residuals, names = ResidualCalculationService._calculate_glm_residuals(
                fitted_model, dv_safe, model_type_name, session_name
            )
            residual_columns.update(residuals)
            column_names.extend(names)
            
        elif 'MultinomialResults' in model_type_str:
            # Multinomial Logit
            residuals, names = ResidualCalculationService._calculate_multinomial_residuals(
                fitted_model, dv_name, dv_safe, model_type_name, eq_formula, session_name, df
            )
            residual_columns.update(residuals)
            column_names.extend(names)
            
        elif 'OrderedModel' in model_type_str:
            # Ordered Logit / Probit
            residuals, names = ResidualCalculationService._calculate_ordinal_residuals(
                fitted_model, dv_name, dv_safe, model_type_name, eq_formula, session_name, df
            )
            residual_columns.update(residuals)
            column_names.extend(names)
            
        else:
            # Fallback: Try to get residuals from common attributes
            residuals, names = ResidualCalculationService._calculate_fallback_residuals(
                fitted_model, dv_name, dv_safe, model_type_name, session_name
            )
            residual_columns.update(residuals)
            column_names.extend(names)
        
        return residual_columns, column_names
    
    @staticmethod
    def _calculate_ols_residuals(
        fitted_model: Any,
        dv_safe: str,
        model_type_name: str,
        session_name: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Calculate residuals for OLS models."""
        residual_columns = {}
        column_names = []
        
        # Raw residuals
        residuals = fitted_model.resid
        col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_raw'
        residual_columns[col_name] = residuals
        column_names.append(col_name)
        
        # Standardized residuals
        if hasattr(fitted_model, 'resid_pearson'):
            pearson_residuals = fitted_model.resid_pearson
            col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_pearson'
            residual_columns[col_name] = pearson_residuals
            column_names.append(col_name)
        
        return residual_columns, column_names
    
    @staticmethod
    def _calculate_glm_residuals(
        fitted_model: Any,
        dv_safe: str,
        model_type_name: str,
        session_name: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Calculate residuals for GLM models."""
        residual_columns = {}
        column_names = []
        
        # Response residuals
        if hasattr(fitted_model, 'resid_response'):
            response_residuals = fitted_model.resid_response
            col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_response'
            residual_columns[col_name] = response_residuals
            column_names.append(col_name)
        
        # Pearson residuals
        if hasattr(fitted_model, 'resid_pearson'):
            pearson_residuals = fitted_model.resid_pearson
            col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_pearson'
            residual_columns[col_name] = pearson_residuals
            column_names.append(col_name)
        
        # Deviance residuals
        if hasattr(fitted_model, 'resid_deviance'):
            deviance_residuals = fitted_model.resid_deviance
            col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_deviance'
            residual_columns[col_name] = deviance_residuals
            column_names.append(col_name)
        
        # Working residuals
        if hasattr(fitted_model, 'resid_working'):
            working_residuals = fitted_model.resid_working
            col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_working'
            residual_columns[col_name] = working_residuals
            column_names.append(col_name)
        
        return residual_columns, column_names
    
    @staticmethod
    def _get_category_names(dv: str, df: pd.DataFrame) -> Optional[List[str]]:
        """Get category names from dependent variable."""
        try:
            if dv in df.columns:
                unique_cats = df[dv].dropna().unique()
                category_names = sorted([str(cat) for cat in unique_cats])
                # Sanitize category names
                category_names = [ResidualCalculationService._sanitize_name(cat) for cat in category_names]
                print(f"DEBUG: Found {len(category_names)} categories: {category_names}")
                return category_names
        except Exception as e:
            print(f"DEBUG: Could not get category names: {e}")
        return None
    
    @staticmethod
    def _calculate_multinomial_residuals(
        fitted_model: Any,
        dv_name: str,
        dv_safe: str,
        model_type_name: str,
        eq_formula: str,
        session_name: str,
        df: pd.DataFrame
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Calculate residuals for multinomial models."""
        residual_columns = {}
        column_names = []
        
        # Get category names
        category_names = None
        if '~' in eq_formula:
            dv = eq_formula.split('~')[0].strip()
            category_names = ResidualCalculationService._get_category_names(dv, df)
        
        # Try to get response residuals
        try:
            if hasattr(fitted_model, 'resid_response'):
                response_residuals = fitted_model.resid_response
                residuals, names = ResidualCalculationService._process_multivariate_residuals(
                    response_residuals, 'response', dv_safe, model_type_name,
                    session_name, category_names
                )
                residual_columns.update(residuals)
                column_names.extend(names)
        except (ValueError, AttributeError) as e:
            # Calculate manually if resid_response fails
            print(f"DEBUG: resid_response not available for multinomial model: {e}")
            print(f"DEBUG: Calculating response residuals manually...")
            try:
                predictions = fitted_model.predict()
                actual_values = fitted_model.model.endog
                
                # Convert to one-hot encoding
                n_categories = predictions.shape[1]
                actual_onehot = np.zeros_like(predictions)
                for i, actual_cat in enumerate(actual_values):
                    if not np.isnan(actual_cat) and 0 <= int(actual_cat) < n_categories:
                        actual_onehot[i, int(actual_cat)] = 1.0
                
                # Calculate response residuals
                response_residuals = actual_onehot - predictions
                
                # Add each category's residuals
                for col_idx in range(response_residuals.shape[1]):
                    if category_names and col_idx < len(category_names):
                        category_name = category_names[col_idx]
                    else:
                        category_name = f'cat{col_idx}'
                    col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_response_{category_name}'
                    residual_columns[col_name] = pd.Series(response_residuals[:, col_idx])
                    column_names.append(col_name)
                print(f"DEBUG: Successfully calculated {response_residuals.shape[1]} response residual columns")
            except Exception as e2:
                print(f"DEBUG: Failed to calculate response residuals manually: {e2}")
        
        # Pearson residuals
        try:
            if hasattr(fitted_model, 'resid_pearson'):
                pearson_residuals = fitted_model.resid_pearson
                residuals, names = ResidualCalculationService._process_multivariate_residuals(
                    pearson_residuals, 'pearson', dv_safe, model_type_name,
                    session_name, category_names
                )
                residual_columns.update(residuals)
                column_names.extend(names)
        except (ValueError, AttributeError) as e:
            print(f"DEBUG: resid_pearson not available for multinomial model: {e}")
        
        return residual_columns, column_names
    
    @staticmethod
    def _process_multivariate_residuals(
        residuals: Any,
        residual_type: str,
        dv_safe: str,
        model_type_name: str,
        session_name: str,
        category_names: Optional[List[str]]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Process multivariate residuals (DataFrame or 2D array)."""
        residual_columns = {}
        column_names = []
        
        if isinstance(residuals, pd.DataFrame):
            for col in residuals.columns:
                residual_series = residuals[col]
                if isinstance(residual_series, pd.Series):
                    if len(residual_series.shape) == 1:
                        col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_{residual_type}_{col}'
                        residual_columns[col_name] = residual_series
                        column_names.append(col_name)
                else:
                    residual_series = pd.Series(residual_series)
                    col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_{residual_type}_{col}'
                    residual_columns[col_name] = residual_series
                    column_names.append(col_name)
                    
        elif isinstance(residuals, np.ndarray):
            if len(residuals.shape) == 2:
                # 2D array - extract each column
                for col_idx in range(residuals.shape[1]):
                    if category_names and col_idx < len(category_names):
                        category_name = category_names[col_idx]
                    else:
                        category_name = f'cat{col_idx}'
                    col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_{residual_type}_{category_name}'
                    residual_columns[col_name] = pd.Series(residuals[:, col_idx])
                    column_names.append(col_name)
            else:
                # 1D array
                col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_{residual_type}'
                residual_columns[col_name] = pd.Series(residuals)
                column_names.append(col_name)
        else:
            # Try to convert to Series
            try:
                residual_series = pd.Series(residuals)
                col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual_{residual_type}'
                residual_columns[col_name] = residual_series
                column_names.append(col_name)
            except Exception as e:
                print(f"DEBUG: Error converting {residual_type} residuals to Series: {e}")
        
        return residual_columns, column_names
    
    @staticmethod
    def _calculate_ordinal_residuals(
        fitted_model: Any,
        dv_name: str,
        dv_safe: str,
        model_type_name: str,
        eq_formula: str,
        session_name: str,
        df: pd.DataFrame
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Calculate residuals for ordinal models."""
        residual_columns = {}
        column_names = []
        
        if '~' not in eq_formula:
            return residual_columns, column_names
        
        dv = eq_formula.split('~')[0].strip()
        
        if not hasattr(fitted_model, 'predict') or dv not in df.columns:
            return residual_columns, column_names
        
        try:
            predictions = fitted_model.predict()
            
            # Extract predicted probability (use second class if available)
            if isinstance(predictions, np.ndarray):
                if len(predictions.shape) > 1:
                    predicted_prob = predictions[:, 1] if predictions.shape[1] > 1 else predictions[:, 0]
                else:
                    predicted_prob = predictions
            elif isinstance(predictions, pd.DataFrame):
                predicted_prob = predictions.iloc[:, 1].values if predictions.shape[1] > 1 else predictions.iloc[:, 0].values
            else:
                predictions_array = np.array(predictions)
                if len(predictions_array.shape) > 1 and predictions_array.shape[1] > 1:
                    predicted_prob = predictions_array[:, 1]
                else:
                    predicted_prob = predictions_array.flatten()
            
            # Get actual values
            actual_values_full = df[dv].copy()
            if not pd.api.types.is_numeric_dtype(actual_values_full):
                actual_values_full = pd.Categorical(actual_values_full).codes
                actual_values_full = pd.Series(actual_values_full, index=df.index).replace(-1, np.nan)
            
            actual_values_clean = actual_values_full.dropna()
            
            # Calculate response residuals
            if len(actual_values_clean) == len(predicted_prob):
                response_residuals_clean = actual_values_clean.values - predicted_prob
                response_residuals = pd.Series(index=df.index, dtype=float)
                response_residuals.loc[actual_values_clean.index] = response_residuals_clean
                response_residuals.loc[actual_values_full.isna()] = np.nan
                
                col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual'
                residual_columns[col_name] = response_residuals
                column_names.append(col_name)
                print(f"DEBUG: Added {col_name} with {len(response_residuals.dropna())} non-null values")
            else:
                print(f"DEBUG: Length mismatch - actual: {len(actual_values_clean)}, predicted: {len(predicted_prob)}")
                # Fallback: align by position
                response_residuals = pd.Series(index=df.index, dtype=float)
                min_len = min(len(actual_values_clean), len(predicted_prob))
                response_residuals.iloc[:min_len] = actual_values_clean.iloc[:min_len].values - predicted_prob[:min_len]
                col_name = f'{session_name}_{dv_safe}_{model_type_name}_residual'
                residual_columns[col_name] = response_residuals
                column_names.append(col_name)
        except Exception as e:
            import traceback
            print(f"Error calculating ordered model residuals: {e}")
            print(traceback.format_exc())
        
        return residual_columns, column_names
    
    @staticmethod
    def _calculate_fallback_residuals(
        fitted_model: Any,
        dv_name: str,
        dv_safe: str,
        model_type_name: str,
        session_name: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Fallback method to extract any available residuals."""
        residual_columns = {}
        column_names = []
        
        print(f"DEBUG: Unknown model type for {dv_name}, trying fallback residual extraction...")
        
        residual_attrs = ['resid', 'resid_response', 'resid_pearson', 'resid_deviance', 'resid_working']
        found_any = False
        
        for attr in residual_attrs:
            if hasattr(fitted_model, attr):
                try:
                    residuals = getattr(fitted_model, attr)
                    if attr == 'resid':
                        base_name = 'residual'
                    else:
                        base_name = attr.replace('resid', 'residual')
                    
                    col_name = f'{session_name}_{dv_safe}_{model_type_name}_{base_name}'
                    
                    if isinstance(residuals, pd.DataFrame):
                        for col in residuals.columns:
                            df_col_name = f'{col_name}_{col}'
                            residual_columns[df_col_name] = residuals[col]
                            column_names.append(df_col_name)
                    else:
                        residual_columns[col_name] = residuals
                        column_names.append(col_name)
                    found_any = True
                    print(f"DEBUG: Found and added {attr} as {col_name}")
                except Exception as e:
                    print(f"DEBUG: Error accessing {attr}: {e}")
                    continue
        
        if not found_any:
            print(f"DEBUG: No residual attributes found for {dv_name}. Model attributes: {[a for a in dir(fitted_model) if 'resid' in a.lower()]}")
        
        return residual_columns, column_names

