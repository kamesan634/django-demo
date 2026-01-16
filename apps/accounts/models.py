"""
Account models: User, Role, Permission.
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from apps.core.models import TimeStampedModel


class Role(TimeStampedModel):
    """Role model for RBAC."""
    CODE_CHOICES = [
        ('ADMIN', '系統管理員'),
        ('MANAGER', '店長/經理'),
        ('CASHIER', '收銀員'),
        ('WAREHOUSE', '倉管人員'),
        ('PURCHASER', '採購人員'),
        ('VIEWER', '檢視者'),
    ]

    name = models.CharField(max_length=50, verbose_name='角色名稱')
    code = models.CharField(
        max_length=20,
        choices=CODE_CHOICES,
        unique=True,
        verbose_name='角色代碼'
    )
    description = models.TextField(blank=True, verbose_name='描述')
    permissions = models.JSONField(
        default=dict,
        verbose_name='權限設定',
        help_text='格式: {"module_name": ["read", "write", "delete"]}'
    )
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    class Meta:
        db_table = 'roles'
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['id']

    def __str__(self):
        return f'{self.name} ({self.code})'


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, username, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not username:
            raise ValueError('使用者必須有帳號')
        if not email:
            raise ValueError('使用者必須有電子郵件')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Custom User model."""
    STATUS_CHOICES = [
        ('ACTIVE', '啟用'),
        ('INACTIVE', '停用'),
        ('LOCKED', '鎖定'),
    ]

    username = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='帳號'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='電子郵件'
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name='顯示名稱'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='手機號碼'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='角色'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='狀態'
    )

    is_active = models.BooleanField(default=True, verbose_name='啟用')
    is_staff = models.BooleanField(default=False, verbose_name='員工權限')

    # Login tracking
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='最後登入IP'
    )
    login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name='登入嘗試次數'
    )
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='密碼變更時間'
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'display_name']

    class Meta:
        db_table = 'users'
        verbose_name = '使用者'
        verbose_name_plural = '使用者'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.display_name} ({self.username})'

    def has_module_permission(self, module_name, permission_type='read'):
        """Check if user has permission for a module."""
        if self.is_superuser:
            return True
        if not self.role or not self.role.permissions:
            return False
        module_perms = self.role.permissions.get(module_name, [])
        return permission_type in module_perms

    def lock_account(self):
        """Lock the user account."""
        self.status = 'LOCKED'
        self.save(update_fields=['status'])

    def unlock_account(self):
        """Unlock the user account."""
        self.status = 'ACTIVE'
        self.login_attempts = 0
        self.save(update_fields=['status', 'login_attempts'])


class UserStore(TimeStampedModel):
    """User-Store relationship (many-to-many with extra fields)."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_stores',
        verbose_name='使用者'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='store_users',
        verbose_name='門店'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='主要門店'
    )

    class Meta:
        db_table = 'user_stores'
        verbose_name = '使用者門店'
        verbose_name_plural = '使用者門店'
        unique_together = ['user', 'store']

    def __str__(self):
        return f'{self.user.display_name} - {self.store.name}'

    def save(self, *args, **kwargs):
        """Ensure only one primary store per user."""
        if self.is_primary:
            UserStore.objects.filter(
                user=self.user,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
