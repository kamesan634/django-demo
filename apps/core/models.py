"""
Core abstract models for the application.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base model with created and updated timestamps."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='建立時間'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新時間'
    )

    class Meta:
        abstract = True


class UserTrackingModel(TimeStampedModel):
    """Abstract model that tracks user who created/updated the record."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='建立者'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='更新者'
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract model with soft delete functionality."""
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='已刪除'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='刪除時間'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted',
        verbose_name='刪除者'
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """Perform soft delete."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """Restore soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class BaseModel(UserTrackingModel, SoftDeleteModel):
    """Complete base model with timestamps, user tracking, and soft delete."""
    id = models.BigAutoField(primary_key=True)

    class Meta:
        abstract = True


class ActiveManager(models.Manager):
    """Manager that returns only non-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModelWithManager(BaseModel):
    """Base model with custom manager for filtering deleted records."""
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """
    Audit log model for tracking user operations.
    F06-007: 操作紀錄佇列
    """
    ACTION_CHOICES = [
        ('CREATE', '新增'),
        ('UPDATE', '更新'),
        ('DELETE', '刪除'),
        ('CONFIRM', '確認'),
        ('VOID', '作廢'),
        ('APPROVE', '核准'),
        ('REJECT', '駁回'),
        ('LOCK', '鎖定'),
        ('UNLOCK', '解鎖'),
        ('EXPORT', '匯出'),
        ('LOGIN', '登入'),
        ('LOGOUT', '登出'),
    ]

    MODULE_CHOICES = [
        ('AUTH', '認證'),
        ('USER', '使用者'),
        ('ROLE', '角色'),
        ('PRODUCT', '商品'),
        ('CATEGORY', '分類'),
        ('STORE', '門市'),
        ('WAREHOUSE', '倉庫'),
        ('CUSTOMER', '客戶'),
        ('ORDER', '訂單'),
        ('POS', 'POS'),
        ('INVENTORY', '庫存'),
        ('STOCK_COUNT', '盤點'),
        ('STOCK_TRANSFER', '轉撥'),
        ('SUPPLIER', '供應商'),
        ('PURCHASE_ORDER', '採購單'),
        ('REPORT', '報表'),
        ('UNKNOWN', '未知'),
    ]

    id = models.BigAutoField(primary_key=True)
    audit_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='審計ID'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='使用者'
    )
    username = models.CharField(
        max_length=150,
        verbose_name='使用者名稱'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='操作'
    )
    module = models.CharField(
        max_length=30,
        choices=MODULE_CHOICES,
        verbose_name='模組'
    )
    target_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='目標ID'
    )
    target_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='目標類型'
    )
    old_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name='舊值'
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name='新值'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP位址'
    )
    user_agent = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='User Agent'
    )
    created_at = models.DateTimeField(
        verbose_name='操作時間'
    )

    class Meta:
        db_table = 'audit_logs'
        verbose_name = '審計日誌'
        verbose_name_plural = '審計日誌'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['module']),
            models.Index(fields=['target_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return f"{self.username} - {self.action} - {self.module} - {self.created_at}"


# Import business models to make them discoverable by Django
from apps.core.business_models import (
    PaymentMethod,
    NumberingRule,
    ProductPrice,
    SupplierPerformance,
    AccountPayable,
    PayablePayment,
)
