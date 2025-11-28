"""
View modules for the engine app.

This package contains views organized by functionality:
- pages: Landing pages, static pages, robots.txt, sitemap
- sessions: Session management (list, edit, delete)
- datasets: Dataset management (upload, delete, variables)
- analysis: Analysis execution (run_analysis, BMA, ANOVA, VARX)
- visualization: Plot generation and visualization
- utils: Utility functions
"""
from .pages import (
    landing_view,
    page_view,
    robots_txt,
    sitemap_xml,
    privacy_policy_view,
    terms_of_service_view,
)
from .sessions import (
    index,
    edit_session,
    delete_session,
    bulk_delete_sessions,
    download_session_history_view,
    _list_context,
)
from .datasets import (
    upload_dataset,
    delete_dataset,
    get_dataset_variables,
    update_sessions_for_variable_rename,
    preview_drop_rows,
    apply_drop_rows,
    merge_datasets,
)
from .analysis import (
    run_analysis,
    run_bma_analysis,
    run_anova_analysis,
    run_varx_analysis,
    generate_varx_irf_view,
    generate_varx_irf_data_view,
    calculate_summary_stats,
    add_model_errors_to_dataset,
    ai_chat,
    cancel_bayesian_analysis,
)
from .visualization import (
    visualize_data,
    generate_plot,
    generate_spotlight_plot,
    generate_correlation_heatmap,
    generate_anova_plot_view,
    _generate_multinomial_ordinal_spotlight_from_predictions,
)
from .utils import download_file

__all__ = [
    # Pages
    'landing_view',
    'page_view',
    'robots_txt',
    'sitemap_xml',
    'privacy_policy_view',
    'terms_of_service_view',
    # Sessions
    'index',
    'edit_session',
    'delete_session',
    'bulk_delete_sessions',
    'download_session_history_view',
    '_list_context',
    # Datasets
    'upload_dataset',
    'delete_dataset',
    'get_dataset_variables',
    'update_sessions_for_variable_rename',
    'preview_drop_rows',
    'apply_drop_rows',
    'merge_datasets',
    # Analysis
    'run_analysis',
    'run_bma_analysis',
    'run_anova_analysis',
    'run_varx_analysis',
    'generate_varx_irf_view',
    'generate_varx_irf_data_view',
    'calculate_summary_stats',
    'add_model_errors_to_dataset',
    'ai_chat',
    'cancel_bayesian_analysis',
    # Visualization
    'visualize_data',
    'generate_plot',
    'generate_spotlight_plot',
    'generate_correlation_heatmap',
    'generate_anova_plot_view',
    '_generate_multinomial_ordinal_spotlight_from_predictions',
    # Utils
    'download_file',
]



