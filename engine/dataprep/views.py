# engine/dataprep/views.py
import os
import uuid
import json
import numpy as np
from typing import Optional, Tuple
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse, JsonResponse
import pandas as pd
from pandas.api.types import CategoricalDtype

from engine.models import Dataset
from .loader import load_dataframe_any
import sys
import os
import json
from django.http import JsonResponse

# Add parent directory to path to import date_detection
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from data_prep.date_detection import detect_date_formats, convert_date_column, standardize_date_column
from models.VARX import adf_check

INITIAL_PREVIEW_CHUNK = 200
METADATA_SAMPLE_LIMIT = 1000

VAR_TYPES = [
    ("auto", "Auto"),
    ("numeric", "Numeric / Continuous"),
    ("binary", "Binary"),
    ("categorical", "Categorical"),
    ("ordinal", "Ordinal"),
    ("count", "Count (non-negative int)"),
    ("date", "Date / Time"),
]

def _dataset_path(ds: Dataset) -> str:
    return getattr(ds, "file_path", None) or getattr(getattr(ds, "file", None), "path", None)

def _infer_dataset_format(path: str) -> str:
    """Return dataset format (csv, xlsx, etc.)."""
    if not path:
        return 'csv'
    base, ext = os.path.splitext(path)
    ext = (ext or '').lower().lstrip('.')
    return ext or 'csv'

def open_cleaner(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        from engine.dataprep.loader import get_dataset_columns_only, load_dataframe_any
        
        # Get column names and types efficiently
        columns, column_types = get_dataset_columns_only(path)
        
        # Load the full dataset so the editor can display every row
        df_full, _ = load_dataframe_any(path, preview_rows=None)
        total_rows = len(df_full)
        
        # Use a capped sample for type detection/uniques to avoid heavy operations
        if total_rows <= METADATA_SAMPLE_LIMIT:
            df_sample = df_full
        else:
            df_sample = df_full.head(METADATA_SAMPLE_LIMIT).copy()
        df_preview = df_full  # Entire dataset will be available in the UI
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Failed to read dataset: {e}"
        print(f"DEBUG: Error loading dataset editor for dataset_id={dataset_id}: {error_msg}")
        print(f"DEBUG: Traceback: {error_details}")
        # Provide more detailed error message for debugging
        response = HttpResponse(
            f"Failed to read dataset: {e}\n\n"
            f"If you recently added model residuals to this dataset, the file may need to be re-uploaded.\n"
            f"Error details: {error_msg}",
            status=400,
            content_type="text/plain"
        )
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    
    # detect columns whose non-null values are all strings (character columns)
    # but allow numeric for categorical/ordinal columns that can be converted back
    all_str_cols = {}
    for c in columns:
        s = pd.Series(df_sample[c]).dropna()
        is_categorical = hasattr(s.dtype, 'categories')  # is categorical/ordinal
        
        # Handle categorical data properly - convert to string first for type checking
        if is_categorical:
            # For categorical data, check if all values are strings
            s_str = s.astype(str)
            is_all_str = bool(len(s_str) > 0 and s_str.map(lambda v: isinstance(v, str)).all()) or (len(s_str) == 0)
        else:
            # For non-categorical data, check directly
            is_all_str = bool(len(s) > 0 and s.map(lambda v: isinstance(v, str)).all()) or (len(s) == 0)
        
        # Allow numeric for categorical columns (can be converted back) or if not all-string
        all_str_cols[c] = is_all_str and not is_categorical
    
    # Use detected column types as default, then override with existing schema
    existing_types = column_types.copy()
    existing_orders = {}
    
    # Load schema once for both type overrides and date standardization check
    schema_path = os.path.splitext(path)[0] + ".schema.json"
    standardized_dates = {}
    try:
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            # Override detected types with schema types if they exist
            existing_types.update(schema.get('types', {}))
            existing_orders = schema.get('orders', {})
            # Get standardized dates info
            standardized_dates = schema.get('date_standardized', {})
    except Exception:
        pass
    
    # Detect date columns with multiple formats
    # Skip columns that have already been standardized
    date_columns_with_formats = {}
    for col in columns:
        # Skip if this column has already been standardized
        if col in standardized_dates and standardized_dates[col].get('standardized', False):
            continue
            
        if column_types.get(col) == 'date':
            # Check for multiple date formats
            formats = detect_date_formats(df_sample[col], sample_size=100)
            if len(formats) > 1:
                # Multiple formats detected - user needs to choose
                date_columns_with_formats[col] = formats
    # convert each row to a dict keyed by column name for rendering only
    def _to_str(v):
        try:
            import pandas as _pd
            if _pd.isna(v):
                return ""
        except Exception:
            pass
        return str(v)
    rows_data = [dict(zip(columns, (_to_str(v) for v in r))) for r in df_preview.itertuples(index=False, name=None)]
    initial_rows = rows_data[:INITIAL_PREVIEW_CHUNK] if rows_data else []
    
    # compute unique non-null values per column for ranking UI (stringified)
    # Use only sample data to avoid memory issues with large datasets
    uniques = {}
    for c in columns:
        try:
            vals = pd.Series(df_sample[c]).dropna().unique().tolist()
            uniques[c] = [str(v) for v in vals][:200]  # Limit to 200 unique values
        except Exception:
            uniques[c] = []
    
    ctx = {
        "dataset": dataset,
        "columns": columns,
        "columns_json": json.dumps(columns),
        "rows_initial": initial_rows,
        "rows_data": rows_data,
        "var_types": VAR_TYPES,
        "all_str_cols": all_str_cols,
        "uniques_json": json.dumps(uniques),
        "existing_types": existing_types,
        "existing_orders": existing_orders,
        "total_rows": total_rows,
        "is_large_dataset": total_rows > 10000,
        "date_columns_with_formats_json": json.dumps(date_columns_with_formats),
        "row_chunk_size": INITIAL_PREVIEW_CHUNK,
    }
    response = render(request, "dataprep/cleaner.html", ctx)
    # Explicitly allow this view to be loaded in an iframe (for modal display)
    # This overrides any default X-Frame-Options from middleware
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response

def _make_unique(names):
    seen = {}
    out = []
    for n in names:
        base = n or "col"
        if base not in seen:
            seen[base] = 1
            out.append(base)
        else:
            seen[base] += 1
            out.append(f"{base}_{seen[base]}")
    return out

def _apply_types(df: pd.DataFrame, new_types: dict, orders: dict) -> pd.DataFrame:
    for col in df.columns:
        t = new_types.get(col, "auto")
        if t == "auto":
            continue
        if t == "numeric":
            # Convert categorical back to numeric if needed
            if hasattr(df[col].dtype, 'categories'):
                # Convert categorical to string first, then to numeric
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
                dtype = CategoricalDtype(categories=order, ordered=True)
                df[col] = df[col].astype(dtype)
        elif t == "count":
            # Convert categorical back to numeric if needed
            if hasattr(df[col].dtype, 'categories'):
                df[col] = df[col].astype(str)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            df[col] = df[col].clip(lower=0).round().astype("int64")
        elif t == "date":
            # Date columns are kept as strings in standardized format
            # Conversion to datetime objects can be done later if needed for analysis
            # For now, we just ensure they're strings
            if not pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].astype(str)
    return df

def apply_cleaning(request, dataset_id: int):
    if request.method != "POST":
        return HttpResponse("POST only", status=405)

    # Get dataset - no authentication required for local app
    ds = get_object_or_404(Dataset, pk=dataset_id)
    
    # Use user_id from dataset if available, otherwise None (local app)
    user_id = ds.user.id if ds.user else None
    
    path = _dataset_path(ds)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    try:
        df, column_types = load_dataframe_any(path, user_id=user_id)
    except Exception as e:
        return HttpResponse(f"Failed to read dataset: {e}", status=400, content_type="text/plain")

    # Expect arrays aligned to original columns:
    orig_cols = request.POST.getlist("orig[]")
    new_names = request.POST.getlist("name[]")
    types     = request.POST.getlist("type[]")
    orders    = request.POST.getlist("order[]")

    if not orig_cols or len(orig_cols) != len(df.columns):
        return HttpResponse("Column metadata mismatch.", status=400)

    # Build rename map
    proposed = [n.strip() if n.strip() else o for n, o in zip(new_names, orig_cols)]
    unique_names = _make_unique(proposed)
    rename_map = {o: n for o, n in zip(orig_cols, unique_names)}
    df.rename(columns=rename_map, inplace=True)

    # Build types & orders keyed by new name
    types_map  = {rename_map[o]: (t or "auto") for o, t in zip(orig_cols, types)}
    orders_map = {rename_map[o]: (ordr or "")  for o, ordr in zip(orig_cols, orders)}

    # Apply dtype conversions
    df = _apply_types(df, types_map, orders_map)

    # Determine save behavior
    save_mode = request.POST.get("save_mode", "new")  # 'overwrite', 'new', or 'download'
    save_format = request.POST.get("save_format")  # csv, xlsx, tsv, json
    save_name = (request.POST.get("save_name") or "").strip()
    ajax = request.POST.get("ajax") == "1"

    def _write_dataframe(out_path: str, fmt: Optional[str]):
        ext = (fmt or os.path.splitext(out_path)[1].lstrip(".")).lower()
        if ext in ("csv", ""):  # default
            df.to_csv(out_path, index=False)
        elif ext in ("xlsx", "xls"):  # excel
            try:
                df.to_excel(out_path, index=False)
            except Exception as e:
                raise RuntimeError(f"Excel write failed: {e}")
        elif ext == "tsv":
            df.to_csv(out_path, index=False, sep="\t")
        elif ext == "json":
            df.to_json(out_path, orient="records")
        else:
            df.to_csv(out_path, index=False)

    def _buffer_dataframe(fmt: str) -> Tuple[bytes, str]:
        import io
        ext = (fmt or 'csv').lower()
        buf = io.BytesIO()
        if ext == 'csv':
            buf.write(df.to_csv(index=False).encode('utf-8'))
            mime = 'text/csv'
        elif ext == 'tsv':
            buf.write(df.to_csv(index=False, sep='\t').encode('utf-8'))
            mime = 'text/tab-separated-values'
        elif ext in ('xlsx', 'xls'):
            try:
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            except Exception as e:
                raise RuntimeError(f"Excel write failed: {e}")
        elif ext == 'json':
            buf.write(df.to_json(orient='records').encode('utf-8'))
            mime = 'application/json'
        else:
            buf.write(df.to_csv(index=False).encode('utf-8'))
            mime = 'text/csv'
        buf.seek(0)
        return buf.read(), mime

    if save_mode == "overwrite" and path:
        # Overwrite original file using its extension
        try:
            from engine.encrypted_storage import is_encrypted_file, save_encrypted_dataframe
            file_format = _infer_dataset_format(path)
            
            if is_encrypted_file(path):
                save_encrypted_dataframe(df, path, user_id=user_id, file_format=file_format)
            else:
                _write_dataframe(path, file_format)
            # save schema sidecar next to original file
            schema = {"types": types_map, "orders": orders_map}
            schema_path = os.path.splitext(path)[0] + ".schema.json"
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return HttpResponse(f"Failed to save: {e}", status=400, content_type="text/plain")
        if ajax:
            return HttpResponse("OK", content_type="text/plain")
        return redirect("index")

    if save_mode == "download":
        fmt = (save_format or "csv").lower()
        try:
            data, mime = _buffer_dataframe(fmt)
        except Exception as e:
            return HttpResponse(f"Failed to prepare download: {e}", status=400, content_type="text/plain")
        def _sanitize_name(n: str) -> str:
            keep = [c if c.isalnum() or c in ('-', '_') else '_' for c in n]
            s = ''.join(keep).strip('_')
            return s or 'dataset'
        base_name = _sanitize_name(save_name) if save_name else f"{_sanitize_name(ds.name)}_cleaned"
        filename = f"{base_name}.{fmt if fmt in ('csv','xlsx','xls','tsv','json') else 'csv'}"
        resp = HttpResponse(data, content_type=mime)
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    # Save as: choose format and register new dataset
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    outdir = os.path.join(settings.MEDIA_ROOT, "datasets")
    os.makedirs(outdir, exist_ok=True)
    slug = str(uuid.uuid4())[:8]
    fmt = (save_format or "csv").lower()
    ext = fmt if fmt in ("csv", "xlsx", "xls", "tsv", "json") else "csv"
    # Build output name
    def _sanitize_name(n: str) -> str:
        keep = [c if c.isalnum() or c in ('-', '_') else '_' for c in n]
        s = ''.join(keep).strip('_')
        return s or 'dataset'
    base_name = _sanitize_name(save_name) if save_name else f"{_sanitize_name(ds.name)}_cleaned"
    outname = f"{slug}_{base_name}.{ext}"
    outpath = os.path.join(outdir, outname)
    try:
        _write_dataframe(outpath, ext)
        # save schema sidecar
        schema = {"types": types_map, "orders": orders_map}
        schema_path = os.path.splitext(outpath)[0] + ".schema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return HttpResponse(f"Failed to save: {e}", status=400, content_type="text/plain")

    from engine.models import Dataset as DatasetModel
    DatasetModel.objects.create(name=f"{ds.name} (cleaned)", file_path=outpath)

    if ajax:
        return HttpResponse("OK", content_type="text/plain")
    return redirect("index")

def normalize_columns(request, dataset_id):
    """Normalize selected numeric columns in a dataset."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        columns = data.get('columns', [])
        method = data.get('method', 'min_max')
        
        if not columns:
            return HttpResponse(json.dumps({"error": "No columns selected"}), 
                              status=400, content_type="application/json")
        
        # Load the full dataset
        df, _ = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if columns exist and are numeric
        missing_cols = [col for col in columns if col not in df.columns]
        if missing_cols:
            return HttpResponse(json.dumps({"error": f"Columns not found: {missing_cols}"}), 
                              status=400, content_type="application/json")
        
        # Apply normalization to each column
        normalized_columns = []
        for col in columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue  # Skip non-numeric columns
            
            # Create normalized column name
            method_suffix = {
                'min_max': 'min_max',
                'mean_center': 'mean_center', 
                'standardize': 'standardize'
            }.get(method, 'min_max')
            
            new_col_name = f"{col}_normalized_{method_suffix}"
            
            # Apply normalization
            if method == 'min_max':
                # Min-Max normalization (0-1)
                col_min = df[col].min()
                col_max = df[col].max()
                if col_max != col_min:
                    df[new_col_name] = (df[col] - col_min) / (col_max - col_min)
                else:
                    df[new_col_name] = 0.5  # If all values are the same
                    
            elif method == 'mean_center':
                # Mean centering
                col_mean = df[col].mean()
                df[new_col_name] = df[col] - col_mean
                
            elif method == 'standardize':
                # Z-score standardization
                col_mean = df[col].mean()
                col_std = df[col].std()
                if col_std != 0:
                    df[new_col_name] = (df[col] - col_mean) / col_std
                else:
                    df[new_col_name] = 0  # If std is 0, all values are the same
            
            normalized_columns.append(new_col_name)
        
        # Save the updated dataset
        def _write_dataframe(out_path: str, fmt: Optional[str]):
            ext = (fmt or os.path.splitext(out_path)[1].lstrip(".")).lower()
            if ext in ("csv", ""):  # default
                df.to_csv(out_path, index=False)
            elif ext == "xlsx":
                df.to_excel(out_path, index=False)
            elif ext == "xls":
                df.to_excel(out_path, index=False)
            elif ext == "tsv":
                df.to_csv(out_path, sep="\t", index=False)
            elif ext == "json":
                df.to_json(out_path, orient="records", indent=2)
            else:
                df.to_csv(out_path, index=False)
        
        file_format = _infer_dataset_format(path)
        _write_dataframe(path, file_format)
        
        return HttpResponse(json.dumps({
            "success": True,
            "normalized_columns": normalized_columns,
            "message": f"Successfully normalized {len(normalized_columns)} columns"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), 
                          status=500, content_type="application/json")

def merge_columns_preview(request, dataset_id):
    """Preview merge columns operation."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        column_name = data.get('column_name', '').strip()
        formula = data.get('formula', '').strip()
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name is required"}), status=400, content_type="application/json")
        
        if not formula:
            return HttpResponse(json.dumps({"error": "Formula is required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, _ = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if column name already exists
        if column_name in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' already exists"}), status=400, content_type="application/json")
        
        # Add statistical functions support
        from data_prep.cleaning import add_statistical_functions
        formula_with_functions = add_statistical_functions(df, formula)
        
        # Try to evaluate the formula
        try:
            new_column = df.eval(formula_with_functions)
        except Exception as e:
            error_msg = str(e)
            if "name" in error_msg and "is not defined" in error_msg:
                return HttpResponse(json.dumps({"error": f"Column name not found in formula: {error_msg}"}), status=400, content_type="application/json")
            else:
                return HttpResponse(json.dumps({"error": f"Invalid formula: {error_msg}"}), status=400, content_type="application/json")
        
        # Create preview data (first 10 rows)
        preview_df = df.head(10).copy()
        preview_df[column_name] = new_column.head(10)
        
        # Generate HTML table
        preview_html = preview_df.to_html(classes="table", table_id="preview-table", escape=False, index=False)
        
        return HttpResponse(json.dumps({
            "success": True,
            "row_count": len(df),
            "preview_html": preview_html
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")

def get_column_values(request, dataset_id):
    """Get unique values for a specific column."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        column_name = data.get('column_name', '').strip()
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name is required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, _ = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if column exists
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Get unique values (excluding NaN)
        unique_values = df[column_name].dropna().unique().tolist()
        
        # Convert to strings and sort
        unique_values = sorted([str(v) for v in unique_values])
        
        return HttpResponse(json.dumps({
            "success": True,
            "column_name": column_name,
            "unique_values": unique_values,
            "count": len(unique_values)
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")

def apply_column_coding(request, dataset_id):
    """Apply column coding/recoding."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        column_name = data.get('column_name', '').strip()
        value_mapping = data.get('value_mapping', {})
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name is required"}), status=400, content_type="application/json")
        
        if not value_mapping:
            return HttpResponse(json.dumps({"error": "Value mapping is required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, column_types = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if column exists
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Apply the mapping
        df[column_name] = df[column_name].map(value_mapping).fillna(df[column_name])
        
        # Save the updated dataset
        def _write_dataframe(out_path: str, fmt: Optional[str]):
            ext = (fmt or os.path.splitext(out_path)[1].lstrip(".")).lower()
            if ext in ("csv", ""):
                df.to_csv(out_path, index=False)
            elif ext in ("xlsx", "xls"):
                df.to_excel(out_path, index=False)
            elif ext == "tsv":
                df.to_csv(out_path, index=False, sep="\t")
            elif ext == "json":
                df.to_json(out_path, orient="records")
            else:
                df.to_csv(out_path, index=False)
        
        file_format = _infer_dataset_format(path)
        _write_dataframe(path, file_format)
        
        return HttpResponse(json.dumps({
            "success": True,
            "message": f"Successfully recoded column '{column_name}'"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")

def merge_columns(request, dataset_id):
    """Apply merge columns operation."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        column_name = data.get('column_name', '').strip()
        formula = data.get('formula', '').strip()
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name is required"}), status=400, content_type="application/json")
        
        if not formula:
            return HttpResponse(json.dumps({"error": "Formula is required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, column_types = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if column name already exists
        if column_name in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' already exists"}), status=400, content_type="application/json")
        
        # Add statistical functions support
        from data_prep.cleaning import add_statistical_functions
        formula_with_functions = add_statistical_functions(df, formula)
        
        # Try to evaluate the formula
        try:
            new_column = df.eval(formula_with_functions)
        except Exception as e:
            error_msg = str(e)
            if "name" in error_msg and "is not defined" in error_msg:
                return HttpResponse(json.dumps({"error": f"Column name not found in formula: {error_msg}"}), status=400, content_type="application/json")
            else:
                return HttpResponse(json.dumps({"error": f"Invalid formula: {error_msg}"}), status=400, content_type="application/json")
        
        # Add the new column to the dataframe
        df[column_name] = new_column
        
        # Save the updated dataset
        def _write_dataframe(out_path: str, fmt: Optional[str]):
            ext = (fmt or os.path.splitext(out_path)[1].lstrip(".")).lower()
            if ext in ("csv", ""):
                df.to_csv(out_path, index=False)
            elif ext in ("xlsx", "xls"):
                df.to_excel(out_path, index=False)
            elif ext == "tsv":
                df.to_csv(out_path, index=False, sep="\t")
            elif ext == "json":
                df.to_json(out_path, orient="records")
            else:
                df.to_csv(out_path, index=False)
        
        file_format = _infer_dataset_format(path)
        _write_dataframe(path, file_format)
        
        return HttpResponse(json.dumps({
            "success": True,
            "message": f"Successfully created column '{column_name}'"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")

def get_column_values(request, dataset_id):
    """Get unique values for a specific column."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        column_name = data.get('column_name', '').strip()
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name is required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, _ = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if column exists
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Get unique values (excluding NaN)
        unique_values = df[column_name].dropna().unique().tolist()
        
        # Convert to strings and sort
        unique_values = sorted([str(v) for v in unique_values])
        
        return HttpResponse(json.dumps({
            "success": True,
            "column_name": column_name,
            "unique_values": unique_values,
            "count": len(unique_values)
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")


def apply_column_coding(request, dataset_id):
    """Apply column coding/recoding."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        import json
        data = json.loads(request.body)
        column_name = data.get('column_name', '').strip()
        value_mapping = data.get('value_mapping', {})
        coding_mode = data.get('coding_mode', 'replace')
        new_column_name = data.get('new_column_name', '').strip()
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name is required"}), status=400, content_type="application/json")
        
        if not value_mapping:
            return HttpResponse(json.dumps({"error": "Value mapping is required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, column_types = load_dataframe_any(path, user_id=request.user.id)
        
        # Check if column exists
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Handle new column creation
        if coding_mode == 'new':
            if not new_column_name:
                return HttpResponse(json.dumps({"error": "New column name is required when creating a new column"}), status=400, content_type="application/json")
            
            # Check if new column name already exists
            if new_column_name in df.columns:
                return HttpResponse(json.dumps({"error": f"Column '{new_column_name}' already exists"}), status=400, content_type="application/json")
            
            # Create new column with mapped values
            df[new_column_name] = df[column_name].map(value_mapping).fillna(df[column_name])
            target_column = new_column_name
        else:
            # Replace original column
            df[column_name] = df[column_name].map(value_mapping).fillna(df[column_name])
            target_column = column_name
        
        # Save the updated dataset
        def _write_dataframe(out_path: str, fmt: Optional[str]):
            ext = (fmt or os.path.splitext(out_path)[1].lstrip(".")).lower()
            if ext in ("csv", ""):
                df.to_csv(out_path, index=False)
            elif ext in ("xlsx", "xls"):
                df.to_excel(out_path, index=False)
            elif ext == "tsv":
                df.to_csv(out_path, index=False, sep="\t")
            elif ext == "json":
                df.to_json(out_path, orient="records")
            else:
                df.to_csv(out_path, index=False)
        
        file_format = _infer_dataset_format(path)
        _write_dataframe(path, file_format)
        
        return HttpResponse(json.dumps({
            "success": True,
            "message": f"Successfully recoded column '{target_column}'"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")


def drop_columns(request, dataset_id):
    """Drop selected columns from a dataset."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != "POST":
        return HttpResponse(json.dumps({"error": "Method not allowed"}), status=405, content_type="application/json")

    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse(json.dumps({"error": "Dataset has no file path"}), status=400, content_type="application/json")
    
    try:
        # Load the dataset
        df, column_types = load_dataframe_any(path, user_id=request.user.id)
        original_column_count = len(df.columns)
        
        # Get columns to drop from request
        data = json.loads(request.body)
        columns_to_drop = data.get('columns', [])
        
        if not columns_to_drop:
            return HttpResponse(json.dumps({"error": "No columns specified"}), status=400, content_type="application/json")
        
        # Validate that all columns exist
        missing_columns = [col for col in columns_to_drop if col not in df.columns]
        if missing_columns:
            return HttpResponse(json.dumps({"error": f"Columns not found: {', '.join(missing_columns)}"}), status=400, content_type="application/json")
        
        # Drop the columns
        df = df.drop(columns=columns_to_drop)
        
        if len(df.columns) == 0:
            return HttpResponse(json.dumps({"error": "Cannot drop all columns. At least one column must remain."}), status=400, content_type="application/json")
        
        # Save the updated dataset
        def _write_dataframe(out_path: str, fmt: Optional[str]):
            ext = (fmt or os.path.splitext(out_path)[1].lstrip(".")).lower()
            if ext in ("csv", ""):
                df.to_csv(out_path, index=False)
            elif ext in ("xlsx", "xls"):
                df.to_excel(out_path, index=False)
            elif ext == "tsv":
                df.to_csv(out_path, index=False, sep="\t")
            elif ext == "json":
                df.to_json(out_path, orient="records")
            else:
                df.to_csv(out_path, index=False)
        
        file_format = _infer_dataset_format(path)
        _write_dataframe(path, file_format)
        
        return HttpResponse(json.dumps({
            "success": True,
            "columns_dropped": len(columns_to_drop),
            "columns_remaining": len(df.columns),
            "message": f"Successfully dropped {len(columns_to_drop)} column(s)"
        }), content_type="application/json")
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return HttpResponse(json.dumps({"error": f"Failed to drop columns: {error_msg}"}), status=500, content_type="application/json")


def detect_date_formats_api(request, dataset_id):
    """API endpoint to detect date formats in a specific column."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)

    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse(json.dumps({"error": "Dataset has no file path"}), status=400, content_type="application/json")
    
    try:
        import json as json_module
        data = json_module.loads(request.body)
        column_name = data.get('column')
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name required"}), status=400, content_type="application/json")
        
        # Load dataset
        df, _ = load_dataframe_any(path, preview_rows=1000, user_id=request.user.id)
        
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Detect date formats
        formats = detect_date_formats(df[column_name], sample_size=100)
        
        return HttpResponse(json.dumps({
            "success": True,
            "column": column_name,
            "formats": formats
        }), content_type="application/json")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")


def convert_date_format_api(request, dataset_id):
    """API endpoint to convert a date column to a selected format."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)

    # Security: Only allow access to user's own datasets
    dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse(json.dumps({"error": "Dataset has no file path"}), status=400, content_type="application/json")
    
    try:
        import json as json_module
        data = json_module.loads(request.body)
        column_name = data.get('column')
        target_format = data.get('target_format')
        original_format = data.get('original_format')  # The format user selected (for reference)
        
        # The target_format should be the format the user wants to convert TO
        # If not provided, use the selected format (unless it's 'dateutil', then use YYYY-MM-DD)
        if not target_format:
            if original_format and original_format != 'dateutil':
                target_format = original_format
            else:
                target_format = '%Y-%m-%d'
        
        # Log for debugging
        print(f"DEBUG: Converting date column '{column_name}' to format '{target_format}' (selected: {original_format})")
        
        # For parsing, we should use dateutil since dates might be in different formats
        # The original_format is just for reference - we'll parse flexibly
        parse_format = 'dateutil'  # Always use flexible parsing since dates are mixed
        
        if not column_name:
            return HttpResponse(json.dumps({"error": "Column name required"}), status=400, content_type="application/json")
        
        # Load full dataset
        df, _ = load_dataframe_any(path, user_id=request.user.id)
        
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Store original sample for verification
        original_sample = df[column_name].head(10).tolist()
        
        # Convert date column
        # Use dateutil for parsing (since dates are in mixed formats)
        # Then convert all to the selected target format
        df = standardize_date_column(df, column_name, target_format, 'dateutil')
        
        # Verify conversion (check a few values)
        converted_sample = df[column_name].head(10).tolist()
        
        # Save the updated dataset
        file_format = _infer_dataset_format(path)
        
        if file_format in ("csv", ""):
            df.to_csv(path, index=False)
        elif file_format in ("xlsx", "xls"):
            df.to_excel(path, index=False, engine='openpyxl')
        elif file_format == "tsv":
            df.to_csv(path, index=False, sep="\t")
        elif file_format == "json":
            df.to_json(path, orient="records")
        else:
            df.to_csv(path, index=False)
        
        # Update schema to mark this column as date (standardized)
        # This prevents the modal from showing again
        schema_path = os.path.splitext(path)[0] + ".schema.json"
        schema = {}
        try:
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json_module.load(f)
        except Exception:
            pass
        
        # Ensure types dict exists
        if 'types' not in schema:
            schema['types'] = {}
        
        # Mark column as date type (standardized)
        schema['types'][column_name] = 'date'
        
        # Store metadata that this column has been standardized
        if 'date_standardized' not in schema:
            schema['date_standardized'] = {}
        schema['date_standardized'][column_name] = {
            'original_format': original_format,
            'target_format': target_format,
            'standardized': True,
            'standardized_to': target_format  # Store the format we converted to
        }
        
        # Save updated schema
        try:
            with open(schema_path, 'w', encoding='utf-8') as f:
                json_module.dump(schema, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Log but don't fail if schema update fails
            print(f"Warning: Failed to update schema: {e}")
        
        return HttpResponse(json.dumps({
            "success": True,
            "column": column_name,
            "target_format": target_format,
            "message": f"Successfully converted '{column_name}' to format {target_format}",
            "original_sample": [str(v) for v in original_sample[:3]],
            "converted_sample": [str(v) for v in converted_sample[:3]]
        }), content_type="application/json")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")


def fix_stationary(request, dataset_id):
    """API endpoint to fix stationarity by applying transformation (diff or log) to a variable."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        import json as json_module
        data = json_module.loads(request.body)
        variable_name = data.get('variable')
        transform_type = data.get('transform_type', 'diff')  # 'diff' or 'log'
        
        if not variable_name:
            return JsonResponse({'error': 'Variable name required'}, status=400)
        
        if transform_type not in ['diff', 'log']:
            return JsonResponse({'error': 'Transform type must be "diff" or "log"'}, status=400)
        
        # Get dataset - no authentication required for local app
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        
        # Use user_id from dataset if available, otherwise None (local app)
        user_id = dataset.user.id if dataset.user else None
        
        path = _dataset_path(dataset)
        if not path:
            return JsonResponse({'error': 'Dataset has no file path'}, status=400)
        
        # Load dataset
        df, _ = load_dataframe_any(path, user_id=user_id)
        
        if variable_name not in df.columns:
            return JsonResponse({'error': f'Variable "{variable_name}" not found in dataset'}, status=400)
        
        # Determine new column name
        new_column_name = f'{variable_name}_stationary'
        
        # Check if column already exists (for overwriting)
        column_exists = new_column_name in df.columns
        
        # Apply transformation
        if transform_type == 'diff':
            # First difference: ΔX = X(t) - X(t-1)
            df[new_column_name] = df[variable_name].diff()
            # First value will be NaN, we can keep it or fill with 0
            # For VARX, it's better to keep NaN and drop it later
        elif transform_type == 'log':
            # Log transformation: log(X)
            # Check if any values are negative
            if (df[variable_name] < 0).any():
                negative_count = (df[variable_name] < 0).sum()
                return JsonResponse({
                    'error': f'Cannot apply log transformation: variable "{variable_name}" contains {negative_count} negative value(s). Log transformation requires all values to be non-negative. Please use difference transformation instead or remove negative values from your data.'
                }, status=400)
            
            # Check if any values are zero
            if (df[variable_name] == 0).any():
                zero_count = (df[variable_name] == 0).sum()
                # Add a small number (epsilon) to avoid log(0) error
                # Use a very small value relative to the data scale
                epsilon = 1e-10
                # Add epsilon to all values to shift them slightly
                df[new_column_name] = np.log(df[variable_name] + epsilon)
                # Warn user about the adjustment (this will be in the response message)
            else:
                # All values are positive, can apply log directly
                df[new_column_name] = np.log(df[variable_name])
        
        # Save updated dataset
        # Check if file is encrypted and handle accordingly
        from engine.encrypted_storage import is_encrypted_file, save_encrypted_dataframe
        
        file_format = _infer_dataset_format(path)
        
        if is_encrypted_file(path):
            # File is encrypted - use encrypted save function
            save_encrypted_dataframe(df, path, user_id=user_id, file_format=file_format)
        else:
            # File is not encrypted - save directly
            if file_format in ("csv", ""):
                df.to_csv(path, index=False)
            elif file_format in ("xlsx", "xls"):
                df.to_excel(path, index=False, engine='openpyxl')
            elif file_format == "tsv":
                df.to_csv(path, index=False, sep="\t")
            elif file_format == "json":
                df.to_json(path, orient="records")
            else:
                df.to_csv(path, index=False)
        
        # Re-run ADF test on the new column
        adf_result = adf_check(df[new_column_name], new_column_name)
        
        # Prepare response
        message = f'Transformation applied successfully. '
        if column_exists:
            message += f'Column "{new_column_name}" was overwritten. '
        else:
            message += f'New column "{new_column_name}" was created. '
        
        # Add warning about zero values if log transformation was used
        if transform_type == 'log' and (df[variable_name] == 0).any():
            zero_count = (df[variable_name] == 0).sum()
            message += f'Note: Variable contained {zero_count} zero value(s). Added small epsilon (1e-10) before log transformation to avoid log(0) error. '
        
        message += f'ADF test on transformed variable: '
        if adf_result.get('is_stationary'):
            p_val = adf_result.get('p_value')
            if p_val is not None and isinstance(p_val, (int, float)):
                message += f'Stationary (p-value: {p_val:.6f})'
            else:
                message += f'Stationary (p-value: N/A)'
        else:
            p_val = adf_result.get('p_value')
            if p_val is not None and isinstance(p_val, (int, float)):
                message += f'Non-stationary (p-value: {p_val:.6f}). You may need to apply another transformation.'
            else:
                message += f'Non-stationary (p-value: N/A). You may need to apply another transformation.'
        
        # Convert adf_result to JSON-serializable format
        # Handle numpy bool types and ensure all values are JSON-serializable
        import json as json_lib
        adf_result_serializable = {}
        for key, value in adf_result.items():
            if value is None:
                adf_result_serializable[key] = None
            elif isinstance(value, bool):
                # Python bool - JsonResponse handles this fine
                adf_result_serializable[key] = value
            elif hasattr(value, 'item'):  # numpy scalar types
                # Convert numpy scalar to Python native type
                adf_result_serializable[key] = value.item()
            elif isinstance(value, (int, float)):
                adf_result_serializable[key] = value
            else:
                adf_result_serializable[key] = str(value)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'variable': variable_name,
            'new_column': new_column_name,
            'transform_type': transform_type,
            'adf_result': adf_result_serializable
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
