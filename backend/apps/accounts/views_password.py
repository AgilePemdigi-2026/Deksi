import secrets
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdminUser, PasswordResetToken
from .serializers import (
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ValidateResetTokenSerializer,
)

logger = logging.getLogger(__name__)


class ForgotPasswordView(APIView):
    """
    UC-01 (Alt): Kirim email reset kata sandi.
    POST /api/v1/auth/forgot-password/
    Body: { "email": "admin@example.com" }

    Selalu return 200 agar email tidak bisa dienumerate.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']

        try:
            user = AdminUser.objects.get(email=email, is_active=True)
            self._send_reset_email(user, request)
        except AdminUser.DoesNotExist:
            # Tetap return 200 agar email tidak bisa dienumerate
            pass

        return Response(
            {
                'success': True,
                'message': (
                    'Jika email terdaftar, tautan reset kata sandi '
                    'akan dikirim dalam beberapa menit.'
                ),
            },
            status=status.HTTP_200_OK
        )

    def _send_reset_email(self, user, request):
        """Buat token dan kirim email reset."""
        # Nonaktifkan token lama yang belum digunakan
        PasswordResetToken.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=timezone.now()
        ).update(expires_at=timezone.now())

        # Buat token baru
        timeout_seconds = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
        token = PasswordResetToken.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            expires_at=timezone.now() + timezone.timedelta(seconds=timeout_seconds),
            ip_address=self._get_ip(request),
        )

        # URL reset untuk frontend
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
        reset_url = f"{frontend_url}/reset-password?token={token.token}"

        expiry_minutes = timeout_seconds // 60

        subject = '[DEKSI] Reset Kata Sandi'
        message = (
            f"Halo {user.full_name},\n\n"
            f"Kami menerima permintaan reset kata sandi untuk akun DEKSI Anda.\n\n"
            f"Klik tautan berikut untuk membuat kata sandi baru:\n"
            f"{reset_url}\n\n"
            f"Tautan ini berlaku selama {expiry_minutes} menit.\n\n"
            f"Jika Anda tidak meminta reset kata sandi, abaikan email ini.\n\n"
            f"— Tim DEKSI"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"Email reset terkirim ke: {user.email}")
        except Exception as e:
            logger.error(f"Gagal kirim email reset ke {user.email}: {e}")

    def _get_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class ValidateResetTokenView(APIView):
    """
    Validasi token sebelum form reset ditampilkan.
    GET /api/v1/auth/reset-password/validate/?token=<token>
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token_value = request.query_params.get('token', '')
        serializer = ValidateResetTokenSerializer(data={'token': token_value})

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'valid': False,
                    'message': serializer.errors.get('token', ['Token tidak valid.'])[0],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'success': True,
                'valid': True,
                'message': 'Token valid. Silakan masukkan kata sandi baru.',
            },
            status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    """
    UC-01 (Alt): Reset kata sandi dengan token.
    POST /api/v1/auth/reset-password/
    Body: { "token": "...", "new_password": "...", "confirm_password": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_obj = serializer.validated_data['token_obj']
        new_password = serializer.validated_data['new_password']
        user = token_obj.user

        # Set kata sandi baru
        user.set_password(new_password)
        # Reset percobaan gagal dan buka kunci
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['password', 'failed_login_attempts', 'locked_until'])

        # Tandai token sudah digunakan
        token_obj.mark_used()

        # Hapus semua token DRF lama agar sesi lama tidak bisa dipakai
        try:
            user.auth_token.delete()
        except Exception:
            pass

        logger.info(f"Kata sandi berhasil direset untuk: {user.email}")

        return Response(
            {
                'success': True,
                'message': 'Kata sandi berhasil diubah. Silakan login dengan kata sandi baru.',
            },
            status=status.HTTP_200_OK
        )
