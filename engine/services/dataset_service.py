"""
Service for dataset operations related to residual storage.
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List


class DatasetService:
    """Service for dataset operations."""
    
    @staticmethod
    def align_and_add_residuals(
        df: pd.DataFrame,
        residual_columns: Dict[str, Any],
        column_names: List[str]
    ) -> pd.DataFrame:
        """
        Align residual columns to dataframe indices and add them.
        
        Args:
            df: Target dataframe
            residual_columns: Dictionary of column_name -> residuals
            column_names: List of column names to add
            
        Returns:
            DataFrame with residual columns added
        """
        for col_name in column_names:
            if col_name not in residual_columns:
                continue
                
            residuals = residual_columns[col_name]
            
            try:
                if isinstance(residuals, pd.DataFrame):
                    # Handle DataFrame case
                    for col in residuals.columns:
                        df_col_name = f'{col_name}_{col}'
                        aligned_residuals = pd.Series(index=df.index, dtype=float)
                        if len(residuals) <= len(df):
                            aligned_residuals.iloc[:len(residuals)] = residuals[col].values
                            aligned_residuals.iloc[len(residuals):] = np.nan
                        else:
                            aligned_residuals = residuals[col].iloc[:len(df)]
                        df[df_col_name] = aligned_residuals
                        
                elif isinstance(residuals, pd.Series):
                    # Create aligned series
                    aligned_residuals = pd.Series(index=df.index, dtype=float)
                    if len(residuals) <= len(df):
                        aligned_residuals.iloc[:len(residuals)] = residuals.values
                        aligned_residuals.iloc[len(residuals):] = np.nan
                    else:
                        aligned_residuals = residuals.iloc[:len(df)]
                    df[col_name] = aligned_residuals
                    
                elif isinstance(residuals, np.ndarray):
                    # Handle numpy arrays
                    if len(residuals.shape) == 1:
                        aligned_residuals = pd.Series(index=df.index, dtype=float)
                        if len(residuals) <= len(df):
                            aligned_residuals.iloc[:len(residuals)] = residuals
                            aligned_residuals.iloc[len(residuals):] = np.nan
                        else:
                            aligned_residuals = pd.Series(residuals[:len(df)], index=df.index)
                        df[col_name] = aligned_residuals
                    else:
                        print(f"DEBUG: Warning - residuals for {col_name} is {residuals.shape}D array, skipping")
                        continue
                else:
                    # Convert to Series if not already
                    residuals_array = np.array(residuals)
                    if len(residuals_array.shape) == 1:
                        aligned_residuals = pd.Series(index=df.index, dtype=float)
                        if len(residuals_array) <= len(df):
                            aligned_residuals.iloc[:len(residuals_array)] = residuals_array
                            aligned_residuals.iloc[len(residuals_array):] = np.nan
                        else:
                            aligned_residuals = pd.Series(residuals_array[:len(df)], index=df.index)
                        df[col_name] = aligned_residuals
                    else:
                        print(f"DEBUG: Warning - residuals for {col_name} has shape {residuals_array.shape}, skipping")
                        continue
            except Exception as e:
                print(f"DEBUG: Error adding column {col_name}: {e}")
                import traceback
                print(traceback.format_exc())
                continue
        
        return df
    
    @staticmethod
    def save_dataframe(df: pd.DataFrame, file_path: str) -> None:
        """
        Save dataframe to file based on extension.
        
        Args:
            df: DataFrame to save
            file_path: Path to save the file
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ('.csv', ''):
            df.to_csv(file_path, index=False)
        elif file_ext == '.xlsx':
            df.to_excel(file_path, index=False)
        elif file_ext == '.xls':
            df.to_excel(file_path, index=False)
        elif file_ext == '.tsv':
            df.to_csv(file_path, sep='\t', index=False)
        elif file_ext == '.json':
            df.to_json(file_path, orient='records', indent=2)
        else:
            df.to_csv(file_path, index=False)



