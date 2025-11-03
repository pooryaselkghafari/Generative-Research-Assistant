# engine/dataprep/loader.py
from pathlib import Path
import json
import pandas as pd

def _sanitize_columns_inplace(df: pd.DataFrame) -> None:
    def _clean(s):
        s = str(s)
        s = s.replace("\ufeff", "")  # BOM
        s = s.replace("\r", " ").replace("\n", " ")
        return s.strip()
    df.rename(columns=_clean, inplace=True)

def _auto_detect_column_types(df: pd.DataFrame) -> dict:
    """Automatically detect and assign data types to columns: numeric, binary, categorical, ordinal, or string."""
    column_types = {}
    
    for col in df.columns:
        # First check if it's binary (exactly 2 unique values) - this applies to ALL variables
        unique_values = df[col].dropna().nunique()
        if unique_values == 2:
            column_types[col] = 'binary'
            print(f"DEBUG: Auto-detected binary variable '{col}' with values: {df[col].dropna().unique().tolist()}")
            continue
            
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
                if unique_values <= 100:  # Reasonable threshold for categorical
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

def _read_csv_robust(path: str, *, encoding=None, nrows=None) -> pd.DataFrame:
    encodings = [encoding, "utf-8", "utf-8-sig", "cp1252", "latin-1", "utf-16", "utf-16le", "utf-16be"]
    seps = [",", ";", "\t", "|"]
    for enc in [e for e in encodings if e]:
        for sep in seps:
            try:
                df = pd.read_csv(
                    path, sep=sep, encoding=enc, engine="python",
                    on_bad_lines="skip", nrows=nrows
                )
                if df.shape[1] == 1:
                    try:
                        df2 = pd.read_csv(
                            path, sep=sep, encoding=enc, engine="python",
                            on_bad_lines="skip", header=None, nrows=nrows
                        )
                        if df2.shape[0] >= 1 and df2.iloc[0].map(lambda x: isinstance(x, str)).mean() > 0.5:
                            df2.columns = df2.iloc[0]
                            df2 = df2.iloc[1:].reset_index(drop=True)
                            return df2
                    except Exception:
                        pass
                return df
            except Exception:
                continue
    return pd.read_csv(path, engine="python", on_bad_lines="skip", nrows=nrows)

def _read_excel_robust(path: str, *, sheet=None, nrows=None) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=(sheet if sheet is not None else 0), nrows=nrows)
    except ImportError as ie:
        raise RuntimeError(
            "Reading Excel requires 'openpyxl' (for .xlsx/.xlsm) or 'xlrd' (legacy .xls). "
            "Install with: pip install openpyxl"
        ) from ie

def _read_json_robust(path: str, *, nrows=None) -> pd.DataFrame:
    try:
        df = pd.read_json(path, lines=True)
        if isinstance(df, pd.Series):
            df = df.to_frame()
        if nrows is not None:
            df = df.head(nrows)
        return df
    except Exception:
        pass
    try:
        df = pd.read_json(path)
        if isinstance(df, pd.Series):
            df = df.to_frame()
        if nrows is not None:
            df = df.head(nrows)
        return df
    except ValueError:
        import json
        rows = []
        with open(path, "rb") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return pd.DataFrame(data)
        elif isinstance(data, list):
            for item in data[: (nrows or len(data))]:
                rows.append(item)
            return pd.DataFrame(rows)
        else:
            raise

def get_dataset_columns_only(path: str, *, sheet=None) -> tuple[list, dict]:
    """Get only column names and types without loading the full dataset."""
    if not path:
        raise FileNotFoundError("Dataset path is empty.")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    ext = p.suffix.lower()
    if ext in {".csv", ".tsv", ".txt", ""}:
        # Read only first few rows to get column names and sample data for type detection
        df_sample = _read_csv_robust(path, nrows=1000)
    elif ext in {".xlsx", ".xls", ".xlsm"}:
        df_sample = _read_excel_robust(path, sheet=sheet, nrows=1000)
    elif ext in {".json", ".ndjson", ".jsonl"}:
        df_sample = _read_json_robust(path, nrows=1000)
    else:
        try:
            df_sample = _read_csv_robust(path, nrows=1000)
        except Exception:
            try:
                df_sample = _read_excel_robust(path, sheet=sheet, nrows=1000)
            except Exception:
                df_sample = _read_json_robust(path, nrows=1000)

    _sanitize_columns_inplace(df_sample)
    if df_sample.columns.duplicated().any():
        df_sample = df_sample.loc[:, ~df_sample.columns.duplicated()].copy()
    
    # Auto-detect column types using sample data
    detected_types = _auto_detect_column_types(df_sample)
    
    # Apply schema sidecar if present (types/orders)
    schema_path = str(Path(path).with_suffix('')) + '.schema.json'
    sp = Path(schema_path)
    if sp.exists():
        try:
            with open(sp, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            types = schema.get('types') or {}
            # Override detected types with schema types
            detected_types.update(types)
        except Exception:
            pass
    else:
        # If no schema exists, save the detected types to create a schema
        try:
            schema = {"types": detected_types, "orders": {}}
            with open(schema_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
            print(f"DEBUG: Created schema file with detected types: {detected_types}")
        except Exception as e:
            print(f"DEBUG: Failed to save schema: {e}")
    
    return list(df_sample.columns), detected_types

def load_dataframe_any(path: str, *, sheet=None, preview_rows=None) -> tuple[pd.DataFrame, dict]:
    if not path:
        raise FileNotFoundError("Dataset path is empty.")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    ext = p.suffix.lower()
    if ext in {".csv", ".tsv", ".txt", ""}:
        df = _read_csv_robust(path, nrows=preview_rows)
    elif ext in {".xlsx", ".xls", ".xlsm"}:
        df = _read_excel_robust(path, sheet=sheet, nrows=preview_rows)
    elif ext in {".json", ".ndjson", ".jsonl"}:
        df = _read_json_robust(path, nrows=preview_rows)
    else:
        try:
            df = _read_csv_robust(path, nrows=preview_rows)
        except Exception:
            try:
                df = _read_excel_robust(path, sheet=sheet, nrows=preview_rows)
            except Exception:
                df = _read_json_robust(path, nrows=preview_rows)

    _sanitize_columns_inplace(df)
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Auto-detect and assign column types
    detected_types = _auto_detect_column_types(df)
    
    # Apply schema sidecar if present (types/orders)
    try:
        schema_path = str(Path(path).with_suffix('')) + '.schema.json'
        sp = Path(schema_path)
        if sp.exists():
            with open(sp, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            types = schema.get('types') or {}
            orders = schema.get('orders') or {}
            from pandas.api.types import CategoricalDtype
            for col, t in types.items():
                if col not in df.columns:
                    continue
                t = (t or 'auto').lower()
                if t == 'numeric':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif t == 'count':
                    df[col] = pd.to_numeric(df[col], errors='coerce').round().astype('Int64')
                elif t == 'categorical' or t == 'binary':
                    df[col] = df[col].astype('category')
                elif t == 'ordinal':
                    order_str = orders.get(col) or ""
                    order = [x.strip() for x in order_str.split(",") if x.strip()] if order_str else []
                    # Replace categories not present in order with string versions to avoid empty-category errors
                    if order:
                        # Convert values not in order to strings so astype doesn't fail on unseen categories
                        mask = ~df[col].isin(order) & df[col].notna()
                        if mask.any():
                            df.loc[mask, col] = df.loc[mask, col].astype(str)
                        dtype = CategoricalDtype(categories=order, ordered=True)
                        df[col] = df[col].astype(dtype)
                    else:
                        # best-effort: infer order from uniques
                        cats = sorted(df[col].dropna().astype(str).unique().tolist())
                        dtype = CategoricalDtype(categories=cats, ordered=True)
                        df[col] = df[col].astype(dtype)
    except Exception:
        # best-effort; ignore schema errors
        pass
    
    # Merge detected types with schema types (schema takes precedence)
    final_types = detected_types.copy()
    if 'types' in locals():
        final_types.update(types)
    
    return df, final_types
