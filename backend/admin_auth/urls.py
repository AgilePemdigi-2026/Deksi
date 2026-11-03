from django.urls import path

from . import password_reset, views

app_name = "admin_auth"
urlpatterns = [
    path("csrf/", views.csrf_bootstrap, name="csrf"),
    path("login/", views.login_view, name="login"),
    path("session/", views.session_view, name="session"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/request/", password_reset.request_reset, name="password_reset_request"),
    path("password-reset/check/", password_reset.check_reset, name="password_reset_check"),
    path("password-reset/confirm/", password_reset.confirm_reset, name="password_reset_confirm"),
]
