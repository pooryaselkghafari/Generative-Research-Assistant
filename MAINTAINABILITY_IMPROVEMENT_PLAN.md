# Maintainability Index Improvement Plan
## Target: 80%+ MI (Current: 63.0%)

### Current State Analysis

| Module | Lines | Functions | CF | Avg Func Size | MI | Priority |
|--------|-------|-----------|----|---------------|----|-----------| 
| visualization.py | 678 | 6 | 192 | 113.0 | **44.6** | 🔴 **CRITICAL** |
| datasets.py | 544 | 7 | 114 | 77.7 | **62.2** | 🟡 **HIGH** |
| analysis.py | 689 | 10 | 119 | 68.9 | **60.5** | 🟡 **HIGH** |
| analysis_helpers.py | 459 | 9 | 111 | 51.0 | **69.5** | 🟢 **MEDIUM** |
| pages.py | 220 | 6 | 33 | 36.7 | **85.0** | ✅ Good |
| sessions.py | 179 | 6 | 40 | 29.8 | **86.5** | ✅ Good |
| decorators.py | 76 | 3 | 10 | 25.3 | **92.4** | ✅ Excellent |
| utils.py | 14 | 1 | 1 | 14.0 | **96.8** | ✅ Excellent |

**Overall Weighted Average MI: 63.0/100**
**Target: 80.0/100**
**Gap: 17.0 points**

---

## Improvement Recommendations

### 🔴 Priority 1: Refactor `visualization.py` (MI: 44.6 → Target: 70+)

**Current Issues:**
- 678 lines with only 6 functions (avg 113 lines per function!)
- 192 control flow statements (very high complexity)
- `generate_spotlight_plot()` is likely 200+ lines

**Action Plan:**

1. **Extract spotlight plot generation logic:**
   - Create `engine/services/spotlight_service.py`
   - Move ordinal/multinomial prediction logic to service
   - Extract plot configuration to separate functions

2. **Break down `generate_spotlight_plot()`:**
   ```python
   # Current: One massive function
   def generate_spotlight_plot(request, session_id):
       # 200+ lines of code
   
   # Target: Multiple focused functions
   def generate_spotlight_plot(request, session_id):
       # Main orchestration (20-30 lines)
   
   def _load_fitted_model(session):
       # Model loading logic (15-20 lines)
   
   def _prepare_spotlight_options(request, session):
       # Options preparation (20-30 lines)
   
   def _generate_ordinal_spotlight(fitted_model, df, interaction, options):
       # Ordinal-specific logic (30-40 lines)
   
   def _generate_multinomial_spotlight(fitted_model, df, interaction, options):
       # Multinomial-specific logic (30-40 lines)
   
   def _generate_standard_spotlight(fitted_model, df, interaction, options):
       # Standard regression logic (30-40 lines)
   ```

3. **Extract correlation heatmap logic:**
   - Move to `engine/services/visualization_service.py`
   - Separate data preparation from plot generation

4. **Extract ANOVA plot logic:**
   - Move to `engine/services/anova_visualization_service.py`

**Expected Impact:**
- Reduce from 6 functions to 15-20 functions
- Reduce average function size from 113 to ~35 lines
- Reduce control flow by extracting to smaller functions
- **Target MI: 70+**

---

### 🟡 Priority 2: Refactor `datasets.py` (MI: 62.2 → Target: 75+)

**Current Issues:**
- 544 lines with 7 functions (avg 77.7 lines per function)
- 114 control flow statements
- `upload_dataset()`, `merge_datasets()`, `preview_drop_rows()` likely too large

**Action Plan:**

1. **Extract dataset validation logic:**
   ```python
   # Create: engine/services/dataset_validation_service.py
   def validate_dataset_limits(user, file_size_mb):
       # Check user limits
   
   def validate_file_format(file):
       # Validate file type
   ```

2. **Break down `upload_dataset()`:**
   ```python
   def upload_dataset(request):
       # Main orchestration (30-40 lines)
   
   def _check_user_limits(user, file_size):
       # Limit checking (20-30 lines)
   
   def _save_uploaded_file(file, slug):
       # File saving (15-20 lines)
   
   def _create_dataset_record(name, path, user, file_size):
       # Record creation (15-20 lines)
   ```

3. **Extract row dropping logic:**
   ```python
   # Create: engine/services/row_filtering_service.py
   def preview_drop_rows(dataset, conditions):
       # Preview logic
   
   def apply_drop_rows(dataset, conditions):
       # Apply logic
   
   def _evaluate_condition(df, condition):
       # Condition evaluation
   ```

4. **Extract merge logic:**
   ```python
   # Create: engine/services/dataset_merge_service.py
   def merge_datasets(datasets, merge_columns):
       # Main merge orchestration
   
   def _validate_merge_columns(datasets, merge_columns):
       # Validation
   
   def _perform_merge(dataframes, merge_columns):
       # Actual merge
   ```

**Expected Impact:**
- Reduce from 7 functions to 15-18 functions
- Reduce average function size from 77.7 to ~35 lines
- **Target MI: 75+**

---

### 🟡 Priority 3: Refactor `analysis.py` (MI: 60.5 → Target: 75+)

**Current Issues:**
- 689 lines with 10 functions (avg 68.9 lines per function)
- 119 control flow statements
- `run_bma_analysis()`, `run_anova_analysis()`, `run_varx_analysis()` are likely large

**Action Plan:**

1. **Extract analysis execution logic:**
   ```python
   # Create: engine/services/analysis_execution_service.py
   def execute_bma_analysis(dataset, formula, options):
       # BMA-specific execution
   
   def execute_anova_analysis(dataset, formula, options):
       # ANOVA-specific execution
   
   def execute_varx_analysis(dataset, formula, options):
       # VARX-specific execution
   ```

2. **Break down `add_model_errors_to_dataset()`:**
   - Already uses services, but can be further simplified
   - Extract error calculation logic

3. **Extract IRF generation:**
   ```python
   # Create: engine/services/irf_service.py
   def generate_irf_plot(session, periods, shock_var, response_vars):
       # Plot generation
   
   def generate_irf_data(session, periods, shock_var, response_vars):
       # Data generation
   ```

**Expected Impact:**
- Reduce from 10 functions to 18-20 functions
- Reduce average function size from 68.9 to ~35 lines
- **Target MI: 75+**

---

### 🟢 Priority 4: Optimize `analysis_helpers.py` (MI: 69.5 → Target: 80+)

**Current Issues:**
- 459 lines with 9 functions (avg 51.0 lines per function)
- 111 control flow statements
- Some functions like `_prepare_template_context()` are likely large

**Action Plan:**

1. **Break down `_prepare_template_context()`:**
   ```python
   def _prepare_template_context(sess, dataset, results, cols, model_table_matrix, estimate_col_index, options):
       # Main orchestration (30-40 lines)
   
   def _extract_dataset_columns(dataset):
       # Column extraction (15-20 lines)
   
   def _extract_dv_categories(dataset, formula, regression_type):
       # Category extraction (20-30 lines)
   
   def _build_base_context(sess, dataset, results):
       # Base context (20-30 lines)
   ```

2. **Simplify `_validate_equation()`:**
   - Extract validation rules to separate functions
   - Create validation rule classes

**Expected Impact:**
- Reduce from 9 functions to 15-18 functions
- Reduce average function size from 51.0 to ~30 lines
- **Target MI: 80+**

---

## Implementation Strategy

### Phase 1: Critical Refactoring (Week 1)
1. ✅ Refactor `visualization.py` - Extract spotlight service
2. ✅ Break down `generate_spotlight_plot()` into smaller functions
3. ✅ Extract correlation heatmap logic

**Expected MI Improvement: +8-10 points**

### Phase 2: High Priority Refactoring (Week 2)
1. ✅ Refactor `datasets.py` - Extract validation and merge services
2. ✅ Break down large functions in `datasets.py`
3. ✅ Refactor `analysis.py` - Extract analysis execution services

**Expected MI Improvement: +5-7 points**

### Phase 3: Optimization (Week 3)
1. ✅ Optimize `analysis_helpers.py`
2. ✅ Add more helper functions where needed
3. ✅ Reduce control flow complexity

**Expected MI Improvement: +2-3 points**

---

## Code Quality Best Practices

### Function Size Guidelines
- **Target:** 20-40 lines per function
- **Maximum:** 50 lines per function
- **Action:** Split functions exceeding 50 lines

### Control Flow Guidelines
- **Target:** < 10 control flow statements per function
- **Maximum:** 15 control flow statements per function
- **Action:** Extract complex conditionals to separate functions

### Module Size Guidelines
- **Target:** 200-400 lines per module
- **Maximum:** 500 lines per module
- **Action:** Split modules exceeding 500 lines

### Service Layer Pattern
- Extract business logic to service classes
- Keep views thin (orchestration only)
- Services are testable and reusable

---

## Metrics to Track

### Before Refactoring
- Overall MI: **63.0/100**
- Largest module: `visualization.py` (678 lines, MI: 44.6)
- Largest function: ~200+ lines (in `visualization.py`)
- Average function size: **59.6 lines**

### After Refactoring (Target)
- Overall MI: **80+/100**
- Largest module: < 500 lines, MI: 70+
- Largest function: < 50 lines
- Average function size: **30-35 lines**

---

## Quick Wins (Can be done immediately)

1. **Extract constants:**
   - Move magic numbers to constants
   - Create configuration classes

2. **Add type hints:**
   - Improve code readability
   - Enable better IDE support

3. **Add docstrings:**
   - Document function purposes
   - Improve maintainability

4. **Extract repeated code:**
   - Identify duplicate logic
   - Create shared helper functions

5. **Simplify conditionals:**
   - Extract complex if/else chains
   - Use early returns

---

## Example Refactoring: `generate_spotlight_plot()`

### Before (Estimated 200+ lines):
```python
def generate_spotlight_plot(request, session_id):
    # Authentication check
    # Load dataset
    # Load fitted model
    # Check model type (ordinal/multinomial/standard)
    # Prepare options
    # Handle ordinal regression
    # Handle multinomial regression
    # Handle standard regression
    # Generate plot
    # Return response
    # Error handling throughout
```

### After (Target: 6-8 functions, 20-40 lines each):
```python
def generate_spotlight_plot(request, session_id):
    """Main orchestration for spotlight plot generation."""
    session = _get_session(request, session_id)
    df = _load_dataset(session)
    fitted_model = _load_fitted_model(session, df)
    options = _prepare_spotlight_options(request, session)
    
    plot_json = _generate_plot_by_type(fitted_model, df, request.POST.get('interaction'), options)
    return _format_response(plot_json)

def _get_session(request, session_id):
    """Get and validate session."""
    # 15-20 lines

def _load_dataset(session):
    """Load dataset from session."""
    # 10-15 lines

def _load_fitted_model(session, df):
    """Load or generate fitted model."""
    # 20-30 lines

def _prepare_spotlight_options(request, session):
    """Prepare options from request and session."""
    # 25-35 lines

def _generate_plot_by_type(fitted_model, df, interaction, options):
    """Route to appropriate plot generator."""
    # 20-30 lines with routing logic

def _format_response(plot_json):
    """Format response for return."""
    # 10-15 lines
```

**Impact:**
- Function size: 200+ lines → 6 functions of 20-40 lines each
- Control flow: Distributed across smaller functions
- Testability: Each function can be tested independently
- Reusability: Functions can be reused in other contexts

---

## Success Criteria

✅ Overall MI reaches **80+/100**
✅ No module has MI < **70**
✅ No function exceeds **50 lines**
✅ Average function size < **35 lines**
✅ All modules < **500 lines**
✅ Control flow complexity reduced by **30%+**

---

## Next Steps

1. Review and approve this plan
2. Start with Phase 1 (visualization.py refactoring)
3. Create service classes for extracted logic
4. Update tests to cover new structure
5. Monitor MI improvements after each phase
6. Iterate until target is reached


