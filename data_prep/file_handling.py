"""
File handling utilities for reading and processing datasets
"""
import json
import os
import pandas as pd
import numpy as np


def _auto_detect_column_types(df: pd.DataFrame) -> dict:
    """Automatically detect and assign data types to columns: numeric, binary, categorical, ordinal, or string."""
    column_types = {}
    
    for col in df.columns:
        # Skip if already numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            column_types[col] = 'numeric'
            continue
            
        # Skip if it's already a categorical with numeric categories
        if hasattr(df[col].dtype, 'categories') and pd.api.types.is_numeric_dtype(df[col].cat.categories):
            column_types[col] = 'numeric'
            continue
            
        # Try to convert to numeric, keeping track of how many values were successfully converted
        try:
            # Get the original non-null values
            original_non_null = df[col].notna()
            original_non_null_count = original_non_null.sum()
            
            if original_non_null_count == 0:
                column_types[col] = 'string'
                continue
                
            # Try to convert to numeric
            numeric_converted = pd.to_numeric(df[col], errors='coerce')
            
            # Count how many of the original non-null values were successfully converted
            # (not NaN in the converted version)
            successful_conversions = (original_non_null & numeric_converted.notna()).sum()
            
            # If more than 80% of non-null values can be converted to numeric
            if successful_conversions / original_non_null_count >= 0.8:
                # Convert the column to numeric
                df[col] = numeric_converted
                
                # Check if it's binary (exactly 2 unique values)
                unique_values = df[col].dropna().nunique()
                if unique_values == 2:
                    column_types[col] = 'binary'
                else:
                    column_types[col] = 'numeric'
            else:
                # Check if it's categorical (limited unique values)
                unique_values = df[col].dropna().nunique()
                if unique_values <= 10:  # Reasonable threshold for categorical
                    # Check if values look like they could be ordered (e.g., "Low", "Medium", "High")
                    values = df[col].dropna().unique()
                    if _looks_ordered(values):
                        column_types[col] = 'ordinal'
                    else:
                        column_types[col] = 'categorical'
                else:
                    column_types[col] = 'string'
        except Exception:
            # If conversion fails, check if it's categorical
            unique_values = df[col].dropna().nunique()
            if unique_values <= 10:
                values = df[col].dropna().unique()
                if _looks_ordered(values):
                    column_types[col] = 'ordinal'
                else:
                    column_types[col] = 'categorical'
            else:
                column_types[col] = 'string'
    
    return column_types

def _looks_ordered(values):
    """Check if values look like they could be ordered (e.g., "Low", "Medium", "High")."""
    # Convert to lowercase for comparison
    values_lower = [str(v).lower() for v in values]
    
    # Common ordered patterns
    ordered_patterns = [
        ['low', 'medium', 'high'],
        ['small', 'medium', 'large'],
        ['1', '2', '3', '4', '5'],
        ['a', 'b', 'c', 'd', 'f'],
        ['poor', 'fair', 'good', 'excellent'],
        ['never', 'rarely', 'sometimes', 'often', 'always'],
        ['disagree', 'neutral', 'agree'],
        ['strongly disagree', 'disagree', 'neutral', 'agree', 'strongly agree']
    ]
    
    # Check if values match any ordered pattern
    for pattern in ordered_patterns:
        if len(values_lower) >= 2 and all(v in pattern for v in values_lower):
            return True
    
    # Check if values are numeric strings that could be ordered
    try:
        numeric_values = [float(v) for v in values if str(v).replace('.', '').replace('-', '').isdigit()]
        if len(numeric_values) >= 2 and len(numeric_values) == len(values):
            return True
    except:
        pass
    
    return False

def _read_dataset_file(file_path):
    """Helper function to read dataset files (CSV or Excel) with schema loading"""
    file_extension = file_path.lower().split('.')[-1]
    
    # Read the file
    if file_extension in ['xlsx', 'xls']:
        df = pd.read_excel(file_path)
    elif file_extension == 'csv':
        df = pd.read_csv(file_path)
    else:
        # Try CSV first, then Excel as fallback
        try:
            df = pd.read_csv(file_path)
        except:
            df = pd.read_excel(file_path)
    
    # Auto-detect and assign column types
    detected_types = _auto_detect_column_types(df)
    
    # Load schema if it exists
    schema_types = {}
    schema_orders = {}
    try:
        schema_path = os.path.splitext(file_path)[0] + ".schema.json"
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            schema_types = schema.get('types', {})
            schema_orders = schema.get('orders', {})
    except Exception:
        pass
    
    # Apply saved types if schema exists
    if schema_types:
        df = _apply_types(df, schema_types, schema_orders)
    
    # Merge detected types with schema types (schema takes precedence)
    final_types = detected_types.copy()
    final_types.update(schema_types)
    
    return df, final_types, schema_orders


def _apply_types(df: pd.DataFrame, new_types: dict, orders: dict) -> pd.DataFrame:
    """Apply data type conversions based on user selections"""
    for col in df.columns:
        t = new_types.get(col, "auto")
        if t == "auto":
            continue
        if t == "numeric":
            # Convert categorical back to numeric if needed
            if hasattr(df[col].dtype, 'categories'):
                df[col] = df[col].astype(str)
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif t == "binary":
            s = df[col]
            if s.dropna().nunique() <= 2:
                uniq = list(s.dropna().unique())
                mapping = {}
                if len(uniq) == 2:
                    mapping = {uniq[0]: 0, uniq[1]: 1}
                elif len(uniq) == 1:
                    mapping = {uniq[0]: 1}
                df[col] = s.map(mapping).fillna(0).astype(int)
            else:
                df[col] = pd.to_numeric(s, errors="coerce").fillna(0)
                df[col] = (df[col] != 0).astype(int)
        elif t == "categorical":
            df[col] = df[col].astype("category")
        elif t == "ordinal":
            # Convert to text first, regardless of current data type
            df[col] = df[col].astype(str)
            # Replace 'nan' strings with actual NaN
            df[col] = df[col].replace('nan', pd.NA)
            
            # Get unique values (excluding NaN)
            unique_vals = df[col].dropna().unique()
            
            if len(unique_vals) > 0:
                # Use user-provided order if available, otherwise use sorted unique values
                order = [x.strip() for x in (orders.get(col) or "").split(",") if x.strip()]
                if not order:
                    # Fallback to sorted unique values
                    order = sorted(unique_vals)
                
                # Create ordinal categorical with user-specified order
                from pandas.api.types import CategoricalDtype
                dtype = CategoricalDtype(categories=order, ordered=True)
                df[col] = df[col].astype(dtype)
        elif t == "count":
            # Convert categorical back to numeric if needed
            if hasattr(df[col].dtype, 'categories'):
                df[col] = df[col].astype(str)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            df[col] = df[col].clip(lower=0).round().astype("int64")
    return df
