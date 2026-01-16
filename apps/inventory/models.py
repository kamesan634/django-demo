"""
Inventory models: Inventory, InventoryMovement, StockCount, StockTransfer.
"""
from django.db import models
from apps.core.models import BaseModel


class Inventory(BaseModel):
    """Inventory model - stock quantity per warehouse/product."""
    warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.CASCADE,
        related_name='inventory_items',
        verbose_name='倉庫'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='inventory_items',
        verbose_name='商品'
    )
    quantity = models.IntegerField(default=0, verbose_name='庫存數量')
    available_quantity = models.IntegerField(default=0, verbose_name='可用數量')
    reserved_quantity = models.IntegerField(default=0, verbose_name='預留數量')

    class Meta:
        db_table = 'inventory'
        verbose_name = '庫存'
        verbose_name_plural = '庫存'
        unique_together = ['warehouse', 'product']
        indexes = [
            models.Index(fields=['warehouse', 'product']),
        ]

    def __str__(self):
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}'

    def save(self, *args, **kwargs):
        self.available_quantity = self.quantity - self.reserved_quantity
        super().save(*args, **kwargs)


class InventoryMovement(BaseModel):
    """Inventory movement log."""
    TYPE_CHOICES = [
        ('PURCHASE_IN', '採購入庫'),
        ('SALE_OUT', '銷售出庫'),
        ('RETURN_IN', '退貨入庫'),
        ('RETURN_OUT', '退貨出庫'),
        ('ADJUST_IN', '調整增加'),
        ('ADJUST_OUT', '調整減少'),
        ('TRANSFER_IN', '調撥入庫'),
        ('TRANSFER_OUT', '調撥出庫'),
        ('COUNT_ADJUST', '盤點調整'),
    ]

    warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name='倉庫'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name='商品'
    )
    movement_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name='異動類型'
    )
    quantity = models.IntegerField(verbose_name='異動數量')
    balance = models.IntegerField(verbose_name='異動後餘額')
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='來源類型'
    )
    reference_id = models.IntegerField(null=True, blank=True, verbose_name='來源ID')
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'inventory_movements'
        verbose_name = '庫存異動'
        verbose_name_plural = '庫存異動'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['warehouse', 'product', 'created_at']),
        ]

    def __str__(self):
        return f'{self.product.name}: {self.quantity:+d}'


class StockCount(BaseModel):
    """Stock count (inventory check) model."""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('IN_PROGRESS', '盤點中'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]

    warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.CASCADE,
        related_name='stock_counts',
        verbose_name='倉庫'
    )
    count_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='盤點單號'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='狀態'
    )
    count_date = models.DateField(verbose_name='盤點日期')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'stock_counts'
        verbose_name = '盤點單'
        verbose_name_plural = '盤點單'
        ordering = ['-created_at']

    def __str__(self):
        return self.count_number


class StockCountItem(BaseModel):
    """Stock count item - individual product count."""
    stock_count = models.ForeignKey(
        StockCount,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='盤點單'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        verbose_name='商品'
    )
    system_quantity = models.IntegerField(verbose_name='系統數量')
    actual_quantity = models.IntegerField(null=True, blank=True, verbose_name='實際數量')
    difference = models.IntegerField(default=0, verbose_name='差異')

    class Meta:
        db_table = 'stock_count_items'
        verbose_name = '盤點明細'
        verbose_name_plural = '盤點明細'

    def save(self, *args, **kwargs):
        if self.actual_quantity is not None:
            self.difference = self.actual_quantity - self.system_quantity
        super().save(*args, **kwargs)


class StockTransfer(BaseModel):
    """Stock transfer between warehouses."""
    STATUS_CHOICES = [
        ('PENDING', '待處理'),
        ('IN_TRANSIT', '調撥中'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]

    transfer_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='調撥單號'
    )
    from_warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.CASCADE,
        related_name='transfers_out',
        verbose_name='來源倉庫'
    )
    to_warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.CASCADE,
        related_name='transfers_in',
        verbose_name='目標倉庫'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    transfer_date = models.DateField(verbose_name='調撥日期')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'stock_transfers'
        verbose_name = '調撥單'
        verbose_name_plural = '調撥單'
        ordering = ['-created_at']

    def __str__(self):
        return self.transfer_number


class StockTransferItem(BaseModel):
    """Stock transfer item."""
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='調撥單'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        verbose_name='商品'
    )
    quantity = models.IntegerField(verbose_name='數量')

    class Meta:
        db_table = 'stock_transfer_items'
        verbose_name = '調撥明細'
        verbose_name_plural = '調撥明細'
