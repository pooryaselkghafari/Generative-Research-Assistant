"""
Data cleaning utilities
"""
import pandas as pd
import numpy as np
import re


def add_statistical_functions(df, formula):
    """Add support for statistical functions like mean(), max(), min(), etc. in formulas
    Supports: min, max, mean, median, std, var, log (case-insensitive)
    Also converts ^ to ** for power operations (e.g., col1^2 becomes col1**2)
    """
    # Find all function calls in the formula (case-insensitive)
    function_pattern = r'(\w+)\(([^)]+)\)'
    matches = re.findall(function_pattern, formula)
    
    # Process matches in reverse order to avoid replacing overlapping patterns
    matches = list(reversed(matches))
    
    for func_name, column_name in matches:
        # Normalize function name to lowercase for case-insensitive matching
        func_name_lower = func_name.lower()
        
        # Supported functions (case-insensitive)
        supported_functions = ['mean', 'max', 'min', 'sum', 'count', 'std', 'median', 'var', 'log']
        
        if func_name_lower in supported_functions:
            # Clean column name (remove spaces)
            column_name = column_name.strip()
            
            if column_name in df.columns:
                # Calculate value based on function
                if func_name_lower == 'mean':
                    value = df[column_name].mean()
                elif func_name_lower == 'max':
                    value = df[column_name].max()
                elif func_name_lower == 'min':
                    value = df[column_name].min()
                elif func_name_lower == 'sum':
                    value = df[column_name].sum()
                elif func_name_lower == 'count':
                    value = df[column_name].count()
                elif func_name_lower == 'std':
                    value = df[column_name].std()
                elif func_name_lower == 'median':
                    value = df[column_name].median()
                elif func_name_lower == 'var':
                    value = df[column_name].var()
                elif func_name_lower == 'log':
                    # Log base 10 - calculate mean of log10 values (handling zeros/negatives)
                    col_data = df[column_name]
                    # Replace zeros and negatives with NaN before taking log
                    col_data_clean = col_data.replace([0, -np.inf, np.inf], np.nan)
                    col_data_clean = col_data_clean[col_data_clean > 0]  # Only positive values
                    if len(col_data_clean) > 0:
                        value = np.log10(col_data_clean).mean()
                    else:
                        value = 0
                    if pd.isna(value):
                        value = 0
                
                # Replace the function call with the calculated value (preserve original case)
                # Need to handle case-insensitive replacement
                import re as re_module
                pattern = re_module.escape(f'{func_name}({column_name})')
                formula = re_module.sub(pattern, str(value), formula, flags=re_module.IGNORECASE)
    
    # Convert ^ to ** for power operations (pandas uses ** for exponentiation)
    # This handles cases like col1^2, col1^3, (col1 + col2)^2, etc.
    # We need to be careful to only replace ^ when it's used for exponentiation
    # Pattern: match ^ followed by a number or expression in parentheses
    # Replace ^ with ** (pandas power operator)
    formula = re.sub(r'\^', '**', formula)
    
    return formula
