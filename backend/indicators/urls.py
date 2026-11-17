from django.urls import path

from indicators import (
    bulk_candidate_views,
    candidate_views,
    dashboard_views,
    feedback_views,
    resync_views,
    schedule_views,
    source_admin_views,
    sync_history_views,
    views,
)

urlpatterns = [
    # ── Sistem ──────────────────────────────────────────────────────────────
    path("status/", views.system_status, name="system-status"),
    path("system/update-status/", views.update_status, name="update-status"),
    path("system/bps-status/", views.bps_status, name="bps-status"),

    # ── Indikator ────────────────────────────────────────────────────────────
    path("indicators/", views.indicator_summary, name="indicator-summary"),
    path("indicators/latest-periods/", views.latest_periods, name="latest-periods"),
    path("indicators/<str:code>/trend/", views.indicator_trend, name="indicator-trend"),
    path("indicators/<str:code>/source-trace/", views.indicator_source_trace, name="indicator-source-trace"),
    path(
        "indicators/<str:code>/raw-file/<int:raw_file_id>/",
        views.raw_file_download,
        name="indicator-raw-file",
    ),
    path("indicators/dashboard/", dashboard_views.indicator_dashboard_filter, name="indicator-dashboard-filter"),
    path("indicators/categories/", dashboard_views.indicator_categories, name="indicator-categories"),
    path("feedback/", feedback_views.submit_feedback, name="feedback-submit"),
    path("feedback/categories/", feedback_views.feedback_categories, name="feedback-categories"),

    # ── Fitur 9: Daftar Sumber Data / Source Trace ──────────────────────────
    path("sources/", views.source_list, name="source-list"),
    path("sources/<str:source_id>/", views.source_detail, name="source-detail"),
    path(
        "sources/<str:source_id>/indicators/",
        views.source_indicators,
        name="source-indicators",
    ),

    # ── Fitur 10-11: Kelola Sumber Data (Admin, session auth + staf) ─────────
    path("admin/sync-history/", sync_history_views.admin_sync_history, name="admin-sync-history"),
    path("admin/resync-jobs/<int:job_id>/", resync_views.resync_status, name="admin-resync-status"),
    path("admin/resync-jobs/<int:job_id>/reconcile/", resync_views.reconcile_resync, name="admin-resync-reconcile"),
    path("admin/sources/<str:source_id>/resync/", resync_views.request_resync, name="admin-source-resync"),
    path("admin/sources/<str:source_id>/resync-active/", resync_views.active_resync, name="admin-source-resync-active"),
    path("admin/sources/<str:source_id>/candidates/", candidate_views.candidate_list, name="admin-candidate-list"),
    path("admin/sources/<str:source_id>/candidates/bulk-preview/",
         bulk_candidate_views.bulk_candidate_preview, name="admin-candidate-bulk-preview"),
    path("admin/sources/<str:source_id>/candidates/bulk-review/active/",
         bulk_candidate_views.bulk_candidate_active, name="admin-candidate-bulk-active"),
    path("admin/sources/<str:source_id>/candidates/bulk-review/<uuid:batch_id>/confirm/",
         bulk_candidate_views.bulk_candidate_confirm, name="admin-candidate-bulk-confirm"),
    path("admin/sources/<str:source_id>/candidates/bulk-review/<uuid:batch_id>/reconcile/",
         bulk_candidate_views.bulk_candidate_reconcile, name="admin-candidate-bulk-reconcile"),
    path("admin/sources/<str:source_id>/candidates/bulk-review/<uuid:batch_id>/",
         bulk_candidate_views.bulk_candidate_status, name="admin-candidate-bulk-status"),
    path("admin/sources/<str:source_id>/candidates/<int:candidate_id>/",
         candidate_views.candidate_detail, name="admin-candidate-detail"),
    path("admin/sources/<str:source_id>/candidates/<int:candidate_id>/review/",
         candidate_views.candidate_review, name="admin-candidate-review"),
    path("admin/session/", source_admin_views.admin_session, name="admin-session"),
    path("admin/login/", source_admin_views.admin_login, name="admin-login"),
    path("admin/logout/", source_admin_views.admin_logout, name="admin-logout"),
    path(
        "admin/sources/acquisition-methods/",
        source_admin_views.acquisition_methods,
        name="admin-acquisition-methods",
    ),
    path("admin/sources/", source_admin_views.admin_source_list, name="admin-source-list"),
    path(
        "admin/sources/create/",
        source_admin_views.admin_source_create,
        name="admin-source-create",
    ),
    path(
        "admin/sources/<str:source_id>/",
        source_admin_views.admin_source_detail,
        name="admin-source-detail",
    ),
    path(
        "admin/sources/<str:source_id>/revisions/",
        source_admin_views.admin_source_revisions,
        name="admin-source-revisions",
    ),
    path(
        "admin/sources/<str:source_id>/update/",
        source_admin_views.admin_source_update,
        name="admin-source-update",
    ),

    # ── Feature 23: Konfigurasi Jadwal Pembaruan ──────────────────────────
    path("admin/schedules/", schedule_views.schedule_list, name="admin-schedule-list"),
    path("admin/schedules/next/", schedule_views.schedule_next, name="admin-schedule-next"),
    path("admin/schedules/<str:source_id>/", schedule_views.schedule_update, name="admin-schedule-update"),

    # ── Fitur 15-18: Daftar, Detail, Pencarian, dan Status Umpan Balik ──────
    path("admin/feedback/", feedback_views.admin_feedback_list, name="admin-feedback-list"),
    path(
        "admin/feedback/<int:feedback_id>/",
        feedback_views.admin_feedback_detail,
        name="admin-feedback-detail",
    ),
    path(
        "admin/feedback/<int:feedback_id>/status/",
        feedback_views.admin_feedback_update_status,
        name="admin-feedback-status",
    ),
]
