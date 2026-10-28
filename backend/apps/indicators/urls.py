from django.urls import path

from .views import SourceTraceView

urlpatterns = [
    path('<str:code>/data-points/<str:data_point_id>/source-trace/', SourceTraceView.as_view(), name='source-trace-current'),
    path('<str:code>/data-points/<str:data_point_id>/source-trace/revisions/', SourceTraceView.as_view(kind='history'), name='source-trace-history'),
    path('<str:code>/data-points/<str:data_point_id>/source-trace/revisions/<str:revision_id>/', SourceTraceView.as_view(kind='revision'), name='source-trace-revision'),
    path('<str:code>/data-points/<str:data_point_id>/source-trace/<path:invalid_path>', SourceTraceView.as_view(kind='not_found')),
]
