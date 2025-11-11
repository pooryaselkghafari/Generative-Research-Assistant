from django.urls import path
from engine import views
from engine.dataprep import views as dataprep_views   # ← absolute import

from .views import (
        landing_view, page_view, robots_txt, sitemap_xml, index, edit_session, run_analysis, download_file,
        upload_dataset, delete_dataset, delete_session, bulk_delete_sessions, generate_spotlight_plot,
        generate_correlation_heatmap, get_dataset_variables, update_sessions_for_variable_rename,
        preview_drop_rows, apply_drop_rows, merge_datasets, calculate_summary_stats, visualize_data,
        run_bma_analysis, run_anova_analysis, generate_anova_plot_view, download_session_history_view,
        run_varx_analysis, generate_varx_irf_view, generate_varx_irf_data_view, ai_chat, add_model_errors_to_dataset,
        privacy_policy_view, terms_of_service_view
    )

urlpatterns = [
    path('', landing_view, name='landing'),
    path('page/<slug:slug>/', page_view, name='page_view'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('app/', index, name='index'),
    path('session/<int:pk>/', edit_session, name='edit_session'),
    path('session/delete/<int:pk>/', delete_session, name='delete_session'),  # ← add this
    path('sessions/bulk-delete/', bulk_delete_sessions, name='bulk_delete_sessions'),
    path('run/', run_analysis, name='run'),
    path('visualize/', visualize_data, name='visualize'),
    path('datasets/upload/', upload_dataset, name='upload_dataset'),
    path('datasets/delete/<int:pk>/', delete_dataset, name='delete_dataset'),
    path('dl/<path:fname>/', download_file, name='download_file'),
    path('dataprep/<int:dataset_id>/', dataprep_views.open_cleaner, name='dataprep_open'),
    path('dataprep/<int:dataset_id>/apply/', dataprep_views.apply_cleaning, name='dataprep_apply'),
    path('dataprep/normalize/<int:dataset_id>/', dataprep_views.normalize_columns, name='dataprep_normalize'),
    path('dataprep/merge-columns-preview/<int:dataset_id>/', dataprep_views.merge_columns_preview, name='dataprep_merge_columns_preview'),
    path('dataprep/merge-columns/<int:dataset_id>/', dataprep_views.merge_columns, name='dataprep_merge_columns'),
    path('dataprep/get-column-values/<int:dataset_id>/', dataprep_views.get_column_values, name='dataprep_get_column_values'),
    path('dataprep/apply-column-coding/<int:dataset_id>/', dataprep_views.apply_column_coding, name='dataprep_apply_column_coding'),
    path('dataprep/drop-columns/<int:dataset_id>/', dataprep_views.drop_columns, name='dataprep_drop_columns'),
    path('dataprep/detect-date-formats/<int:dataset_id>/', dataprep_views.detect_date_formats_api, name='dataprep_detect_date_formats'),
    path('dataprep/convert-date-format/<int:dataset_id>/', dataprep_views.convert_date_format_api, name='dataprep_convert_date_format'),
    path('session/<int:session_id>/spotlight/', generate_spotlight_plot, name='generate_spotlight_plot'),
    path('session/<int:session_id>/correlation-heatmap/', generate_correlation_heatmap, name='generate_correlation_heatmap'),
    path('api/dataset/<int:dataset_id>/variables/', get_dataset_variables, name='get_dataset_variables'),
    path('api/dataset/<int:dataset_id>/update-sessions/', update_sessions_for_variable_rename, name='update_sessions_for_variable_rename'),
    path('api/dataset/<int:dataset_id>/preview-drop/', preview_drop_rows, name='preview_drop_rows'),
    path('api/dataset/<int:dataset_id>/apply-drop/', apply_drop_rows, name='apply_drop_rows'),
    path('api/dataset/<int:dataset_id>/fix-stationary/', dataprep_views.fix_stationary, name='fix_stationary'),
    path('api/datasets/merge/', merge_datasets, name='merge_datasets'),
    path('api/session/<int:session_id>/calculate-summary-stats/', views.calculate_summary_stats, name='calculate_summary_stats'),
    path('cancel-bayesian-analysis/', views.cancel_bayesian_analysis, name='cancel_bayesian_analysis'),
    path('bma/', run_bma_analysis, name='run_bma_analysis'),
    path('anova/', run_anova_analysis, name='run_anova_analysis'),
    path('session/<int:session_id>/anova-plot/', generate_anova_plot_view, name='generate_anova_plot'),
    path('varx/', run_varx_analysis, name='run_varx_analysis'),
    path('session/<int:session_id>/varx-irf/', generate_varx_irf_view, name='generate_varx_irf'),
    path('session/<int:session_id>/varx-irf-data/', generate_varx_irf_data_view, name='generate_varx_irf_data'),
    path('session/<int:session_id>/history/', download_session_history_view, name='download_session_history'),
    path('session/<int:session_id>/add-model-errors/', add_model_errors_to_dataset, name='add_model_errors_to_dataset'),
    path('api/ai-chat/', ai_chat, name='ai_chat'),
    # Privacy and Legal
    path('privacy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms/', views.terms_of_service_view, name='terms_of_service'),
]

