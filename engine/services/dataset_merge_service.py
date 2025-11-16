"""
Service for merging multiple datasets.

This service encapsulates logic for merging datasets based on common columns.
"""
import os
import uuid
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from django.conf import settings
from engine.models import Dataset
from data_prep.file_handling import _read_dataset_file


class DatasetMergeService:
    """Service for dataset merging operations."""
    
    @staticmethod
    def load_datasets(dataset_ids: List[int], user) -> Tuple[List[Dataset], List[pd.DataFrame], Optional[str]]:
        """
        Load datasets and their dataframes.
        
        Args:
            dataset_ids: List of dataset IDs
            user: User object for security check
            
        Returns:
            Tuple of (datasets_list, dataframes_list, error_message)
        """
        from django.shortcuts import get_object_or_404
        
        datasets = []
        dataframes = []
        
        for dataset_id in dataset_ids:
            try:
                # Security: Only allow access to user's own datasets
                dataset = get_object_or_404(Dataset, pk=dataset_id, user=user)
                datasets.append(dataset)
                
                # Read dataset file
                df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
                dataframes.append(df)
                
            except Exception as e:
                return None, None, f'Error loading dataset {dataset_id}: {str(e)}'
        
        return datasets, dataframes, None
    
    @staticmethod
    def validate_merge_columns(
        merged_df: pd.DataFrame,
        df: pd.DataFrame,
        merge_column_1: str,
        merge_column_2: str,
        dataset_name: str
    ) -> Optional[str]:
        """
        Validate merge columns exist and have compatible types.
        
        Args:
            merged_df: First dataframe
            df: Second dataframe
            merge_column_1: Column name in first dataframe
            merge_column_2: Column name in second dataframe
            dataset_name: Name of second dataset for error messages
            
        Returns:
            Error message if validation fails, None otherwise
        """
        # Check if merge columns exist
        if merge_column_1 not in merged_df.columns:
            return f'Column "{merge_column_1}" not found in first dataset'
        
        if merge_column_2 not in df.columns:
            return f'Column "{merge_column_2}" not found in dataset {dataset_name}'
        
        # Check data types before merging
        col1_type = str(merged_df[merge_column_1].dtype)
        col2_type = str(df[merge_column_2].dtype)
        
        if col1_type != col2_type:
            return (
                f'These two columns don\'t have common values. Column "{merge_column_1}" '
                f'has {col1_type} data type while column "{merge_column_2}" has {col2_type} '
                f'data type. Please select columns with the same data type.'
            )
        
        return None
    
    @staticmethod
    def perform_merge(
        dataframes: List[pd.DataFrame],
        merge_columns: List[Dict[str, str]],
        datasets: List[Dataset]
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Perform merge operation on multiple dataframes.
        
        Args:
            dataframes: List of dataframes to merge
            merge_columns: List of merge column dictionaries with 'column' key
            datasets: List of dataset objects for naming
            
        Returns:
            Tuple of (merged_dataframe, error_message)
        """
        # Start with the first dataset
        merged_df = dataframes[0].copy()
        merge_column_1 = merge_columns[0]['column']
        
        # Merge with each subsequent dataset
        for i in range(1, len(dataframes)):
            df = dataframes[i]
            merge_column_2 = merge_columns[i]['column']
            
            # Validate merge columns
            error = DatasetMergeService.validate_merge_columns(
                merged_df, df, merge_column_1, merge_column_2, datasets[i].name
            )
            if error:
                return None, error
            
            try:
                # Perform inner join
                merged_df = pd.merge(
                    merged_df, 
                    df, 
                    left_on=merge_column_1, 
                    right_on=merge_column_2, 
                    how='inner',
                    suffixes=('', f'_from_{datasets[i].name.replace(" ", "_")}')
                )
                
                # Remove duplicate merge columns (keep the first one)
                if merge_column_1 != merge_column_2:
                    merged_df = merged_df.drop(columns=[merge_column_2])
                    
            except Exception as e:
                error_msg = str(e)
                # Check for specific pandas merge errors
                if "int64" in error_msg and "object" in error_msg:
                    return None, (
                        'These two columns don\'t have common values. '
                        'Please select columns with the same data type.'
                    )
                else:
                    return None, f'Error merging datasets: {error_msg}'
        
        return merged_df, None
    
    @staticmethod
    def save_merged_dataset(merged_df: pd.DataFrame, datasets: List[Dataset], user) -> Dataset:
        """
        Save merged dataframe as a new dataset.
        
        Args:
            merged_df: Merged dataframe
            datasets: List of original datasets
            user: User object
            
        Returns:
            Created Dataset object
        """
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        merged_filename = f"merged_{unique_id}.csv"
        merged_file_path = os.path.join(settings.MEDIA_ROOT, merged_filename)
        
        # Save merged dataset
        merged_df.to_csv(merged_file_path, index=False)
        
        # Create dataset record
        merged_dataset = Dataset.objects.create(
            name=merged_filename,
            file_path=merged_file_path,
            user=user
        )
        
        # Generate dataset name
        dataset_names = [d.name for d in datasets]
        merged_dataset_name = f"merged_{'_'.join(dataset_names[:2])}"
        if len(dataset_names) > 2:
            merged_dataset_name += f"_and_{len(dataset_names)-2}_more"
        
        # Update dataset name
        merged_dataset.name = merged_dataset_name
        merged_dataset.save()
        
        return merged_dataset


