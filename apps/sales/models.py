"""
Sales models: Order, OrderItem, Payment, Refund.
"""
from django.db import models
from apps.core.models import BaseModel


class Order(BaseModel):
    """Order model."""
    TYPE_CHOICES = [
        ('POS', 'POS 銷售'),
        ('ONLINE', '線上訂單'),
        ('PHONE', '電話訂單'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '待處理'),
        ('CONFIRMED', '已確認'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
        ('VOIDED', '已作廢'),
    ]

    order_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='訂單編號'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='門店'
    )
    warehouse = models.ForeignKey(
        'stores.Warehouse',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='出貨倉庫'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='客戶'
    )
    order_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='POS',
        verbose_name='訂單類型'
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='小計'
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='折扣金額'
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='稅額'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='總金額'
    )
    points_earned = models.IntegerField(default=0, verbose_name='獲得點數')
    points_used = models.IntegerField(default=0, verbose_name='使用點數')
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    note = models.TextField(blank=True, verbose_name='備註')

    # Void fields
    void_reason = models.TextField(blank=True, verbose_name='作廢原因')
    voided_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voided_orders',
        verbose_name='作廢者'
    )
    voided_at = models.DateTimeField(null=True, blank=True, verbose_name='作廢時間')

    class Meta:
        db_table = 'orders'
        verbose_name = '訂單'
        verbose_name_plural = '訂單'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['store', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(BaseModel):
    """Order item model."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='訂單'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        verbose_name='商品'
    )
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='規格'
    )
    quantity = models.IntegerField(verbose_name='數量')
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='單價'
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='折扣'
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='小計'
    )
    refunded_quantity = models.IntegerField(default=0, verbose_name='已退數量')

    class Meta:
        db_table = 'order_items'
        verbose_name = '訂單明細'
        verbose_name_plural = '訂單明細'

    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)


class Payment(BaseModel):
    """Payment model."""
    METHOD_CHOICES = [
        ('CASH', '現金'),
        ('CREDIT_CARD', '信用卡'),
        ('DEBIT_CARD', '金融卡'),
        ('LINE_PAY', 'LINE Pay'),
        ('APPLE_PAY', 'Apple Pay'),
        ('POINTS', '點數折抵'),
        ('OTHER', '其他'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '待付款'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失敗'),
        ('REFUNDED', '已退款'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='訂單'
    )
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        verbose_name='付款方式'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='金額'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='COMPLETED',
        verbose_name='狀態'
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='交易序號'
    )

    class Meta:
        db_table = 'payments'
        verbose_name = '付款記錄'
        verbose_name_plural = '付款記錄'


class Refund(BaseModel):
    """Refund model."""
    STATUS_CHOICES = [
        ('PENDING', '待處理'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]

    refund_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='退貨單號'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='refunds',
        verbose_name='原訂單'
    )
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='退款金額'
    )
    reason = models.TextField(verbose_name='退貨原因')
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')

    class Meta:
        db_table = 'refunds'
        verbose_name = '退貨單'
        verbose_name_plural = '退貨單'
        ordering = ['-created_at']

    def __str__(self):
        return self.refund_number


class RefundItem(BaseModel):
    """Refund item model."""
    refund = models.ForeignKey(
        Refund,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='退貨單'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.PROTECT,
        verbose_name='原訂單項目'
    )
    quantity = models.IntegerField(verbose_name='退貨數量')

    class Meta:
        db_table = 'refund_items'
        verbose_name = '退貨明細'
        verbose_name_plural = '退貨明細'


class Invoice(BaseModel):
    """Invoice model for tax purposes."""
    TYPE_CHOICES = [
        ('B2C', '二聯式'),
        ('B2B', '三聯式'),
        ('DONATION', '捐贈發票'),
        ('VOID', '作廢發票'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '待開立'),
        ('ISSUED', '已開立'),
        ('VOIDED', '已作廢'),
        ('CANCELLED', '已註銷'),
    ]

    invoice_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='發票號碼'
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='invoice',
        verbose_name='訂單'
    )
    invoice_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='B2C',
        verbose_name='發票類型'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    # 發票金額明細
    taxable_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='應稅金額'
    )
    tax_free_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='免稅金額'
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='稅額'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='發票總額'
    )
    # 買受人資訊 (三聯式發票用)
    buyer_tax_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='買受人統編'
    )
    buyer_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='買受人名稱'
    )
    # 載具資訊 (電子發票)
    carrier_type = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='載具類型'
    )
    carrier_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='載具號碼'
    )
    # 捐贈碼
    donation_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='捐贈碼'
    )
    # 開立時間
    issued_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='開立時間'
    )
    # 作廢相關
    void_reason = models.TextField(blank=True, verbose_name='作廢原因')
    voided_at = models.DateTimeField(null=True, blank=True, verbose_name='作廢時間')

    class Meta:
        db_table = 'invoices'
        verbose_name = '發票'
        verbose_name_plural = '發票'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice_type']),
        ]

    def __str__(self):
        return self.invoice_number


class InvoiceItem(BaseModel):
    """Invoice item model."""
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='發票'
    )
    description = models.CharField(max_length=200, verbose_name='品名')
    quantity = models.IntegerField(verbose_name='數量')
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='單價'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='金額'
    )

    class Meta:
        db_table = 'invoice_items'
        verbose_name = '發票明細'
        verbose_name_plural = '發票明細'

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
