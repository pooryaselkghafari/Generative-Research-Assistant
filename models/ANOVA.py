import numpy as np
import pandas as pd
from statsmodels.stats.anova import anova_lm
from statsmodels.formula.api import ols
import plotly.graph_objects as go
from scipy import stats
import re


class ANOVAModule:
    def run(self, df, formula, analysis_type=None, outdir=None, options=None, schema_types=None, schema_orders=None):
        """
        Run ANOVA analysis on the dataset.
        
        Parameters:
        - df: DataFrame containing the data
        - formula: Formula string (e.g., "y ~ x1 + x2")
        - analysis_type: Not used in ANOVA
        - outdir: Output directory for results
        - options: Dictionary of analysis options
        - schema_types: Column type information
        - schema_orders: Column ordering information
        
        Returns:
        Dictionary with ANOVA results
        """
        
        def _quote_column_names_with_special_chars(df, formula):
            """Handle column names with spaces, dots, and other special characters for statsmodels processing"""
            # For statsmodels, we need to temporarily rename columns with special characters
            # and update the formula accordingly
            column_mapping = {}
            df_renamed = df.copy()
            
            # Create mapping for columns with special characters
            for col in df.columns:
                # Check if column name contains spaces, dots, or other problematic characters
                if any(char in col for char in [' ', '.', '-', '(', ')', '[', ']', '+', '*', ':', '~', '^', '$', '|', '\\', '/', '?']):
                    # Create a safe name by replacing problematic characters with underscores
                    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', col)
                    # Ensure the safe name doesn't start with a number
                    if safe_name and safe_name[0].isdigit():
                        safe_name = 'var_' + safe_name
                    # Ensure the safe name is unique
                    original_safe_name = safe_name
                    counter = 1
                    while safe_name in column_mapping.values() or safe_name in df_renamed.columns:
                        safe_name = f"{original_safe_name}_{counter}"
                        counter += 1
                    
                    column_mapping[safe_name] = col
                    df_renamed = df_renamed.rename(columns={col: safe_name})
                    # Update formula to use safe names - use word boundaries to avoid partial matches
                    formula = re.sub(rf'\b{re.escape(col)}\b', safe_name, formula)
            
            return formula, df_renamed, column_mapping
        
        # Parse the formula to extract dependent and independent variables
        if '~' not in formula:
            return {
                'error': 'Invalid formula format. Use "y ~ x1 + x2"',
                'has_results': False
            }
        
        # Split formula into dependent (DV) and independent (IV) variables
        parts = formula.split('~')
        dependent_vars = [v.strip() for v in parts[0].split('+')]
        independent_vars_str = parts[1].strip()
        
        # Parse independent variables (handle interactions)
        independent_vars_raw = [v.strip() for v in independent_vars_str.split('+')]
        independent_vars = []
        
        for var in independent_vars_raw:
            # Handle interactions
            if '*' in var:
                # Extract individual variables from interaction
                ind_vars = [v.strip() for v in var.split('*')]
                independent_vars.extend(ind_vars)
                independent_vars.append(var)  # Also add the full interaction term
            elif ':' in var:
                # Explicit interaction notation
                ind_vars = [v.strip() for v in var.split(':')]
                independent_vars.extend(ind_vars)
                independent_vars.append(var)
            else:
                independent_vars.append(var)
        
        # Remove duplicates while preserving order
        independent_vars = list(dict.fromkeys(independent_vars))
        
        # Filter to only numeric variables
        all_vars = dependent_vars + independent_vars
        
        # Check if variables exist in the dataset
        missing_vars = [v for v in all_vars if v not in df.columns]
        if missing_vars:
            return {
                'error': f'Variables not found in dataset: {", ".join(missing_vars)}',
                'has_results': False
            }
        
        # Filter to only numeric variables
        numeric_vars = []
        for var in all_vars:
            if pd.api.types.is_numeric_dtype(df[var]):
                numeric_vars.append(var)
        
        if not numeric_vars:
            return {
                'error': 'No numeric variables found in the equation. ANOVA requires at least one numeric variable.',
                'has_results': False
            }
        
        # Handle column names with special characters for proper processing BEFORE checking numeric types
        # This ensures variables with special chars are renamed before statsmodels processing
        original_formula = formula
        formula, df_renamed, column_mapping = _quote_column_names_with_special_chars(df, formula)
        
        # Re-parse formula after renaming to get updated variable names
        parts = formula.split('~')
        dependent_vars_renamed = [v.strip() for v in parts[0].split('+')]
        independent_vars_str_renamed = parts[1].strip()
        
        # Re-parse independent variables with updated names
        independent_vars_raw_renamed = [v.strip() for v in independent_vars_str_renamed.split('+')]
        independent_vars_renamed = []
        
        for var in independent_vars_raw_renamed:
            # Handle interactions
            if '*' in var:
                ind_vars = [v.strip() for v in var.split('*')]
                independent_vars_renamed.extend(ind_vars)
                independent_vars_renamed.append(var)  # Also add the full interaction term
            elif ':' in var:
                ind_vars = [v.strip() for v in var.split(':')]
                independent_vars_renamed.extend(ind_vars)
                independent_vars_renamed.append(var)
            else:
                independent_vars_renamed.append(var)
        
        # Remove duplicates while preserving order
        independent_vars_renamed = list(dict.fromkeys(independent_vars_renamed))
        
        # Filter to only numeric variables in renamed dataframe
        all_vars_renamed = dependent_vars_renamed + independent_vars_renamed
        numeric_vars_renamed = []
        for var in all_vars_renamed:
            if var in df_renamed.columns and pd.api.types.is_numeric_dtype(df_renamed[var]):
                numeric_vars_renamed.append(var)
        
        if not numeric_vars_renamed:
            return {
                'error': 'No numeric variables found in the equation. ANOVA requires at least one numeric variable.',
                'has_results': False
            }
        
        # Separate numeric dependent and independent variables
        numeric_dependent_vars = [v for v in dependent_vars_renamed if v in numeric_vars_renamed]
        numeric_independent_vars_renamed = [v for v in independent_vars_renamed if v in numeric_vars_renamed and v not in numeric_dependent_vars]
        
        if not numeric_dependent_vars:
            return {
                'error': 'No numeric dependent variables found in the equation.',
                'has_results': False
            }
        
        if not numeric_independent_vars_renamed:
            return {
                'error': 'No numeric independent variables found in the equation.',
                'has_results': False
            }
        
        # Prepare ANOVA results
        anova_results = {}
        
        try:
            # Run ANOVA for each dependent variable
            for dv in numeric_dependent_vars:
                # Build ANOVA model for this DV
                iv_formula = ' + '.join(numeric_independent_vars_renamed)
                anova_formula = f"{dv} ~ {iv_formula}"
                
                # Fit the model using renamed dataframe
                model = ols(anova_formula, data=df_renamed).fit()
                anova_table = anova_lm(model, typ=2)
                
                anova_table_data = []
                
                # Create reverse mapping from renamed to original names
                reverse_mapping = {v: k for k, v in column_mapping.items()}
                
                try:
                    for idx, row in anova_table.iterrows():
                        # Map source name back to original if it was renamed
                        source_name = str(idx)
                        # Check if this is a renamed variable
                        if source_name in reverse_mapping:
                            source_name = reverse_mapping[source_name]
                        # Also check for interaction terms - they might contain renamed variables
                        else:
                            # Handle interaction terms like "var1:var2" or "var1 * var2"
                            for renamed_var, original_var in reverse_mapping.items():
                                if renamed_var in source_name:
                                    source_name = source_name.replace(renamed_var, original_var)
                                    break
                        
                        row_data = {'source': source_name}
                        
                        # Try to get sum of squares
                        sum_sq = None
                        if 'sum_sq' in anova_table.columns:
                            sum_sq = float(row['sum_sq']) if pd.notna(row['sum_sq']) else None
                        row_data['sum_sq'] = sum_sq
                        
                        # Try to get degrees of freedom (use df_value to avoid overwriting DataFrame df)
                        df_value = None
                        if 'df' in anova_table.columns:
                            df_value = int(row['df']) if pd.notna(row['df']) else None
                        row_data['df'] = df_value
                        
                        # Calculate mean square = sum_sq / df
                        mean_sq = None
                        if 'mean_sq' in anova_table.columns:
                            mean_sq = float(row['mean_sq']) if pd.notna(row['mean_sq']) else None
                        else:
                            # Calculate it ourselves
                            if sum_sq is not None and df_value is not None and df_value != 0:
                                mean_sq = sum_sq / df_value
                        row_data['mean_sq'] = mean_sq
                        
                        # Try to get F statistic
                        f_stat = None
                        if 'F' in anova_table.columns:
                            f_stat = float(row['F']) if pd.notna(row['F']) else None
                        row_data['F'] = f_stat
                        
                        # Try to get p-value (PR(>F))
                        pr_gt_f = None
                        if 'PR(>F)' in anova_table.columns:
                            pr_gt_f = float(row['PR(>F)']) if pd.notna(row['PR(>F)']) else None
                        elif 'pvalue' in anova_table.columns:
                            pr_gt_f = float(row['pvalue']) if pd.notna(row['pvalue']) else None
                        elif 'p_value' in anova_table.columns:
                            pr_gt_f = float(row['p_value']) if pd.notna(row['p_value']) else None
                        
                        row_data['PR_F'] = pr_gt_f
                        anova_table_data.append(row_data)
                        
                except Exception as e:
                    print(f"Error processing ANOVA table: {e}")
                    # Return a simplified version with just source names
                    reverse_mapping = {v: k for k, v in column_mapping.items()}
                    for idx, _ in anova_table.iterrows():
                        source_name = str(idx)
                        if source_name in reverse_mapping:
                            source_name = reverse_mapping[source_name]
                        anova_table_data.append({'source': source_name})
                
                anova_results[dv] = {
                    'anova_table': anova_table_data,
                    'formula': anova_formula,
                    'model': model
                }
            
            # Map dependent and independent variable names back to originals for display
            reverse_mapping = {v: k for k, v in column_mapping.items()}
            original_dependent_vars = [reverse_mapping.get(v, v) for v in numeric_dependent_vars]
            original_independent_vars = [reverse_mapping.get(v, v) for v in numeric_independent_vars_renamed]
            
            # For numeric_vars, we want ALL numeric variables in the original dataframe (for dropdown)
            # not just the ones in the formula. Calculate this from the original dataframe.
            all_numeric_vars_from_original_df = [
                col for col in df.columns 
                if pd.api.types.is_numeric_dtype(df[col])
            ]
            
            # Prepare output with original variable names
            results = {
                'has_results': True,
                'anova_results': anova_results,
                'dependent_vars': original_dependent_vars,
                'independent_vars': original_independent_vars,
                'formula': original_formula,  # Use original formula for display
                'numeric_vars': all_numeric_vars_from_original_df,  # All numeric vars from original dataframe
                'error': None
            }
            
            return results
            
        except Exception as e:
            return {
                'error': f'Error running ANOVA: {str(e)}',
                'has_results': False
            }

def generate_anova_plot(df, x_var, y_var, group_var=None, x_std=1.0, group_std=1.0, sig_level=0.05):
    """
    Generate a bar chart with t-tests between high/low groups on X in terms of Y.
    
    Parameters:
    - df: DataFrame containing the data
    - x_var: X axis variable name
    - y_var: Y axis variable name  
    - group_var: Optional grouping variable name
    - x_std: Number of standard deviations to split X by
    - group_std: Number of standard deviations to split group by
    - sig_level: Significance level for asterisks (0.01, 0.05, or 0.10)
    
    Returns:
    Dictionary with plot data and statistical results
    """
    
    def is_binary(vec):
        """Check if a variable is binary (only 0 and 1)"""
        unique_vals = pd.Series(vec).dropna().unique()
        return set(unique_vals).issubset({0, 1}) and len(unique_vals) == 2
    
    def check_group_size(groups, group_name=""):
        """Check if each group has at least 2 data points"""
        for group_name_val, group_mask in groups.items():
            if np.sum(group_mask) < 2:
                return False, f"{group_name_val}"
        return True, None
    
    # Check if variables exist
    if x_var not in df.columns or y_var not in df.columns:
        return {'success': False, 'error': 'Variables not found in dataset'}
    
    if group_var and group_var not in df.columns:
        return {'success': False, 'error': 'Group variable not found in dataset'}
    
    # Get data
    x_data = df[x_var].values
    y_data = df[y_var].values
    
    # Check if X is binary
    x_is_binary = is_binary(x_data)
    
    # Split X into high/low
    if x_is_binary:
        high_x = x_data == 1
        low_x = x_data == 0
        x_labels = ['Low (0)', 'High (1)']
    else:
        mean_x = np.nanmean(x_data)
        sd_x = np.nanstd(x_data) * x_std
        high_x = x_data > (mean_x + sd_x)
        low_x = x_data < (mean_x - sd_x)
        x_labels = ['Low', 'High']
    
    # Check if we have enough data in high_x and low_x groups
    if np.sum(high_x) < 2 or np.sum(low_x) < 2:
        return {
            'success': False, 
            'error': 'Insufficient data for comparison. Please adjust the X split standard deviation (current: {:.1f}). At least one group has fewer than 2 data points.'.format(x_std)
        }
    
    # Handle grouping variable
    if group_var:
        group_data = df[group_var].values
        group_is_binary = is_binary(group_data)
        
        if group_is_binary:
            high_group = group_data == 1
            low_group = group_data == 0
            group_labels = ['Low (0)', 'High (1)']
        else:
            mean_group = np.nanmean(group_data)
            sd_group = np.nanstd(group_data) * group_std
            high_group = group_data > (mean_group + sd_group)
            low_group = group_data < (mean_group - sd_group)
            group_labels = ['Low', 'High']
        
        # Check if we have enough data in each group combination
        if (np.sum(high_x & high_group) < 2 or 
            np.sum(high_x & low_group) < 2 or 
            np.sum(low_x & high_group) < 2 or 
            np.sum(low_x & low_group) < 2):
            return {
                'success': False, 
                'error': 'Insufficient data for comparison. Please adjust the X and group variable division (X std: {:.1f}, Group std: {:.1f}). At least one t-test cannot be done due to lack of enough data points.'.format(x_std, group_std)
            }
        
        # Calculate means for each group combination
        mean_high_x_high_group = np.nanmean(y_data[high_x & high_group]) if np.any(high_x & high_group) else np.nan
        mean_high_x_low_group = np.nanmean(y_data[high_x & low_group]) if np.any(high_x & low_group) else np.nan
        mean_low_x_high_group = np.nanmean(y_data[low_x & high_group]) if np.any(low_x & high_group) else np.nan
        mean_low_x_low_group = np.nanmean(y_data[low_x & low_group]) if np.any(low_x & low_group) else np.nan
        
        # Perform t-tests with error handling
        t_test_high_x = None
        try:
            high_x_high_group = y_data[high_x & high_group]
            high_x_low_group = y_data[high_x & low_group]
            if len(high_x_high_group) >= 2 and len(high_x_low_group) >= 2:
                t_test_high_x = stats.ttest_ind(high_x_high_group, high_x_low_group, nan_policy='omit')
        except Exception:
            pass
        
        t_test_low_x = None
        try:
            low_x_high_group = y_data[low_x & high_group]
            low_x_low_group = y_data[low_x & low_group]
            if len(low_x_high_group) >= 2 and len(low_x_low_group) >= 2:
                t_test_low_x = stats.ttest_ind(low_x_high_group, low_x_low_group, nan_policy='omit')
        except Exception:
            pass
        
        t_test_high_vs_low = None
        try:
            high_x_data = y_data[high_x]
            low_x_data = y_data[low_x]
            if len(high_x_data) >= 2 and len(low_x_data) >= 2:
                t_test_high_vs_low = stats.ttest_ind(high_x_data, low_x_data, nan_policy='omit')
        except Exception:
            pass
        
        # Create plot data with variable names
        # X-axis categories: High x_var, Low x_var
        x_categories = [
            f"{x_labels[1]} {x_var}",  # High x_var
            f"{x_labels[0]} {x_var}"   # Low x_var
        ]
        
        # Means order: [High X Low Group, High X High Group, Low X Low Group, Low X High Group]
        means = [mean_high_x_low_group, mean_high_x_high_group, mean_low_x_low_group, mean_low_x_high_group]
        
        # Calculate significance symbols
        def get_sig_symbol(p):
            if p < 0.001: return "***"
            elif p < 0.01: return "**"
            elif p < 0.05: return "*"
            else: return ""
        
        # Create the plot with legend for group variable
        fig = go.Figure()
        
        # Add bars split by group variable (legend)
        # At "High x_var" position: Low group and High group bars
        # At "Low x_var" position: Low group and High group bars
        fig.add_trace(go.Bar(
            name=f"{group_labels[0]} {group_var}",  # Low group
            x=x_categories,
            y=[means[0], means[2]],  # High X Low Group, Low X Low Group
            marker_color='#cccccc',
            marker_line_color=['black', 'black'],  # Border color for each bar in this trace
            marker_line_width=1,
            text=[f'{means[0]:.2f}', f'{means[2]:.2f}'],
            textposition='outside'
        ))
        
        fig.add_trace(go.Bar(
            name=f"{group_labels[1]} {group_var}",  # High group
            x=x_categories,
            y=[means[1], means[3]],  # High X High Group, Low X High Group
            marker_color='#333333',
            marker_line_color=['black', 'black'],  # Border color for each bar in this trace
            marker_line_width=1,
            text=[f'{means[1]:.2f}', f'{means[3]:.2f}'],
            textposition='outside'
        ))
        
        # Add significance asterisks
        def get_sig_symbol(p):
            if p < 0.001: return "***"
            elif p < 0.01: return "**"
            elif p < 0.05: return "*"
            else: return ""
        
        # Check if we have any valid means
        valid_means = [m for m in means if not np.isnan(m)]
        if not valid_means:
            return {
                'success': False,
                'error': 'Insufficient data for comparison. Please adjust the X and group variable division (X std: {:.1f}, Group std: {:.1f}). At least one t-test cannot be done due to lack of enough data points.'.format(x_std, group_std)
            }
        y_max = max(valid_means)
        asterisk_y = y_max * 1.15
        
        # Add significance lines for high x group (first position)
        if t_test_high_x and not np.isnan(t_test_high_x.pvalue):
            if t_test_high_x.pvalue <= sig_level:
                # Get the two bar positions for this x category (for grouped bars)
                # At x position 0, bars are at -0.2 and 0.2 (for grouped bar mode)
                bar_x_left = -0.2  # Left bar position
                bar_x_right = 0.2  # Right bar position
                
                # Add horizontal line connecting the two bars within high x group
                fig.add_shape(
                    type="line",
                    x0=bar_x_left, y0=asterisk_y,
                    x1=bar_x_right, y1=asterisk_y,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add vertical cap on left side
                fig.add_shape(
                    type="line",
                    x0=bar_x_left, y0=asterisk_y - 0.01 * y_max,
                    x1=bar_x_left, y1=asterisk_y + 0.01 * y_max,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add vertical cap on right side
                fig.add_shape(
                    type="line",
                    x0=bar_x_right, y0=asterisk_y - 0.01 * y_max,
                    x1=bar_x_right, y1=asterisk_y + 0.01 * y_max,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add asterisk centered above the line
                sig_symbol = get_sig_symbol(t_test_high_x.pvalue)
                fig.add_annotation(
                    xref="x",
                    yref="y",
                    x=0,  # Center of x position
                    y=asterisk_y + 0.02 * y_max,
                    text=sig_symbol,
                    showarrow=False,
                    font=dict(size=16, color='black'),
                    bgcolor="white",
                    bordercolor="white",
                    borderwidth=0
                )
        
        # Add significance lines for low x group (second position)
        if t_test_low_x and not np.isnan(t_test_low_x.pvalue):
            if t_test_low_x.pvalue <= sig_level:
                # Get the two bar positions for this x category (for grouped bars)
                # At x position 1, bars are at 0.8 and 1.2 (for grouped bar mode)
                bar_x_left = 0.8  # Left bar position
                bar_x_right = 1.2  # Right bar position
                
                # Add horizontal line connecting the two bars within low x group
                fig.add_shape(
                    type="line",
                    x0=bar_x_left, y0=asterisk_y,
                    x1=bar_x_right, y1=asterisk_y,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add vertical cap on left side
                fig.add_shape(
                    type="line",
                    x0=bar_x_left, y0=asterisk_y - 0.01 * y_max,
                    x1=bar_x_left, y1=asterisk_y + 0.01 * y_max,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add vertical cap on right side
                fig.add_shape(
                    type="line",
                    x0=bar_x_right, y0=asterisk_y - 0.01 * y_max,
                    x1=bar_x_right, y1=asterisk_y + 0.01 * y_max,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add asterisk centered above the line
                sig_symbol = get_sig_symbol(t_test_low_x.pvalue)
                fig.add_annotation(
                    xref="x",
                    yref="y",
                    x=1,  # Center of x position
                    y=asterisk_y + 0.02 * y_max,
                    text=sig_symbol,
                    showarrow=False,
                    font=dict(size=16, color='black'),
                    bgcolor="white",
                    bordercolor="white",
                    borderwidth=0
                )
        
        # Add significance line for overall high_x vs low_x comparison
        if t_test_high_vs_low and not np.isnan(t_test_high_vs_low.pvalue):
            if t_test_high_vs_low.pvalue <= sig_level:
                overall_y = y_max * 1.25  # Slightly higher than the within-group lines
                
                # Add horizontal line spanning from first to second position
                fig.add_shape(
                    type="line",
                    x0=0, y0=overall_y,
                    x1=1, y1=overall_y,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add vertical cap on left side (at x=0)
                fig.add_shape(
                    type="line",
                    x0=0, y0=overall_y - 0.01 * y_max,
                    x1=0, y1=overall_y + 0.01 * y_max,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add vertical cap on right side (at x=1)
                fig.add_shape(
                    type="line",
                    x0=1, y0=overall_y - 0.01 * y_max,
                    x1=1, y1=overall_y + 0.01 * y_max,
                    line=dict(color='black', width=1),
                    xref="x", yref="y"
                )
                
                # Add centered asterisk
                sig_symbol = get_sig_symbol(t_test_high_vs_low.pvalue)
                fig.add_annotation(
                    xref="x",
                    yref="y",
                    x=0.5,  # Center between the two positions
                    y=overall_y + 0.02 * y_max,
                    text=sig_symbol,
                    showarrow=False,
                    font=dict(size=16, color='black'),
                    bgcolor="white",
                    bordercolor="white",
                    borderwidth=0
                )
        
        # Update layout with legend and white background
        fig.update_layout(
            title=f'T-test: {y_var} by {x_var} and {group_var}',
            xaxis_title=x_var,
            yaxis_title=y_var,
            showlegend=True,
            barmode='group',
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500
        )
        
        # Convert to JSON format
        plot_json = fig.to_json()
        
        # Include variable names for customization
        return {
            'success': True,
            'plot_data': fig.to_dict(),
            'plot_json': plot_json,
            'x_var': x_var,
            'y_var': y_var,
            'group_var': group_var
        }
        
    else:
        # No grouping variable - simple comparison
        mean_high_x = np.nanmean(y_data[high_x]) if np.any(high_x) else np.nan
        mean_low_x = np.nanmean(y_data[low_x]) if np.any(low_x) else np.nan
        
        # Perform t-test with error handling
        t_test = None
        try:
            high_x_data = y_data[high_x]
            low_x_data = y_data[low_x]
            if len(high_x_data) >= 2 and len(low_x_data) >= 2:
                t_test = stats.ttest_ind(high_x_data, low_x_data, nan_policy='omit')
        except Exception:
            pass
        
        # Create plot data with variable names
        # Format: "Low x_var" and "High x_var"
        categories = [f"{x_labels[0]} {x_var}", f"{x_labels[1]} {x_var}"]
        means = [mean_low_x, mean_high_x]
        
        # Create the plot
        fig = go.Figure()
        
        # Determine colors for each bar
        # Bars are: 0=Low, 1=High
        # Colors: low group = grey80 (#cccccc), high group = grey20 (#333333)
        bar_colors = ['#cccccc', '#333333']  # Low, High
        
        # Add bars with border colors (black for both)
        bar_border_colors = ['black', 'black']  # Low, High
        fig.add_trace(go.Bar(
            x=categories,
            y=means,
            marker_color=bar_colors,
            marker_line_color=bar_border_colors,
            marker_line_width=1,
            text=[f'{m:.2f}' for m in means],
            textposition='outside'
        ))
        
        # Add significance asterisk if significant
        if t_test and not np.isnan(t_test.pvalue) and t_test.pvalue <= sig_level:
            def get_sig_symbol(p):
                if p < 0.001: return "***"
                elif p < 0.01: return "**"
                elif p < 0.05: return "*"
                else: return ""
            
            # Check if we have any valid means
            valid_means = [m for m in means if not np.isnan(m)]
            if not valid_means:
                return {
                    'success': False,
                    'error': 'Insufficient data for comparison. Please adjust the X split standard deviation (current: {:.1f}). At least one group has fewer than 2 data points.'.format(x_std)
                }
            y_max = max(valid_means)
            asterisk_y = y_max * 1.1
            
            # Add horizontal line connecting the two bars
            fig.add_shape(
                type="line",
                x0=0, y0=asterisk_y,
                x1=1, y1=asterisk_y,
                line=dict(color="black", width=1),
                xref="x", yref="y"
            )
            
            # Add vertical cap on left side (at x=0)
            fig.add_shape(
                type="line",
                x0=0, y0=asterisk_y - 0.01 * y_max,
                x1=0, y1=asterisk_y + 0.01 * y_max,
                line=dict(color="black", width=1),
                xref="x", yref="y"
            )
            
            # Add vertical cap on right side (at x=1)
            fig.add_shape(
                type="line",
                x0=1, y0=asterisk_y - 0.01 * y_max,
                x1=1, y1=asterisk_y + 0.01 * y_max,
                line=dict(color="black", width=1),
                xref="x", yref="y"
            )
            
            # Add single asterisk symbol as annotation centered between the two groups
            sig_symbol = get_sig_symbol(t_test.pvalue)
            fig.add_annotation(
                xref="x",
                yref="y",
                x=0.5,  # Center between first (0) and second (1) category
                y=asterisk_y + 0.02 * y_max,
                text=sig_symbol,
                showarrow=False,
                font=dict(size=16, color='black'),
                bgcolor="white",
                bordercolor="white",
                borderwidth=0
            )
        
        # Update layout with white background
        fig.update_layout(
            title=f'T-test: {y_var} by {x_var}',
            xaxis_title=x_var,
            yaxis_title=y_var,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500
        )
        
        # Convert to JSON format
        plot_json = fig.to_json()
        
        # Include variable names for customization
        return {
            'success': True,
            'plot_data': fig.to_dict(),
            'plot_json': plot_json,
            'x_var': x_var,
            'y_var': y_var,
            'group_var': None
        }

