from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # API v1
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/indicators/', include('apps.indicators.urls')),
    path('api/v1/feedback/', include('apps.feedback.urls')),
]
