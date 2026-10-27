from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone

from .models import AdminUser, PasswordResetToken


@admin.register(AdminUser)
class AdminUserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'full_name', 'role', 'is_active',
        'failed_login_attempts', 'is_locked_display', 'last_login_at'
    )
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'full_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login_at', 'last_login_ip')

    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Informasi Pribadi', {'fields': ('full_name',)}),
        ('Peran & Akses', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Keamanan', {'fields': ('failed_login_attempts', 'locked_until')}),
        ('Audit', {'fields': ('created_at', 'updated_at', 'last_login_at', 'last_login_ip')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )

    def is_locked_display(self, obj):
        if obj.is_locked:
            return format_html('<span style="color:red;">🔒 Terkunci</span>')
        return format_html('<span style="color:green;">✓ Aktif</span>')
    is_locked_display.short_description = 'Status Kunci'

    actions = ['unlock_accounts']

    def unlock_accounts(self, request, queryset):
        queryset.update(failed_login_attempts=0, locked_until=None)
        self.message_user(request, f'{queryset.count()} akun berhasil dibuka kuncinya.')
    unlock_accounts.short_description = 'Buka kunci akun terpilih'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'used_at', 'is_valid_display')
    list_filter = ('used_at',)
    search_fields = ('user__email',)
    readonly_fields = ('id', 'token', 'created_at')
    ordering = ('-created_at',)

    def is_valid_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:green;">✓ Valid</span>')
        return format_html('<span style="color:red;">✗ Tidak Valid</span>')
    is_valid_display.short_description = 'Valid'
