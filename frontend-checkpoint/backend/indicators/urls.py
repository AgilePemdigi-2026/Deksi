from django.urls import path

from indicators import views


urlpatterns = [
    path("status/", views.system_status, name="system-status"),
    path("system/update-status/", views.update_status, name="update-status"),
    path("system/bps-status/", views.bps_status, name="bps-status"),
    path("indicators/", views.indicator_summary, name="indicator-summary"),
    path("indicators/latest-periods/", views.latest_periods, name="latest-periods"),
    path("indicators/<str:code>/trend/", views.indicator_trend, name="indicator-trend"),
    path("indicators/<str:code>/source-trace/", views.indicator_source_trace, name="indicator-source-trace"),
    path(
        "indicators/<str:code>/raw-file/<int:raw_file_id>/",
        views.raw_file_download,
        name="indicator-raw-file",
    ),
]
