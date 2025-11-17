"""
Service for filtering rows from datasets based on conditions.

This service encapsulates logic for previewing and applying row filtering
operations on datasets.
"""
import json
import pandas as pd
import re
from typing import Dict, Any, List, Tuple, Optional
from data_prep.cleaning import add_statistical_functions


class RowFilteringService:
    """Service for row filtering operations."""
    
    @staticmethod
    def validate_condition_formula(formula: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a condition formula for syntax errors.
        
        Args:
            formula: Condition formula string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not formula.strip():
            return False, 'Empty condition provided'
        
        # Check for common syntax errors
        if '=' in formula and '==' not in formula and '!=' not in formula and '>=' not in formula and '<=' not in formula:
            return False, f'Use == for equality comparison, not =. Did you mean: {formula.replace("=", "==")}'
        
        return True, None
    
    @staticmethod
    def normalize_formula(formula: str) -> str:
        """
        Normalize formula by converting AND/OR/NOT to lowercase.
        
        Args:
            formula: Condition formula string
            
        Returns:
            Normalized formula
        """
        formula = re.sub(r'\bAND\b', 'and', formula)
        formula = re.sub(r'\bOR\b', 'or', formula)
        formula = re.sub(r'\bNOT\b', 'not', formula)
        return formula
    
    @staticmethod
    def _quote_complex_columns(df: pd.DataFrame, formula: str) -> str:
        """
        Wrap column names that contain spaces or special characters in backticks so
        pandas can parse them (e.g., `Week Number`).
        """
        unsafe_columns = [
            col for col in df.columns
            if not re.match(r'^[A-Za-z_]\w*$', str(col))
        ]
        
        def replace_column(match):
            matched = match.group(0)
            return f'`{matched}`'
        
        for col in sorted(unsafe_columns, key=len, reverse=True):
            if not col:
                continue
            pattern = re.compile(
                rf'(?<![`])(?<!\w){re.escape(str(col))}(?!\w)(?![`])'
            )
            formula = pattern.sub(replace_column, formula)
        return formula
    
    @staticmethod
    def evaluate_condition(df: pd.DataFrame, formula: str) -> pd.Series:
        """
        Evaluate a condition formula on a dataframe.
        
        Args:
            df: DataFrame to evaluate on
            formula: Condition formula string
            
        Returns:
            Boolean Series indicating which rows match the condition
        """
        # Normalize formula
        formula = RowFilteringService.normalize_formula(formula)
        
        # Quote any column names that require it (spaces, punctuation, etc.)
        formula = RowFilteringService._quote_complex_columns(df, formula)
        
        # Add support for statistical functions
        formula_with_functions = add_statistical_functions(df, formula)
        
        # Evaluate the condition
        # NOTE: df.eval() is pandas DataFrame.eval(), not Python eval() - it's safe for DataFrame expressions
        return df.eval(formula_with_functions)
    
    @staticmethod
    def apply_conditions(df: pd.DataFrame, conditions: List[Dict[str, Any]]) -> Tuple[pd.Series, Optional[str]]:
        """
        Apply multiple conditions to a dataframe.
        
        Args:
            df: DataFrame to filter
            conditions: List of condition dictionaries with 'operator' and 'formula' keys
            
        Returns:
            Tuple of (rows_to_drop_series, error_message)
        """
        rows_to_drop = pd.Series([False] * len(df))  # Start with no rows to drop
        
        for condition in conditions:
            operator = condition.get('operator', 'drop')
            formula = condition.get('formula', '')
            
            if not formula:
                continue
            
            # Validate formula
            is_valid, error_msg = RowFilteringService.validate_condition_formula(formula)
            if not is_valid:
                return None, error_msg
            
            try:
                # Evaluate condition
                condition_result = RowFilteringService.evaluate_condition(df, formula)
                
                if operator == 'drop':
                    # Drop rows where condition is True
                    rows_to_drop = rows_to_drop | condition_result
                else:  # keep
                    # Keep rows where condition is True, so drop rows where condition is False
                    rows_to_drop = rows_to_drop | ~condition_result
                    
            except Exception as e:
                error_msg = str(e)
                # Provide more helpful error messages
                if "unsupported operand type(s)" in error_msg:
                    return None, (
                        'Invalid data types in condition. Make sure you are comparing '
                        'compatible types (e.g., numbers with numbers, strings with strings)'
                    )
                elif "name" in error_msg and "is not defined" in error_msg:
                    return None, f'Column name not found. Available columns: {list(df.columns)}'
                elif "invalid syntax" in error_msg.lower():
                    return None, (
                        f'Invalid syntax in condition. Please check your operators '
                        f'(==, !=, >, <, >=, <=, and, or). Note: Use lowercase "and"/"or", not "AND"/"OR".'
                    )
                else:
                    return None, f'Invalid condition: {error_msg}'
        
        return rows_to_drop, None
    
    @staticmethod
    def preview_drop_rows(df: pd.DataFrame, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Preview which rows would be dropped.
        
        Args:
            df: DataFrame to preview
            conditions: List of condition dictionaries
            
        Returns:
            Dictionary with preview information or error
        """
        rows_to_drop, error = RowFilteringService.apply_conditions(df, conditions)
        
        if error:
            return {'error': error}
        
        rows_to_drop_df = df[rows_to_drop]
        rows_to_keep = df[~rows_to_drop]
        
        # Get preview of first 10 rows to be dropped
        preview_rows = rows_to_drop_df.head(10).to_dict('records')
        
        return {
            'success': True,
            'rows_to_drop': len(rows_to_drop_df),
            'rows_remaining': len(rows_to_keep),
            'columns': list(df.columns),
            'preview_rows': preview_rows
        }
    
    @staticmethod
    def apply_drop_rows(df: pd.DataFrame, conditions: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, int, Optional[str]]:
        """
        Apply row dropping to a dataframe.
        
        Args:
            df: DataFrame to filter
            conditions: List of condition dictionaries
            
        Returns:
            Tuple of (filtered_dataframe, rows_dropped_count, error_message)
        """
        rows_to_drop, error = RowFilteringService.apply_conditions(df, conditions)
        
        if error:
            return None, 0, error
        
        # Apply the mask to keep only the rows we want
        df_filtered = df[~rows_to_drop]
        rows_dropped = len(df) - len(df_filtered)
        
        return df_filtered, rows_dropped, None

