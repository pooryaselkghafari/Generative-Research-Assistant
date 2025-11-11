"""
Date detection and format conversion utilities
"""
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil import parser
import re
from typing import Dict, List, Tuple, Optional


# Common date format patterns
DATE_FORMATS = [
    # Year-Month-Day formats
    ('%Y-%m-%d', 'YYYY-MM-DD'),
    ('%Y/%m/%d', 'YYYY/MM/DD'),
    ('%Y.%m.%d', 'YYYY.MM.DD'),
    # Year-Day-Month formats
    ('%Y-%d-%m', 'YYYY-DD-MM'),
    ('%Y/%d/%m', 'YYYY/DD/MM'),
    ('%Y.%d.%m', 'YYYY.DD.MM'),
    # Month-Day-Year formats
    ('%m/%d/%Y', 'MM/DD/YYYY'),
    ('%m-%d-%Y', 'MM-DD-YYYY'),
    ('%d/%m/%Y', 'DD/MM/YYYY'),
    ('%d-%m-%Y', 'DD-MM-YYYY'),
    ('%d.%m.%Y', 'DD.MM.YYYY'),
    # Two-digit year formats
    ('%m/%d/%y', 'MM/DD/YY'),
    ('%m-%d-%y', 'MM-DD-YY'),
    ('%d/%m/%y', 'DD/MM/YY'),
    ('%d-%m-%y', 'DD-MM-YY'),
    ('%y-%d-%m', 'YY-DD-MM'),
    ('%y/%d/%m', 'YY/DD/MM'),
    # With time
    ('%Y-%m-%d %H:%M:%S', 'YYYY-MM-DD HH:MM:SS'),
    ('%Y/%m/%d %H:%M:%S', 'YYYY/MM/DD HH:MM:SS'),
    ('%Y-%d-%m %H:%M:%S', 'YYYY-DD-MM HH:MM:SS'),
    ('%Y/%d/%m %H:%M:%S', 'YYYY/DD/MM HH:MM:SS'),
    ('%m/%d/%Y %H:%M:%S', 'MM/DD/YYYY HH:MM:SS'),
    ('%d/%m/%Y %H:%M:%S', 'DD/MM/YYYY HH:MM:SS'),
    # ISO formats
    ('%Y-%m-%dT%H:%M:%S', 'ISO 8601 (YYYY-MM-DDTHH:MM:SS)'),
    ('%Y-%m-%dT%H:%M:%S.%f', 'ISO 8601 with microseconds'),
    # Text formats
    ('%B %d, %Y', 'Month DD, YYYY (e.g., January 15, 2024)'),
    ('%b %d, %Y', 'Mon DD, YYYY (e.g., Jan 15, 2024)'),
    ('%d %B %Y', 'DD Month YYYY (e.g., 15 January 2024)'),
    ('%d %b %Y', 'DD Mon YYYY (e.g., 15 Jan 2024)'),
]


def detect_date_formats(series: pd.Series, sample_size: int = 100) -> List[Dict[str, any]]:
    """
    Detect all possible date formats in a pandas Series.
    
    Returns a list of dictionaries with format information:
    [
        {
            'format': '%Y-%m-%d',
            'display': 'YYYY-MM-DD',
            'match_count': 50,
            'match_percentage': 50.0,
            'sample_dates': ['2024-01-15', '2024-02-20']
        },
        ...
    ]
    """
    if series.empty:
        return []
    
    # Get non-null values
    non_null = series.dropna()
    if len(non_null) == 0:
        return []
    
    # Sample for performance (if dataset is large)
    sample = non_null.head(sample_size) if len(non_null) > sample_size else non_null
    
    detected_formats = []
    
    # Try each format pattern
    for format_str, display_name in DATE_FORMATS:
        match_count = 0
        sample_dates = []
        
        for value in sample:
            try:
                # Convert to string if needed
                str_value = str(value).strip()
                if not str_value:
                    continue
                
                # Try parsing with the format
                parsed = datetime.strptime(str_value, format_str)
                match_count += 1
                if len(sample_dates) < 3:  # Keep first 3 examples
                    sample_dates.append(str_value)
            except (ValueError, TypeError):
                continue
        
        if match_count > 0:
            match_percentage = (match_count / len(sample)) * 100
            detected_formats.append({
                'format': format_str,
                'display': display_name,
                'match_count': match_count,
                'match_percentage': round(match_percentage, 1),
                'sample_dates': sample_dates
            })
    
    # Also try dateutil parser (flexible parsing)
    dateutil_matches = 0
    dateutil_samples = []
    for value in sample:
        try:
            str_value = str(value).strip()
            if not str_value:
                continue
            parsed = parser.parse(str_value, fuzzy=False)
            dateutil_matches += 1
            if len(dateutil_samples) < 3:
                dateutil_samples.append(str_value)
        except (ValueError, TypeError, parser.ParserError):
            continue
    
    if dateutil_matches > 0:
        dateutil_percentage = (dateutil_matches / len(sample)) * 100
        # Only add if it's better than any specific format
        if dateutil_percentage > 50 or not detected_formats:
            detected_formats.append({
                'format': 'dateutil',
                'display': 'Auto-detect (flexible)',
                'match_count': dateutil_matches,
                'match_percentage': round(dateutil_percentage, 1),
                'sample_dates': dateutil_samples
            })
    
    # Sort by match percentage (descending)
    detected_formats.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    return detected_formats


def is_date_column(series: pd.Series, threshold: float = 0.5) -> Tuple[bool, List[Dict]]:
    """
    Check if a column contains dates.
    
    Returns:
        (is_date, detected_formats)
    """
    if series.empty:
        return False, []
    
    non_null = series.dropna()
    if len(non_null) == 0:
        return False, []
    
    # Sample for performance
    sample_size = min(100, len(non_null))
    sample = non_null.head(sample_size)
    
    # Detect formats
    detected_formats = detect_date_formats(sample, sample_size=sample_size)
    
    if not detected_formats:
        return False, []
    
    # Check if the best format matches above threshold
    best_format = detected_formats[0]
    is_date = best_format['match_percentage'] >= (threshold * 100)
    
    return is_date, detected_formats


def convert_date_column(series: pd.Series, target_format: str, 
                        original_format: Optional[str] = None) -> pd.Series:
    """
    Convert a date column to a standardized format.
    
    Args:
        series: Pandas Series containing dates
        target_format: Target format string (e.g., '%Y-%m-%d')
        original_format: Original format (if known, 'dateutil' for auto-detect)
    
    Returns:
        Series with converted dates (as strings in target format)
    """
    result = pd.Series(index=series.index, dtype=object)
    
    for idx, value in series.items():
        if pd.isna(value):
            result[idx] = None
            continue
        
        try:
            str_value = str(value).strip()
            if not str_value:
                result[idx] = None
                continue
            
            # Try parsing with dateutil (flexible parsing)
            # First try without fuzzy to get exact matches
            try:
                parsed_date = parser.parse(str_value, fuzzy=False, dayfirst=False, yearfirst=True)
            except (ValueError, TypeError, parser.ParserError):
                # If that fails, try with fuzzy=True (more lenient, can extract dates from text)
                try:
                    parsed_date = parser.parse(str_value, fuzzy=True, dayfirst=False, yearfirst=True)
                except (ValueError, TypeError, parser.ParserError):
                    # Try with dayfirst=True (for DD/MM/YYYY formats)
                    try:
                        parsed_date = parser.parse(str_value, fuzzy=True, dayfirst=True, yearfirst=False)
                    except (ValueError, TypeError, parser.ParserError):
                        # Last resort: try to fix common issues like swapped values
                        # For dates like "2021-22-12", try interpreting as YYYY-DD-MM
                        parts = re.split(r'[-/.\s]+', str_value)
                        if len(parts) == 3:
                            try:
                                year = int(parts[0])
                                part2 = int(parts[1])
                                part3 = int(parts[2])
                                # If part2 > 12, it might be day, try YYYY-DD-MM
                                if part2 > 12 and part3 <= 12:
                                    # Interpret as YYYY-DD-MM
                                    parsed_date = datetime(year, part3, part2)
                                elif part3 > 12 and part2 <= 12:
                                    # Interpret as YYYY-MM-DD (normal)
                                    parsed_date = datetime(year, part2, part3)
                                else:
                                    # Try normal YYYY-MM-DD
                                    parsed_date = datetime(year, part2, part3)
                            except (ValueError, TypeError):
                                # If all parsing attempts fail, set to None
                                result[idx] = None
                                continue
                        else:
                            # If all parsing attempts fail, set to None
                            result[idx] = None
                            continue
            
            # Format to target format (the format the user selected)
            result[idx] = parsed_date.strftime(target_format)
            
        except (ValueError, TypeError, parser.ParserError) as e:
            # If all parsing fails, set to None instead of keeping invalid value
            result[idx] = None
    
    return result


def standardize_date_column(df: pd.DataFrame, column: str, 
                           target_format: str = '%Y-%m-%d',
                           original_format: Optional[str] = None) -> pd.DataFrame:
    """
    Standardize a date column in a DataFrame.
    
    Args:
        df: DataFrame
        column: Column name to convert
        target_format: Target format (default: '%Y-%m-%d')
        original_format: Original format (if known)
    
    Returns:
        DataFrame with converted column
    """
    df = df.copy()
    df[column] = convert_date_column(df[column], target_format, original_format)
    return df

