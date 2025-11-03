#!/usr/bin/env python3
"""
History tracking module for StatBox sessions.

This module tracks all user actions and modifications in a session,
including equations, result tables, and plots, and generates downloadable
history files.
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string


class SessionHistory:
    """Tracks and manages session history."""
    
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.history_file = os.path.join(settings.MEDIA_ROOT, 'history', f'session_{session_id}_history.json')
        self.history_data = self._load_history()
    
    def _load_history(self) -> Dict[str, Any]:
        """Load existing history data or create new structure."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return {
            'session_id': self.session_id,
            'created_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat(),
            'iterations': []
        }
    
    def _save_history(self):
        """Save history data to file."""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.history_data['last_updated'] = datetime.datetime.now().isoformat()
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history_data, f, indent=2, ensure_ascii=False)
    
    def add_iteration(self, 
                     iteration_type: str,
                     equation: str,
                     analysis_type: str = None,
                     results_data: Dict[str, Any] = None,
                     plots_added: List[str] = None,
                     modifications: Dict[str, Any] = None,
                     notes: str = None):
        """Add a new iteration to the session history."""
        
        iteration = {
            'iteration_number': len(self.history_data['iterations']) + 1,
            'timestamp': datetime.datetime.now().isoformat(),
            'type': iteration_type,  # 'initial', 'modification', 'plot_added', etc.
            'equation': equation,
            'analysis_type': analysis_type,
            'results_summary': self._extract_results_summary(results_data),
            'plots_added': plots_added or [],
            'modifications': modifications or {},
            'notes': notes
        }
        
        self.history_data['iterations'].append(iteration)
        self._save_history()
    
    def _extract_results_summary(self, results_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key summary information from results data."""
        if not results_data:
            return {}
        
        summary = {}
        
        # Extract model statistics
        if 'model_stats' in results_data:
            model_stats = results_data['model_stats']
            summary['model_stats'] = {
                'N': model_stats.get('N'),
                'R2': model_stats.get('R²'),
                'Adj_R2': model_stats.get('Adj_R²'),
                'AIC': model_stats.get('AIC'),
                'BIC': model_stats.get('BIC')
            }
        
        # Extract BMA specific stats
        if 'weighted_R2' in results_data:
            summary['bma_stats'] = {
                'weighted_R2': results_data.get('weighted_R2'),
                'best_model_fit': results_data.get('best_model_fit'),
                'n_models_evaluated': results_data.get('n_models_evaluated')
            }
        
        # Extract variable information
        if 'bma_summary' in results_data:
            summary['variable_summary'] = {
                'n_variables': len(results_data['bma_summary']),
                'top_variables': results_data['bma_summary'][:3] if results_data['bma_summary'] else []
            }
        
        # Extract complete results table data
        if 'model_cols' in results_data and 'model_matrix' in results_data:
            summary['results_table'] = {
                'columns': results_data['model_cols'],
                'rows': results_data['model_matrix']
            }
        
        # Extract BMA summary table
        if 'bma_summary' in results_data:
            summary['bma_table'] = results_data['bma_summary']
        
        return summary
    
    def get_history_text(self) -> str:
        """Generate formatted text history for download."""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append(f"STATBOX SESSION HISTORY")
        lines.append(f"Session ID: {self.session_id}")
        lines.append(f"Created: {self.history_data['created_at']}")
        lines.append(f"Last Updated: {self.history_data['last_updated']}")
        lines.append("=" * 80)
        lines.append("")
        
        # Iterations
        for i, iteration in enumerate(self.history_data['iterations'], 1):
            lines.append(f"ITERATION {i}")
            lines.append("-" * 40)
            lines.append(f"Timestamp: {iteration['timestamp']}")
            lines.append(f"Type: {iteration['type']}")
            lines.append(f"Analysis Type: {iteration.get('analysis_type', 'N/A')}")
            lines.append("")
            
            # Equation
            lines.append("EQUATION:")
            lines.append(f"  {iteration['equation']}")
            lines.append("")
            
            # Results Summary
            if iteration['results_summary']:
                summary = iteration['results_summary']
                
                # Model stats
                if 'model_stats' in summary:
                    lines.append("MODEL STATISTICS:")
                    stats = summary['model_stats']
                    lines.append(f"  Sample Size (N): {stats.get('N', 'N/A')}")
                    lines.append(f"  R²: {stats.get('R2', 'N/A')}")
                    lines.append(f"  Adjusted R²: {stats.get('Adj_R2', 'N/A')}")
                    lines.append(f"  AIC: {stats.get('AIC', 'N/A')}")
                    lines.append(f"  BIC: {stats.get('BIC', 'N/A')}")
                    lines.append("")
                
                # BMA stats
                if 'bma_stats' in summary:
                    lines.append("BMA STATISTICS:")
                    bma_stats = summary['bma_stats']
                    lines.append(f"  Weighted R²: {bma_stats.get('weighted_R2', 'N/A')}")
                    lines.append(f"  Models Evaluated: {bma_stats.get('n_models_evaluated', 'N/A')}")
                    if bma_stats.get('best_model_fit'):
                        best_fit = bma_stats['best_model_fit']
                        lines.append(f"  Best Model Index: {best_fit.get('model_index', 'N/A')}")
                        lines.append(f"  Best Model R²: {best_fit.get('R2', 'N/A')}")
                    lines.append("")
                
                # Results Table (Regression Table)
                if 'results_table' in summary:
                    lines.append("REGRESSION TABLE:")
                    table_data = summary['results_table']
                    columns = table_data['columns']
                    rows = table_data['rows']
                    
                    if columns and rows:
                        # Calculate column widths
                        col_widths = []
                        for i, col in enumerate(columns):
                            max_width = len(str(col))
                            for row in rows:
                                if i < len(row):
                                    max_width = max(max_width, len(str(row[i])))
                            col_widths.append(max_width + 2)  # Add padding
                        
                        # Create header
                        header_line = "  "
                        separator_line = "  "
                        for i, col in enumerate(columns):
                            header_line += f"{col:<{col_widths[i]}}"
                            separator_line += "-" * col_widths[i]
                        lines.append(header_line)
                        lines.append(separator_line)
                        
                        # Add rows
                        for row in rows:
                            row_line = "  "
                            for i, cell in enumerate(row):
                                if i < len(col_widths):
                                    row_line += f"{str(cell):<{col_widths[i]}}"
                            lines.append(row_line)
                    else:
                        lines.append("  No table data available")
                    lines.append("")
                
                # BMA Summary Table
                if 'bma_table' in summary:
                    lines.append("BMA SUMMARY TABLE:")
                    bma_table = summary['bma_table']
                    
                    if bma_table:
                        # Find the maximum width for each column
                        if isinstance(bma_table[0], dict):
                            # Dictionary format
                            columns = list(bma_table[0].keys())
                            col_widths = {}
                            for col in columns:
                                max_width = len(str(col))
                                for row in bma_table:
                                    max_width = max(max_width, len(str(row.get(col, ''))))
                                col_widths[col] = max_width + 2
                            
                            # Create header
                            header_line = "  "
                            separator_line = "  "
                            for col in columns:
                                header_line += f"{col:<{col_widths[col]}}"
                                separator_line += "-" * col_widths[col]
                            lines.append(header_line)
                            lines.append(separator_line)
                            
                            # Add rows
                            for row in bma_table:
                                row_line = "  "
                                for col in columns:
                                    row_line += f"{str(row.get(col, '')):<{col_widths[col]}}"
                                lines.append(row_line)
                        else:
                            # List format
                            for row in bma_table:
                                lines.append(f"  {row}")
                    else:
                        lines.append("  No BMA table data available")
                    lines.append("")
                
                # Variable summary
                if 'variable_summary' in summary:
                    lines.append("VARIABLE SUMMARY:")
                    var_summary = summary['variable_summary']
                    lines.append(f"  Number of Variables: {var_summary.get('n_variables', 'N/A')}")
                    if var_summary.get('top_variables'):
                        lines.append("  Top Variables:")
                        for var in var_summary['top_variables']:
                            lines.append(f"    - {var}")
                    lines.append("")
            
            # Plots Added
            if iteration['plots_added']:
                lines.append("PLOTS ADDED:")
                for plot in iteration['plots_added']:
                    lines.append(f"  - {plot}")
                lines.append("")
            
            lines.append("=" * 80)
            lines.append("")
        
        return "\n".join(lines)
    
    def get_history_json(self) -> Dict[str, Any]:
        """Get raw history data as JSON."""
        return self.history_data
    
    def clear_history(self):
        """Clear all history for this session."""
        self.history_data = {
            'session_id': self.session_id,
            'created_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat(),
            'iterations': []
        }
        self._save_history()


def track_session_iteration(session_id: int,
                          iteration_type: str,
                          equation: str,
                          analysis_type: str = None,
                          results_data: Dict[str, Any] = None,
                          plots_added: List[str] = None,
                          modifications: Dict[str, Any] = None,
                          notes: str = None):
    """Convenience function to track a session iteration."""
    history = SessionHistory(session_id)
    history.add_iteration(
        iteration_type=iteration_type,
        equation=equation,
        analysis_type=analysis_type,
        results_data=results_data,
        plots_added=plots_added,
        modifications=modifications,
        notes=notes
    )


def get_session_history(session_id: int) -> SessionHistory:
    """Get session history object."""
    return SessionHistory(session_id)


def download_session_history(session_id: int, format: str = 'text') -> HttpResponse:
    """Generate downloadable history file."""
    history = SessionHistory(session_id)
    
    if format == 'text':
        content = history.get_history_text()
        filename = f'session_{session_id}_history.txt'
        content_type = 'text/plain'
    elif format == 'json':
        content = json.dumps(history.get_history_json(), indent=2, ensure_ascii=False)
        filename = f'session_{session_id}_history.json'
        content_type = 'application/json'
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
