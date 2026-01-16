"""
Purchasing models: Supplier, PurchaseOrder, PurchaseOrderItem.
"""
from django.db import models
from apps.core.models import BaseModel


class Supplier(BaseModel):
    """Supplier model."""
    name = models.CharField(max_length=100, verbose_name='供應商名稱')
    code = models.CharField(max_length=20, unique=True, verbose_name='供應商代碼')
    contact_name = models.CharField(max_length=50, blank=True, verbose_name='聯絡人')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話')
    email = models.EmailField(blank=True, verbose_name='電子郵件')
    tax_id = models.CharField(max_length=20, blank=True, verbose_name='統一編號')
    address = models.TextField(blank=True, verbose_name='地址')
    payment_terms = models.IntegerField(default=30, verbose_name='付款天數')
    note = models.TextField(blank=True, verbose_name='備註')
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    class Meta:
        db_table = 'suppliers'
        verbose_name = '供應商'
        verbose_name_plural = '供應商'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class PurchaseOrder(BaseModel):
    """Purchase order model."""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('SUBMITTED', '已送出'),
        ('APPROVED', '已核准'),
        ('PARTIAL', '部分到貨'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]

    po_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='採購單號'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name='供應商'
    )
    warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name='入庫倉庫'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='狀態'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='總金額'
    )
    expected_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='預計到貨日'
    )
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='送出時間')
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_pos',
        verbose_name='核准者'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='核准時間')
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'purchase_orders'
        verbose_name = '採購單'
        verbose_name_plural = '採購單'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.po_number

    def calculate_total(self):
        """Calculate total amount from items."""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


class PurchaseOrderItem(BaseModel):
    """Purchase order item model."""
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='採購單'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    quantity = models.IntegerField(verbose_name='數量')
    received_quantity = models.IntegerField(default=0, verbose_name='已收數量')
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='單價'
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='小計'
    )

    class Meta:
        db_table = 'purchase_order_items'
        verbose_name = '採購單明細'
        verbose_name_plural = '採購單明細'

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class GoodsReceipt(BaseModel):
    """Goods receipt (receiving) model."""
    STATUS_CHOICES = [
        ('PENDING', '待驗收'),
        ('COMPLETED', '已完成'),
    ]

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='收貨單號'
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name='receipts',
        verbose_name='採購單'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    receipt_date = models.DateField(verbose_name='收貨日期')
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'goods_receipts'
        verbose_name = '收貨單'
        verbose_name_plural = '收貨單'
        ordering = ['-created_at']

    def __str__(self):
        return self.receipt_number


class GoodsReceiptItem(BaseModel):
    """Goods receipt item model."""
    receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='收貨單'
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        verbose_name='採購單項目'
    )
    received_quantity = models.IntegerField(verbose_name='收貨數量')

    class Meta:
        db_table = 'goods_receipt_items'
        verbose_name = '收貨明細'
        verbose_name_plural = '收貨明細'


class PurchaseReturn(BaseModel):
    """Purchase return model for returning goods to supplier."""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('SUBMITTED', '已送出'),
        ('APPROVED', '已核准'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]

    REASON_CHOICES = [
        ('DEFECTIVE', '瑕疵品'),
        ('WRONG_ITEM', '品項錯誤'),
        ('EXCESS', '數量過多'),
        ('EXPIRED', '過期商品'),
        ('QUALITY', '品質不良'),
        ('OTHER', '其他'),
    ]

    return_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='退貨單號'
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name='原採購單'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_returns',
        verbose_name='供應商'
    )
    warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.PROTECT,
        related_name='purchase_returns',
        verbose_name='出庫倉庫'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='狀態'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='DEFECTIVE',
        verbose_name='退貨原因'
    )
    reason_detail = models.TextField(blank=True, verbose_name='原因說明')
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='退貨總額'
    )
    return_date = models.DateField(verbose_name='退貨日期')
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_returns',
        verbose_name='核准者'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='核准時間')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'purchase_returns'
        verbose_name = '採購退貨單'
        verbose_name_plural = '採購退貨單'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['return_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.return_number

    def calculate_total(self):
        """Calculate total amount from items."""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


class PurchaseReturnItem(BaseModel):
    """Purchase return item model."""
    purchase_return = models.ForeignKey(
        PurchaseReturn,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='退貨單'
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        verbose_name='原採購項目'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    quantity = models.IntegerField(verbose_name='退貨數量')
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='單價'
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='小計'
    )
    reason = models.CharField(max_length=200, blank=True, verbose_name='退貨原因')

    class Meta:
        db_table = 'purchase_return_items'
        verbose_name = '採購退貨明細'
        verbose_name_plural = '採購退貨明細'

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class SupplierPrice(BaseModel):
    """Supplier price list for products."""
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='供應商'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='supplier_prices',
        verbose_name='商品'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='單價'
    )
    min_quantity = models.IntegerField(
        default=1,
        verbose_name='最低訂購量'
    )
    lead_time_days = models.IntegerField(
        default=7,
        verbose_name='交期(天)'
    )
    effective_from = models.DateField(verbose_name='生效日期')
    effective_to = models.DateField(
        null=True,
        blank=True,
        verbose_name='失效日期'
    )
    is_preferred = models.BooleanField(
        default=False,
        verbose_name='首選供應商'
    )
    note = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'supplier_prices'
        verbose_name = '供應商報價'
        verbose_name_plural = '供應商報價'
        ordering = ['-effective_from']
        indexes = [
            models.Index(fields=['supplier', 'product']),
            models.Index(fields=['product', 'is_preferred']),
        ]
        unique_together = ['supplier', 'product', 'effective_from']

    def __str__(self):
        return f'{self.supplier.name} - {self.product.name}: ${self.unit_price}'

    @property
    def is_active(self):
        """Check if price is currently active."""
        from django.utils import timezone
        today = timezone.now().date()
        if self.effective_to:
            return self.effective_from <= today <= self.effective_to
        return self.effective_from <= today
