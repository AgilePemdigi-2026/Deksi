from django.urls import path

from . import views

app_name = "admin_auth"
urlpatterns = [
    path("csrf/", views.csrf_bootstrap, name="csrf"),
    path("login/", views.login_view, name="login"),
    path("session/", views.session_view, name="session"),
    path("logout/", views.logout_view, name="logout"),
]
