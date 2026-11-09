from django.urls import path

from indicators import dashboard_views, feedback_views, source_admin_views, views

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
]
