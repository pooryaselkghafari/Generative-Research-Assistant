# Visualization module for generating plots and charts
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

def get_color_palette(n_colors):
    """Generate a color palette with distinct colors for grouping"""
    # Use Plotly's default color sequence for better consistency
    default_colors = px.colors.qualitative.Set1
    if n_colors <= len(default_colors):
        return default_colors[:n_colors]
    
    # If we need more colors, cycle through the palette
    colors = []
    for i in range(n_colors):
        colors.append(default_colors[i % len(default_colors)])
    return colors

def generate_scatter_plot(df, x_var, y_var, group_var=None, trendline=False, **kwargs):
    """Generate a scatter plot with optional grouping and trendline"""
    # Extract custom styling options
    x_label = kwargs.get('x_label', x_var)
    y_label = kwargs.get('y_label', y_var)
    point_color = kwargs.get('point_color', '#1f77b4')
    line_style = kwargs.get('line_style', 'solid')
    background_color = kwargs.get('background_color', '#ffffff')
    
    fig = go.Figure()
    
    if group_var and group_var in df.columns:
        # Grouped scatter plot
        groups = df[group_var].dropna().unique()
        colors = get_color_palette(len(groups))
        for i, group in enumerate(groups):
            group_data = df[df[group_var] == group]
            fig.add_trace(go.Scatter(
                x=group_data[x_var],
                y=group_data[y_var],
                mode='markers',
                name=str(group),
                marker=dict(size=8, opacity=0.7, color=colors[i])
            ))
    else:
        # Simple scatter plot
        fig.add_trace(go.Scatter(
            x=df[x_var],
            y=df[y_var],
            mode='markers',
            name='Data',
            marker=dict(size=8, opacity=0.7, color=point_color)
        ))
    
    # Add trendline if requested
    if trendline:
        if group_var and group_var in df.columns:
            groups = df[group_var].dropna().unique()
            colors = get_color_palette(len(groups))
            for i, group in enumerate(groups):
                group_data = df[df[group_var] == group]
                z = np.polyfit(group_data[x_var].dropna(), group_data[y_var].dropna(), 1)
                p = np.poly1d(z)
                x_trend = np.linspace(group_data[x_var].min(), group_data[x_var].max(), 100)
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=p(x_trend),
                    mode='lines',
                    name=f'Trend {group}',
                    line=dict(dash=line_style, color=colors[i])
                ))
        else:
            z = np.polyfit(df[x_var].dropna(), df[y_var].dropna(), 1)
            p = np.poly1d(z)
            x_trend = np.linspace(df[x_var].min(), df[x_var].max(), 100)
            fig.add_trace(go.Scatter(
                x=x_trend,
                y=p(x_trend),
                mode='lines',
                name='Trend',
                line=dict(dash=line_style)
            ))
    
    fig.update_layout(
        title=f'Scatter Plot: {y_label} vs {x_label}',
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor=background_color,
        paper_bgcolor=background_color
    )
    
    return fig

def generate_histogram(df, var, group_var=None, bins=30, **kwargs):
    """Generate a histogram with optional grouping"""
    # Extract custom styling options
    x_label = kwargs.get('x_label', var)
    y_label = kwargs.get('y_label', 'Frequency')
    bar_color = kwargs.get('bar_color', '#1f77b4')
    background_color = kwargs.get('background_color', '#ffffff')
    
    fig = go.Figure()
    
    if group_var and group_var in df.columns:
        # Grouped histogram
        groups = df[group_var].dropna().unique()
        colors = get_color_palette(len(groups))
        for i, group in enumerate(groups):
            group_data = df[df[group_var] == group]
            fig.add_trace(go.Histogram(
                x=group_data[var],
                name=str(group),
                opacity=0.7,
                nbinsx=bins,
                marker=dict(color=colors[i])
            ))
    else:
        # Simple histogram
        fig.add_trace(go.Histogram(
            x=df[var],
            name=var,
            nbinsx=bins,
            marker=dict(color=bar_color)
        ))
    
    fig.update_layout(
        title=f'Histogram: {x_label}',
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        barmode='overlay' if group_var and group_var in df.columns else 'group'
    )
    
    return fig

def generate_bar_chart(df, x_var, y_var=None, group_var=None, **kwargs):
    """Generate a bar chart"""
    # Extract custom styling options
    x_label = kwargs.get('x_label', x_var)
    y_label = kwargs.get('y_label', y_var if y_var else 'Count')
    bar_color = kwargs.get('bar_color', '#1f77b4')
    background_color = kwargs.get('background_color', '#ffffff')
    
    fig = go.Figure()
    
    if y_var and y_var in df.columns:
        # Bar chart with y values
        if group_var and group_var in df.columns:
            groups = df[group_var].dropna().unique()
            colors = get_color_palette(len(groups))
            for i, group in enumerate(groups):
                group_data = df[df[group_var] == group]
                fig.add_trace(go.Bar(
                    x=group_data[x_var],
                    y=group_data[y_var],
                    name=str(group),
                    marker=dict(color=colors[i])
                ))
        else:
            fig.add_trace(go.Bar(
                x=df[x_var],
                y=df[y_var],
                name=y_var,
                marker=dict(color=bar_color)
            ))
    else:
        # Count bar chart
        value_counts = df[x_var].value_counts()
        fig.add_trace(go.Bar(
            x=value_counts.index,
            y=value_counts.values,
            name='Count',
            marker=dict(color=bar_color)
        ))
    
    fig.update_layout(
        title=f'Bar Chart: {x_label}' + (f' vs {y_label}' if y_var else ''),
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor=background_color,
        paper_bgcolor=background_color
    )
    
    return fig

def generate_line_chart(df, x_var, y_var, group_var=None, **kwargs):
    """Generate a line chart"""
    # Extract custom styling options
    x_label = kwargs.get('x_label', x_var)
    y_label = kwargs.get('y_label', y_var)
    line_color = kwargs.get('line_color', '#1f77b4')
    line_style = kwargs.get('line_style', 'solid')
    background_color = kwargs.get('background_color', '#ffffff')
    
    fig = go.Figure()
    
    if group_var and group_var in df.columns:
        # Grouped line chart
        groups = df[group_var].dropna().unique()
        colors = get_color_palette(len(groups))
        for i, group in enumerate(groups):
            group_data = df[df[group_var] == group].sort_values(x_var)
            fig.add_trace(go.Scatter(
                x=group_data[x_var],
                y=group_data[y_var],
                mode='lines+markers',
                name=str(group),
                line=dict(color=colors[i], dash=line_style)
            ))
    else:
        # Simple line chart
        sorted_data = df.sort_values(x_var)
        fig.add_trace(go.Scatter(
            x=sorted_data[x_var],
            y=sorted_data[y_var],
            mode='lines+markers',
            name=y_var,
            line=dict(color=line_color, dash=line_style)
        ))
    
    fig.update_layout(
        title=f'Line Chart: {y_label} vs {x_label}',
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor=background_color,
        paper_bgcolor=background_color
    )
    
    return fig

def generate_pie_chart(df, var, group_var=None, **kwargs):
    """Generate a pie chart"""
    # Extract custom styling options
    color_scheme = kwargs.get('color_scheme', 'default')
    background_color = kwargs.get('background_color', '#ffffff')
    
    fig = go.Figure()
    
    if group_var and group_var in df.columns:
        # Grouped pie chart - create subplots
        groups = df[group_var].dropna().unique()
        n_groups = len(groups)
        cols = min(3, n_groups)
        rows = (n_groups + cols - 1) // cols
        
        fig = make_subplots(
            rows=rows, cols=cols,
            specs=[[{'type': 'domain'} for _ in range(cols)] for _ in range(rows)],
            subplot_titles=[str(group) for group in groups]
        )
        
        for i, group in enumerate(groups):
            group_data = df[df[group_var] == group]
            value_counts = group_data[var].value_counts()
            
            row = i // cols + 1
            col = i % cols + 1
            
            fig.add_trace(go.Pie(
                labels=value_counts.index,
                values=value_counts.values,
                name=str(group)
            ), row=row, col=col)
    else:
        # Simple pie chart
        value_counts = df[var].value_counts()
        fig.add_trace(go.Pie(
            labels=value_counts.index,
            values=value_counts.values,
            name=var
        ))
    
    fig.update_layout(
        title=f'Pie Chart: {var}',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color
    )
    
    return fig

def get_numeric_columns(df):
    """Get list of numeric columns from dataframe"""
    return df.select_dtypes(include=[np.number]).columns.tolist()

def get_categorical_columns(df):
    """Get list of categorical columns from dataframe"""
    return df.select_dtypes(include=['object', 'category']).columns.tolist()

def get_all_columns(df):
    """Get list of all columns from dataframe"""
    return df.columns.tolist()
