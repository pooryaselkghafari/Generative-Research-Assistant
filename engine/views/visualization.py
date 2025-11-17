"""
Views for visualization and plot generation.
"""
import json
import pandas as pd
import numpy as np
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from engine.models import Dataset, AnalysisSession
from engine.services.spotlight_service import SpotlightService
from engine.services.visualization_service import VisualizationService
from data_prep.file_handling import _read_dataset_file
from models.regression import generate_spotlight_for_interaction

def visualize_data(request):
    """Handle visualization requests"""
    if request.method == 'POST':
        # Handle plot generation requests
        if request.POST.get('action') == 'generate_plot':
            return generate_plot(request)
        
        # Handle initial page load with dataset
        dataset_id = request.POST.get('dataset_id')
        if not dataset_id:
            return HttpResponse('Please select a dataset from the dropdown', status=400)
        
        try:
            # Security: Only allow access to user's own datasets
            dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
            
            # Get column information using service
            column_info = VisualizationService.get_dataset_columns(dataset)
            
            context = {
                'dataset': dataset,
                'numeric_columns': column_info['numeric_columns'],
                'categorical_columns': column_info['categorical_columns'],
                'all_columns': column_info['all_columns'],
                'numeric_columns_json': json.dumps(column_info['numeric_columns']),
                'categorical_columns_json': json.dumps(column_info['categorical_columns']),
                'all_columns_json': json.dumps(column_info['all_columns']),
            }
            
            return render(request, 'engine/visualize.html', context)
            
        except Exception as e:
            return HttpResponse(f'Error loading dataset: {e}', status=400)
    
    return HttpResponse('Method not allowed', status=405)



def generate_plot(request):
    """Generate a plot based on user selections"""
    try:
        dataset_id = request.POST.get('dataset_id')
        plot_type = request.POST.get('plot_type')
        
        if not dataset_id or not plot_type:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        # Security: Only allow access to user's own datasets
        dataset = get_object_or_404(Dataset, pk=dataset_id, user=request.user)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path, user_id=request.user.id)
        
        # Import visualization functions
        from models.visualization import (
            generate_scatter_plot, generate_histogram, generate_bar_chart,
            generate_line_chart, generate_pie_chart
        )
        
        # Get plot parameters
        x_var = request.POST.get('x_var')
        y_var = request.POST.get('y_var')
        group_var = request.POST.get('group_var') or None
        trendline = request.POST.get('trendline') == 'true'
        bins = int(request.POST.get('bins', 30))
        
        # Get custom styling options from request
        x_label = request.POST.get('x_label', '')
        y_label = request.POST.get('y_label', '')
        point_color = request.POST.get('point_color', '')
        bar_color = request.POST.get('bar_color', '')
        line_color = request.POST.get('line_color', '')
        line_style = request.POST.get('line_style', '')
        background_color = request.POST.get('background_color', '')
        color_scheme = request.POST.get('color_scheme', '')
        
        # Prepare custom styling kwargs
        style_kwargs = {}
        if x_label: style_kwargs['x_label'] = x_label
        if y_label: style_kwargs['y_label'] = y_label
        if point_color: style_kwargs['point_color'] = point_color
        if bar_color: style_kwargs['bar_color'] = bar_color
        if line_color: style_kwargs['line_color'] = line_color
        if line_style: style_kwargs['line_style'] = line_style
        if background_color: style_kwargs['background_color'] = background_color
        if color_scheme: style_kwargs['color_scheme'] = color_scheme
        
        # Generate the appropriate plot
        if plot_type == 'scatter':
            if not x_var or not y_var:
                return JsonResponse({'error': 'X and Y variables required for scatter plot'}, status=400)
            fig = generate_scatter_plot(df, x_var, y_var, group_var, trendline, **style_kwargs)
            
        elif plot_type == 'histogram':
            if not x_var:
                return JsonResponse({'error': 'Variable required for histogram'}, status=400)
            fig = generate_histogram(df, x_var, group_var, bins, **style_kwargs)
            
        elif plot_type == 'bar':
            if not x_var:
                return JsonResponse({'error': 'X variable required for bar chart'}, status=400)
            fig = generate_bar_chart(df, x_var, y_var, group_var, **style_kwargs)
            
        elif plot_type == 'line':
            if not x_var or not y_var:
                return JsonResponse({'error': 'X and Y variables required for line chart'}, status=400)
            fig = generate_line_chart(df, x_var, y_var, group_var, **style_kwargs)
            
        elif plot_type == 'pie':
            if not x_var:
                return JsonResponse({'error': 'Variable required for pie chart'}, status=400)
            fig = generate_pie_chart(df, x_var, group_var, **style_kwargs)
            
        else:
            return JsonResponse({'error': 'Invalid plot type'}, status=400)
        
        # Convert plot to JSON
        plot_json = fig.to_json()
        
        return JsonResponse({
            'success': True,
            'plot_data': plot_json,
            'plot_type': plot_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def _generate_multinomial_ordinal_spotlight_from_predictions(predictions, interaction, category, options):
    """Generate spotlight plot from pre-generated ordinal or multinomial predictions."""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
        
        # Parse interaction to get variable names
        x, m = SpotlightService.parse_interaction(interaction)
        if not x or not m:
            return None
        
        # Get moderator levels (should be exactly 2: low and high)
        moderator_levels = list(predictions.keys())
        print(f"DEBUG: Available moderator levels: {moderator_levels}")
        if len(moderator_levels) < 2:
            print(f"DEBUG: Not enough moderator levels: {len(moderator_levels)}")
            return None
        
        # Sort levels to ensure consistent low/high ordering
        low_level, high_level = _get_moderator_levels(moderator_levels)
        
        # Validate predictions data
        if not _validate_predictions_data(predictions, low_level, high_level, category):
            return None
        
        # Get data for both levels
        low_data = predictions[low_level][category]
        high_data = predictions[high_level][category]
        x_values = low_data['x_values']
        low_probs = low_data['probabilities']
        high_probs = high_data['probabilities']
        
        # Create the plot
        fig = _build_spotlight_figure(x_values, low_probs, high_probs, x, m, category, options)
        
        # Convert to JSON
        return pio.to_json(fig)
        
    except Exception as e:
        print(f"Error generating ordinal spotlight from predictions: {e}")
        return None


def _get_moderator_levels(moderator_levels):
    """Get low and high moderator levels from list."""
    numeric_levels = []
    for level in moderator_levels:
        try:
            numeric_levels.append(float(level))
        except ValueError:
            continue
    
    if numeric_levels:
        numeric_levels.sort()
        return str(numeric_levels[0]), str(numeric_levels[1])
    else:
        return moderator_levels[0], moderator_levels[1]


def _validate_predictions_data(predictions, low_level, high_level, category):
    """Validate that predictions data exists for both levels and category."""
    print(f"DEBUG: Selected low_level: {low_level}, high_level: {high_level}")
    print(f"DEBUG: Available categories in low_level: {list(predictions[low_level].keys()) if low_level in predictions else 'Not found'}")
    print(f"DEBUG: Available categories in high_level: {list(predictions[high_level].keys()) if high_level in predictions else 'Not found'}")
    print(f"DEBUG: Looking for category: {category}")
    
    if (low_level not in predictions or high_level not in predictions or 
        category not in predictions[low_level] or 
        category not in predictions[high_level]):
        print(f"DEBUG: Missing data - low_level in predictions: {low_level in predictions}")
        print(f"DEBUG: Missing data - high_level in predictions: {high_level in predictions}")
        if low_level in predictions:
            print(f"DEBUG: Missing data - category in low_level: {category in predictions[low_level]}")
        if high_level in predictions:
            print(f"DEBUG: Missing data - category in high_level: {category in predictions[high_level]}")
        return False
    return True


def _build_spotlight_figure(x_values, low_probs, high_probs, x, m, category, options):
    """Build Plotly figure for spotlight plot."""
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    # Get custom names and styles
    x_label = options.get('x_name', x)
    y_label = options.get('y_name', f'Probability of {category}')
    
    # Handle moderator name
    moderator_var = options.get('moderator_var')
    if moderator_var and moderator_var.strip():
        moderator_name = moderator_var.strip()
    else:
        moderator_name = m
    
    legend_low = options.get('legend_low', f'Low {moderator_name}')
    legend_high = options.get('legend_high', f'High {moderator_name}')
    
    # Get line styles
    line_style_low = options.get('line_style_low', 'solid')
    line_style_high = options.get('line_style_high', 'dashed')
    
    # Convert line style to Plotly format
    def get_plotly_dash(style):
        style_map = {
            'solid': None,
            'dashed': 'dash',
            'dotted': 'dot',
            'dashdot': 'dashdot'
        }
        return style_map.get(style, None)
    
    # Add low moderator line
    fig.add_trace(go.Scatter(
        x=x_values,
        y=low_probs,
        mode='lines',
        name=legend_low,
        line=dict(
            color=options.get('color_low', '#1f77b4'),
            width=2,
            dash=get_plotly_dash(line_style_low)
        )
    ))
    
    # Add high moderator line
    fig.add_trace(go.Scatter(
        x=x_values,
        y=high_probs,
        mode='lines',
        name=legend_high,
        line=dict(
            color=options.get('color_high', '#ff7f0e'),
            width=2,
            dash=get_plotly_dash(line_style_high)
        )
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Probability of {category} by {x_label} (Low vs High {moderator_name})',
        xaxis_title=x_label,
        yaxis_title=y_label,
        showlegend=True,
        plot_bgcolor=options.get('background_color', 'white'),
        paper_bgcolor='white'
    )
    
    # Add grid if requested
    if options.get('show_grid', True):
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    return fig



def generate_spotlight_plot(request, session_id):
    """Generate spotlight plot for a specific interaction."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    # Security: Only allow access to user's own sessions
    session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
    interaction = request.POST.get('interaction')
    
    if not interaction:
        return HttpResponse('Interaction required', status=400)
    
    try:
        # Load dataset
        user_id = session.dataset.user.id if session.dataset.user else None
        df, schema_types, schema_orders = _read_dataset_file(session.dataset.file_path, user_id=user_id)
        print(f"Dataset columns: {list(df.columns)}")
        print(f"Requested interaction: {interaction}")
        print(f"Custom moderator: {request.POST.get('moderator_var', 'None')}")
        
        # Load fitted model using service
        fitted_model = SpotlightService.load_fitted_model(session, df)
        if not fitted_model:
            return HttpResponse('No fitted model available', status=500)
        
        # Prepare options using service
        custom_options = SpotlightService.prepare_spotlight_options(request, session)
        
        # Detect model type
        is_ordinal, is_multinomial = SpotlightService.detect_model_type(fitted_model)
        
        # Generate spotlight plot based on model type
        spotlight_json = _generate_spotlight_by_type(
            session, fitted_model, df, interaction, custom_options, is_ordinal, is_multinomial
        )
        
        # Format and return response
        return _format_spotlight_response(spotlight_json, interaction, df)
        
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}\nTraceback: {traceback.format_exc()}'
        return HttpResponse(error_msg, status=500)


def _generate_spotlight_by_type(session, fitted_model, df, interaction, custom_options, is_ordinal, is_multinomial):
    """Generate spotlight plot based on regression type."""
    # Handle ordinal regression with precomputed predictions
    if is_ordinal and hasattr(session, 'ordinal_predictions') and session.ordinal_predictions:
        return _handle_ordinal_spotlight(session, fitted_model, df, interaction, custom_options, is_ordinal)
    
    # Handle multinomial regression
    if is_multinomial:
        print(f"DEBUG: Multinomial regression detected, using regular generation")
        multinomial_category = custom_options.get('multinomial_category')
        print(f"DEBUG: multinomial_category = {multinomial_category}")
        print(f"DEBUG: interaction = {interaction}")
        print(f"DEBUG: is_multinomial = {is_multinomial}")
        
        return SpotlightService.generate_spotlight_plot(
            fitted_model, df, interaction, custom_options, is_ordinal=False, is_multinomial=True
        )
    
    # Handle standard regression
    return SpotlightService.generate_spotlight_plot(
        fitted_model, df, interaction, custom_options, is_ordinal=False, is_multinomial=False
    )


def _handle_ordinal_spotlight(session, fitted_model, df, interaction, custom_options, is_ordinal):
    """Handle ordinal regression spotlight plot generation."""
    ordinal_category = custom_options.get('ordinal_category')
    
    if not ordinal_category or interaction not in session.ordinal_predictions:
        # Fall back to regular generation
        return _generate_ordinal_fallback(fitted_model, df, interaction, custom_options, is_ordinal)
    
    # Check if we can use precomputed predictions
    separation_method = custom_options.get('moderator_separation', 'mean')
    std_dev_multiplier_raw = custom_options.get('moderator_std_dev_multiplier', 1.0)
    
    try:
        std_dev_multiplier = float(std_dev_multiplier_raw)
    except (ValueError, TypeError):
        std_dev_multiplier = 1.0
        print(f"DEBUG: Could not convert std_dev_multiplier '{std_dev_multiplier_raw}' to float, using 1.0")
    
    print(f"DEBUG: Ordinal regression - separation_method: {separation_method}, std_dev_multiplier: {std_dev_multiplier}")
    
    if SpotlightService.should_use_precomputed_predictions(separation_method, std_dev_multiplier):
        print(f"DEBUG: Using pre-generated ordinal predictions")
        ordinal_options = SpotlightService.prepare_ordinal_options(interaction, custom_options)
        
        return _generate_multinomial_ordinal_spotlight_from_predictions(
            session.ordinal_predictions[interaction],
            interaction,
            ordinal_category,
            ordinal_options
        )
    else:
        # Regenerate with custom parameters
        print(f"DEBUG: Regenerating ordinal spotlight with custom parameters")
        print(f"DEBUG: Ordinal category being passed to regeneration: {ordinal_category}")
        return SpotlightService.generate_spotlight_plot(
            fitted_model, df, interaction, custom_options, is_ordinal=is_ordinal, is_multinomial=False
        )


def _generate_ordinal_fallback(fitted_model, df, interaction, custom_options, is_ordinal):
    """Generate ordinal spotlight plot with fallback options."""
    x_var, moderator_var = SpotlightService.parse_interaction(interaction)
    
    fallback_options = custom_options.copy()
    if not fallback_options.get('x_name'):
        fallback_options['x_name'] = x_var
    if not fallback_options.get('moderator_display_name'):
        fallback_options['moderator_display_name'] = moderator_var
    if not fallback_options.get('y_name'):
        fallback_options['y_name'] = 'Predicted Probability'
    if not fallback_options.get('moderator_separation'):
        fallback_options['moderator_separation'] = 'mean'
    
    return SpotlightService.generate_spotlight_plot(
        fitted_model, df, interaction, fallback_options, is_ordinal=is_ordinal, is_multinomial=False
    )


def _format_spotlight_response(spotlight_json, interaction, df):
    """Format spotlight plot response."""
    if spotlight_json:
        # Check if it's a special response (like ordinal category selection)
        if isinstance(spotlight_json, dict) and 'type' in spotlight_json:
            return JsonResponse(spotlight_json)
        else:
            return HttpResponse(spotlight_json, content_type='application/json')
    else:
        # Generate error message
        x, m = SpotlightService.parse_interaction(interaction)
        
        if not x or not m:
            return HttpResponse(
                SpotlightService.format_error_response(interaction, df, 'invalid_format'),
                status=500
            )
        
        # Check which variable is missing
        if x not in df.columns:
            return HttpResponse(
                SpotlightService.format_error_response(interaction, df, 'missing_x'),
                status=500
            )
        
        if m not in df.columns:
            return HttpResponse(
                SpotlightService.format_error_response(interaction, df, 'missing_moderator'),
                status=500
            )
        
        return HttpResponse(
            SpotlightService.format_error_response(interaction, df, 'unknown'),
            status=500
        )




def generate_correlation_heatmap(request, session_id):
    """Generate correlation heatmap for continuous variables."""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    # Security: Only allow access to user's own sessions
    session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
    
    try:
        # Security: Verify dataset belongs to user
        if session.dataset and session.dataset.user != request.user:
            return JsonResponse({'error': 'Dataset access denied'}, status=403)
        
        # Prepare variables using service
        request_vars = {
            'x_vars': request.POST.getlist('x_vars[]'),
            'y_vars': request.POST.getlist('y_vars[]')
        }
        x_vars, y_vars = VisualizationService.prepare_correlation_heatmap_variables(session, request_vars)
        
        # Prepare options using service
        options = VisualizationService.prepare_heatmap_options(request)
        
        # Generate heatmap using service
        heatmap_json = VisualizationService.generate_correlation_heatmap(session, x_vars, y_vars, options)
        
        if heatmap_json:
            return HttpResponse(heatmap_json, content_type='application/json')
        else:
            return HttpResponse('Failed to generate correlation heatmap', status=500)
            
    except ValueError as e:
        return HttpResponse(str(e), status=400)
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}\nTraceback: {traceback.format_exc()}'
        return HttpResponse(error_msg, status=500)





def generate_anova_plot_view(request, session_id):
    """Generate ANOVA plot with t-tests"""
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        # Security: Only allow access to user's own sessions
        session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
        
        # Parse JSON body
        data = json.loads(request.body)
        
        # Validate required parameters
        x_var = data.get('x_var')
        y_var = data.get('y_var')
        if not x_var or not y_var:
            return JsonResponse({'success': False, 'error': 'X and Y variables required'}, status=400)
        
        # Prepare plot parameters
        plot_params = {
            'x_var': x_var,
            'y_var': y_var,
            'group_var': data.get('group_var'),
            'x_std': float(data.get('x_std', 1.0)),
            'group_std': float(data.get('group_std', 1.0)),
            'sig_level': float(data.get('sig_level', 0.05))
        }
        
        # Generate plot using service
        result = VisualizationService.generate_anova_plot_data(session, plot_params)
        
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': result.get('error', 'Unknown error')}, status=400)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



