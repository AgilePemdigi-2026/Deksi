from django.urls import path
from .views import LoginView, LogoutView, MeView
from .views_password import ForgotPasswordView, ValidateResetTokenView, ResetPasswordView

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),

    # Reset Password
    path('forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),
    path('reset-password/validate/', ValidateResetTokenView.as_view(), name='auth-reset-password-validate'),
]
