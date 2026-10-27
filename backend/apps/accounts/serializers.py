import secrets
import logging
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import serializers

from .models import AdminUser, PasswordResetToken

logger = logging.getLogger(__name__)


class LoginSerializer(serializers.Serializer):
    """Serializer untuk validasi kredensial login Admin."""

    email = serializers.EmailField(
        label='Email',
        error_messages={'required': 'Email wajib diisi.', 'invalid': 'Format email tidak valid.'}
    )
    password = serializers.CharField(
        label='Kata Sandi',
        style={'input_type': 'password'},
        trim_whitespace=False,
        error_messages={'required': 'Kata sandi wajib diisi.'}
    )

    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password', '')

        # Cek apakah akun ada
        try:
            user = AdminUser.objects.get(email=email)
        except AdminUser.DoesNotExist:
            raise serializers.ValidationError(
                {'non_field_errors': ['Email atau kata sandi salah.']},
                code='authorization'
            )

        # Cek status akun
        if not user.is_active:
            raise serializers.ValidationError(
                {'non_field_errors': ['Akun Anda telah dinonaktifkan. Hubungi administrator.']},
                code='account_inactive'
            )

        # Cek apakah akun terkunci
        if user.is_locked:
            remaining = int((user.locked_until - timezone.now()).total_seconds() / 60) + 1
            raise serializers.ValidationError(
                {
                    'non_field_errors': [
                        f'Akun terkunci sementara karena terlalu banyak percobaan gagal. '
                        f'Coba lagi dalam {remaining} menit.'
                    ]
                },
                code='account_locked'
            )

        # Validasi password
        authenticated_user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )

        if not authenticated_user:
            user.increment_failed_attempts()
            max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
            remaining_attempts = max(0, max_attempts - user.failed_login_attempts)

            if user.is_locked:
                raise serializers.ValidationError(
                    {'non_field_errors': [
                        'Akun terkunci karena terlalu banyak percobaan gagal. '
                        'Coba lagi dalam 15 menit atau reset kata sandi Anda.'
                    ]},
                    code='account_locked'
                )

            msg = f'Email atau kata sandi salah.'
            if remaining_attempts > 0:
                msg += f' Sisa percobaan: {remaining_attempts}.'
            raise serializers.ValidationError(
                {'non_field_errors': [msg]},
                code='authorization'
            )

        attrs['user'] = authenticated_user
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer data profil Admin (read-only)."""

    class Meta:
        model = AdminUser
        fields = [
            'id', 'email', 'full_name', 'role',
            'is_active', 'last_login_at', 'created_at'
        ]
        read_only_fields = fields


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer untuk permintaan lupa kata sandi."""

    email = serializers.EmailField(
        label='Email',
        error_messages={
            'required': 'Email wajib diisi.',
            'invalid': 'Format email tidak valid.'
        }
    )

    def validate_email(self, value):
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer untuk reset kata sandi menggunakan token."""

    token = serializers.CharField(
        label='Token',
        error_messages={'required': 'Token reset wajib diisi.'}
    )
    new_password = serializers.CharField(
        label='Kata Sandi Baru',
        min_length=8,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Kata sandi baru wajib diisi.',
            'min_length': 'Kata sandi minimal 8 karakter.'
        }
    )
    confirm_password = serializers.CharField(
        label='Konfirmasi Kata Sandi',
        style={'input_type': 'password'},
        error_messages={'required': 'Konfirmasi kata sandi wajib diisi.'}
    )

    def validate(self, attrs):
        token_value = attrs.get('token')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {'confirm_password': 'Kata sandi baru dan konfirmasi tidak cocok.'}
            )

        # Validasi token
        try:
            token_obj = PasswordResetToken.objects.select_related('user').get(token=token_value)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                {'token': 'Token reset tidak valid atau sudah kedaluwarsa.'}
            )

        if not token_obj.is_valid:
            raise serializers.ValidationError(
                {'token': 'Token reset sudah tidak berlaku. Silakan minta ulang.'}
            )

        attrs['token_obj'] = token_obj
        return attrs


class ValidateResetTokenSerializer(serializers.Serializer):
    """Serializer untuk validasi token sebelum form reset ditampilkan."""

    token = serializers.CharField(error_messages={'required': 'Token wajib diisi.'})

    def validate_token(self, value):
        try:
            token_obj = PasswordResetToken.objects.select_related('user').get(token=value)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError('Token tidak valid atau sudah kedaluwarsa.')

        if not token_obj.is_valid:
            raise serializers.ValidationError('Token sudah tidak berlaku. Silakan minta ulang tautan reset.')

        return value
