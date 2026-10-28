from django.urls import path
from .views import IndicatorDetailRead

urlpatterns = [
    path('<str:code>/detail/', IndicatorDetailRead.as_view(kind='current'), name='indicator-detail-current'),
    path('<str:code>/history/', IndicatorDetailRead.as_view(kind='history'), name='indicator-detail-history'),
    path('<str:code>/data-points/<str:data_point_id>/revisions/<str:revision_id>/',
         IndicatorDetailRead.as_view(kind='revision'), name='indicator-detail-revision'),
]
