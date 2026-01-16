"""
Account admin configuration.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, UserStore


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'code']
    search_fields = ['name', 'code']
    ordering = ['id']


class UserStoreInline(admin.TabularInline):
    model = UserStore
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'display_name', 'role', 'status', 'is_active', 'last_login']
    list_filter = ['status', 'is_active', 'role', 'is_staff']
    search_fields = ['username', 'email', 'display_name', 'phone']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('個人資訊', {'fields': ('display_name', 'email', 'phone')}),
        ('權限', {'fields': ('role', 'status', 'is_active', 'is_staff', 'is_superuser')}),
        ('登入資訊', {'fields': ('last_login', 'last_login_ip', 'login_attempts', 'password_changed_at')}),
        ('時間', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ['last_login', 'last_login_ip', 'login_attempts', 'password_changed_at', 'created_at', 'updated_at']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'display_name', 'password1', 'password2', 'role'),
        }),
    )

    inlines = [UserStoreInline]
