# engine/dataprep/views.py
import os
import uuid
import json
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse
import pandas as pd
from pandas.api.types import CategoricalDtype

from engine.models import Dataset
from .loader import load_dataframe_any

PREVIEW_ROWS = 50

VAR_TYPES = [
    ("auto", "Auto"),
    ("numeric", "Numeric / Continuous"),
    ("binary", "Binary"),
    ("categorical", "Categorical"),
    ("ordinal", "Ordinal"),
    ("count", "Count (non-negative int)"),
]

def _dataset_path(ds: Dataset) -> str:
    return getattr(ds, "file_path", None) or getattr(getattr(ds, "file", None), "path", None)

def open_cleaner(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    
    try:
        # For large datasets, use efficient column loading and limited preview
        from engine.dataprep.loader import get_dataset_columns_only, load_dataframe_any
        
        # Get column names and types efficiently
        columns, column_types = get_dataset_columns_only(path)
        
        # Load only a small sample for preview and analysis
        MAX_PREVIEW_ROWS = 1000  # Limit preview to 1000 rows for large datasets
        df_sample, _ = load_dataframe_any(path, preview_rows=MAX_PREVIEW_ROWS)
        
    except Exception as e:
        return HttpResponse(f"Failed to read dataset: {e}", status=400, content_type="text/plain")
    
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
    
    # Create preview after schema detection
    df_preview = df_sample.head(PREVIEW_ROWS)
    
    # Use detected column types as default, then override with existing schema
    existing_types = column_types.copy()
    existing_orders = {}
    try:
        schema_path = os.path.splitext(path)[0] + ".schema.json"
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            # Override detected types with schema types if they exist
            existing_types.update(schema.get('types', {}))
            existing_orders = schema.get('orders', {})
    except Exception:
        pass
    # convert each row to a dict keyed by column name for rendering only
    def _to_str(v):
        try:
            import pandas as _pd
            if _pd.isna(v):
                return ""
        except Exception:
            pass
        return str(v)
    rows = [dict(zip(columns, (_to_str(v) for v in r))) for r in df_preview.itertuples(index=False, name=None)]
    
    # compute unique non-null values per column for ranking UI (stringified)
    # Use only sample data to avoid memory issues with large datasets
    uniques = {}
    for c in columns:
        try:
            vals = pd.Series(df_sample[c]).dropna().unique().tolist()
            uniques[c] = [str(v) for v in vals][:200]  # Limit to 200 unique values
        except Exception:
            uniques[c] = []
    
    # Add dataset size information for user awareness
    try:
        # Get total row count efficiently
        if path.endswith('.csv'):
            # For CSV, count lines efficiently
            with open(path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for line in f) - 1  # Subtract header
        else:
            # For other formats, load a small sample to estimate
            total_rows = len(df_sample)
    except Exception:
        total_rows = len(df_sample)
    
    ctx = {
        "dataset": dataset,
        "columns": columns,
        "columns_json": json.dumps(columns),
        "rows": rows,
        "var_types": VAR_TYPES,
        "all_str_cols": all_str_cols,
        "uniques_json": json.dumps(uniques),
        "existing_types": existing_types,
        "existing_orders": existing_orders,
        "total_rows": total_rows,
        "is_large_dataset": total_rows > 10000,
    }
    return render(request, "dataprep/cleaner.html", ctx)

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
    return df

def apply_cleaning(request, dataset_id: int):
    if request.method != "POST":
        return HttpResponse("POST only", status=405)

    ds = get_object_or_404(Dataset, pk=dataset_id)
    path = _dataset_path(ds)
    if not path:
        return HttpResponse("Dataset has no file path.", status=400)
    try:
        df, column_types = load_dataframe_any(path)
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

    def _write_dataframe(out_path: str, fmt: str | None):
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

    def _buffer_dataframe(fmt: str) -> tuple[bytes, str]:
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
            orig_ext = os.path.splitext(path)[1].lstrip(".")
            _write_dataframe(path, orig_ext)
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
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, _ = load_dataframe_any(path)
        
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
        def _write_dataframe(out_path: str, fmt: str | None):
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
        
        orig_ext = os.path.splitext(path)[1][1:]  # Get extension without dot
        _write_dataframe(path, orig_ext)
        
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
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, _ = load_dataframe_any(path)
        
        # Check if column name already exists
        if column_name in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' already exists"}), status=400, content_type="application/json")
        
        # Add statistical functions support
        from engine.views import add_statistical_functions
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
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, _ = load_dataframe_any(path)
        
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
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, column_types = load_dataframe_any(path)
        
        # Check if column exists
        if column_name not in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' not found"}), status=400, content_type="application/json")
        
        # Apply the mapping
        df[column_name] = df[column_name].map(value_mapping).fillna(df[column_name])
        
        # Save the updated dataset
        def _write_dataframe(out_path: str, fmt: str | None):
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
        
        orig_ext = os.path.splitext(path)[1][1:]
        _write_dataframe(path, orig_ext)
        
        return HttpResponse(json.dumps({
            "success": True,
            "message": f"Successfully recoded column '{column_name}'"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")

def merge_columns(request, dataset_id):
    """Apply merge columns operation."""
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, column_types = load_dataframe_any(path)
        
        # Check if column name already exists
        if column_name in df.columns:
            return HttpResponse(json.dumps({"error": f"Column '{column_name}' already exists"}), status=400, content_type="application/json")
        
        # Add statistical functions support
        from engine.views import add_statistical_functions
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
        def _write_dataframe(out_path: str, fmt: str | None):
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
        
        orig_ext = os.path.splitext(path)[1][1:]
        _write_dataframe(path, orig_ext)
        
        return HttpResponse(json.dumps({
            "success": True,
            "message": f"Successfully created column '{column_name}'"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")

def get_column_values(request, dataset_id):
    """Get unique values for a specific column."""
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, _ = load_dataframe_any(path)
        
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
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
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
        df, column_types = load_dataframe_any(path)
        
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
        def _write_dataframe(out_path: str, fmt: str | None):
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
        
        orig_ext = os.path.splitext(path)[1][1:]
        _write_dataframe(path, orig_ext)
        
        return HttpResponse(json.dumps({
            "success": True,
            "message": f"Successfully recoded column '{target_column}'"
        }), content_type="application/json")
        
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=500, content_type="application/json")


def drop_columns(request, dataset_id):
    """Drop selected columns from a dataset."""
    if request.method != "POST":
        return HttpResponse(json.dumps({"error": "Method not allowed"}), status=405, content_type="application/json")
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    path = _dataset_path(dataset)
    if not path:
        return HttpResponse(json.dumps({"error": "Dataset has no file path"}), status=400, content_type="application/json")
    
    try:
        # Load the dataset
        df, column_types = load_dataframe_any(path)
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
        def _write_dataframe(out_path: str, fmt: str | None):
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
        
        orig_ext = os.path.splitext(path)[1][1:]
        _write_dataframe(path, orig_ext)
        
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
