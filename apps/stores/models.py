"""
Store and Warehouse models.
"""
from django.db import models
from apps.core.models import BaseModel


class Store(BaseModel):
    """Store model."""
    STATUS_CHOICES = [
        ('ACTIVE', '營業中'),
        ('INACTIVE', '停業'),
    ]

    name = models.CharField(max_length=100, verbose_name='門店名稱')
    code = models.CharField(max_length=20, unique=True, verbose_name='門店代碼')
    address = models.TextField(blank=True, verbose_name='地址')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話')
    tax_id = models.CharField(max_length=20, blank=True, verbose_name='統一編號')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='狀態'
    )
    business_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='營業時間',
        help_text='格式: {"mon": "09:00-21:00", ...}'
    )
    manager = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_stores',
        verbose_name='店長'
    )

    class Meta:
        db_table = 'stores'
        verbose_name = '門店'
        verbose_name_plural = '門店'
        ordering = ['code']

    def __str__(self):
        return f'{self.name} ({self.code})'


class Warehouse(BaseModel):
    """Warehouse model."""
    TYPE_CHOICES = [
        ('STORE', '門店倉庫'),
        ('WAREHOUSE', '獨立倉庫'),
        ('VIRTUAL', '虛擬倉庫'),
    ]

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='warehouses',
        verbose_name='所屬門店'
    )
    name = models.CharField(max_length=100, verbose_name='倉庫名稱')
    code = models.CharField(max_length=20, unique=True, verbose_name='倉庫代碼')
    warehouse_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='STORE',
        verbose_name='倉庫類型'
    )
    address = models.TextField(blank=True, verbose_name='地址')
    is_default = models.BooleanField(default=False, verbose_name='預設倉庫')
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    class Meta:
        db_table = 'warehouses'
        verbose_name = '倉庫'
        verbose_name_plural = '倉庫'
        ordering = ['store', 'code']

    def __str__(self):
        return f'{self.name} ({self.code})'

    def save(self, *args, **kwargs):
        """Ensure only one default warehouse per store."""
        if self.is_default:
            Warehouse.objects.filter(
                store=self.store,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
