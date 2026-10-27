import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class AdminUserManager(BaseUserManager):
    """Custom manager for AdminUser."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email wajib diisi.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', AdminUser.Role.SUPERADMIN)
        return self.create_user(email, password, **extra_fields)


class AdminUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for DEKSI Admin.
    User publik tidak memiliki akun; autentikasi hanya untuk Admin.
    """

    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        REVIEWER = 'reviewer', 'Reviewer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name='Alamat Email')
    full_name = models.CharField(max_length=150, verbose_name='Nama Lengkap')
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
        verbose_name='Peran'
    )

    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_staff = models.BooleanField(default=False, verbose_name='Staff')

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Dibuat Pada')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Diperbarui Pada')
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name='Login Terakhir')
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Login Terakhir')

    # Account lock fields
    failed_login_attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Percobaan Login Gagal'
    )
    locked_until = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Terkunci Hingga'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = AdminUserManager()

    class Meta:
        db_table = 'admin_users'
        verbose_name = 'Admin'
        verbose_name_plural = 'Admin'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def is_locked(self):
        """Cek apakah akun sedang terkunci."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def increment_failed_attempts(self):
        """Tambah percobaan gagal dan kunci akun jika melebihi batas."""
        from django.conf import settings
        max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        lockout_duration = getattr(settings, 'LOCKOUT_DURATION_MINUTES', 15)

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_duration)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def reset_failed_attempts(self):
        """Reset percobaan gagal setelah login berhasil."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def record_login(self, ip_address=None):
        """Catat waktu dan IP login terakhir."""
        self.last_login_at = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.reset_failed_attempts()
        self.save(update_fields=['last_login_at', 'last_login_ip', 'failed_login_attempts', 'locked_until'])


class PasswordResetToken(models.Model):
    """Token untuk reset kata sandi Admin."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        AdminUser,
        on_delete=models.CASCADE,
        related_name='reset_tokens',
        verbose_name='Admin'
    )
    token = models.CharField(max_length=64, unique=True, verbose_name='Token')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Dibuat Pada')
    expires_at = models.DateTimeField(verbose_name='Kedaluwarsa Pada')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='Digunakan Pada')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Peminta')

    class Meta:
        db_table = 'password_reset_tokens'
        verbose_name = 'Token Reset Kata Sandi'
        verbose_name_plural = 'Token Reset Kata Sandi'
        ordering = ['-created_at']

    def __str__(self):
        return f"Token reset untuk {self.user.email}"

    @property
    def is_valid(self):
        """Token valid bila belum digunakan dan belum kedaluwarsa."""
        return self.used_at is None and self.expires_at > timezone.now()

    def mark_used(self):
        """Tandai token sebagai sudah digunakan."""
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])
