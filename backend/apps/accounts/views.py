import logging
import secrets
from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .models import AdminUser
from .serializers import LoginSerializer, AdminUserSerializer

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Ambil IP asli dari request (support reverse proxy)."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LoginThrottle(AnonRateThrottle):
    rate = '5/minute'
    scope = 'login'


class LoginView(APIView):
    """
    UC-01: Login Admin.
    POST /api/v1/auth/login/
    Body: { "email": "...", "password": "..." }
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Login gagal.',
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.validated_data['user']
        ip = get_client_ip(request)

        # Catat login dan reset percobaan gagal
        user.record_login(ip_address=ip)

        # Buat atau ambil token DRF
        token, _ = Token.objects.get_or_create(user=user)

        # Buat session Django
        auth_login(request, user)

        logger.info(f"Login berhasil: {user.email} dari IP {ip}")

        return Response(
            {
                'success': True,
                'message': 'Login berhasil.',
                'data': {
                    'token': token.key,
                    'user': AdminUserSerializer(user).data,
                },
            },
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """
    UC-01: Logout Admin.
    POST /api/v1/auth/logout/
    Header: Authorization: Token <key>
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Hapus token DRF
        try:
            request.user.auth_token.delete()
        except Exception:
            pass

        # Hapus session Django
        auth_logout(request)

        logger.info(f"Logout: {request.user.email}")

        return Response(
            {
                'success': True,
                'message': 'Logout berhasil.',
            },
            status=status.HTTP_200_OK
        )


class MeView(APIView):
    """
    Profil Admin yang sedang login.
    GET /api/v1/auth/me/
    Header: Authorization: Token <key>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                'success': True,
                'data': AdminUserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK
        )
