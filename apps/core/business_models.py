"""
Business configuration models.
F02-003: 付款方式管理
F02-006: 編號規則設定
F03-003: 價格管理
"""
from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel


class PaymentMethod(BaseModel):
    """
    Payment method configuration model.
    F02-003: 付款方式管理
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='付款方式代碼'
    )
    name = models.CharField(
        max_length=50,
        verbose_name='付款方式名稱'
    )
    description = models.TextField(
        blank=True,
        verbose_name='描述'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='啟用'
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='排序'
    )
    # 手續費率 (%)
    fee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='手續費率 (%)'
    )
    # 是否需要參考編號
    requires_reference = models.BooleanField(
        default=False,
        verbose_name='需要參考編號'
    )
    # 圖示 (可選)
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='圖示'
    )

    class Meta:
        db_table = 'payment_methods'
        verbose_name = '付款方式'
        verbose_name_plural = '付款方式'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class NumberingRule(BaseModel):
    """
    Document numbering rule configuration.
    F02-006: 編號規則設定
    """
    DOCUMENT_TYPES = [
        ('ORDER', '銷售訂單'),
        ('PURCHASE_ORDER', '採購單'),
        ('GOODS_RECEIPT', '收貨單'),
        ('STOCK_TRANSFER', '調撥單'),
        ('STOCK_COUNT', '盤點單'),
        ('MEMBER', '會員編號'),
        ('INVOICE', '發票'),
        ('REFUND', '退貨單'),
    ]

    RESET_FREQUENCY = [
        ('NEVER', '不重置'),
        ('DAILY', '每日'),
        ('MONTHLY', '每月'),
        ('YEARLY', '每年'),
    ]

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPES,
        unique=True,
        verbose_name='單據類型'
    )
    prefix = models.CharField(
        max_length=10,
        default='',
        blank=True,
        verbose_name='前綴'
    )
    suffix = models.CharField(
        max_length=10,
        default='',
        blank=True,
        verbose_name='後綴'
    )
    # 日期格式 (如 YYYYMMDD, YYMMDD, YYMM)
    date_format = models.CharField(
        max_length=20,
        default='YYYYMMDD',
        verbose_name='日期格式'
    )
    # 流水號位數
    sequence_length = models.IntegerField(
        default=4,
        verbose_name='流水號位數'
    )
    # 目前流水號
    current_sequence = models.IntegerField(
        default=0,
        verbose_name='目前流水號'
    )
    # 上次重置日期
    last_reset_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='上次重置日期'
    )
    # 重置頻率
    reset_frequency = models.CharField(
        max_length=10,
        choices=RESET_FREQUENCY,
        default='DAILY',
        verbose_name='重置頻率'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='啟用'
    )

    class Meta:
        db_table = 'numbering_rules'
        verbose_name = '編號規則'
        verbose_name_plural = '編號規則'

    def __str__(self):
        return f'{self.get_document_type_display()} ({self.prefix})'

    def generate_number(self) -> str:
        """
        Generate next document number based on rules.
        Uses distributed lock to prevent concurrent conflicts.
        """
        from apps.core.redis_services import distributed_lock

        with distributed_lock(f'{self.document_type}:number', ttl=5) as lock_id:
            if lock_id is None:
                # Fallback without lock (less safe but functional)
                return self._generate_number_internal()
            return self._generate_number_internal()

    def _generate_number_internal(self) -> str:
        """Internal number generation logic."""
        today = timezone.now().date()

        # Check if need to reset sequence
        should_reset = self._should_reset(today)
        if should_reset:
            self.current_sequence = 0
            self.last_reset_date = today

        # Increment sequence
        self.current_sequence += 1
        self.save(update_fields=['current_sequence', 'last_reset_date'])

        # Format date part
        date_part = self._format_date(today)

        # Format sequence
        seq_part = str(self.current_sequence).zfill(self.sequence_length)

        # Combine parts
        return f'{self.prefix}{date_part}{seq_part}{self.suffix}'

    def _should_reset(self, today) -> bool:
        """Check if sequence should be reset."""
        if self.last_reset_date is None:
            return True

        if self.reset_frequency == 'NEVER':
            return False
        elif self.reset_frequency == 'DAILY':
            return today != self.last_reset_date
        elif self.reset_frequency == 'MONTHLY':
            return (today.year != self.last_reset_date.year or
                   today.month != self.last_reset_date.month)
        elif self.reset_frequency == 'YEARLY':
            return today.year != self.last_reset_date.year

        return False

    def _format_date(self, date) -> str:
        """Format date according to date_format."""
        format_map = {
            'YYYYMMDD': '%Y%m%d',
            'YYMMDD': '%y%m%d',
            'YYMM': '%y%m',
            'YYYYMM': '%Y%m',
            'YYYY': '%Y',
            'MM': '%m',
            'DD': '%d',
        }
        py_format = format_map.get(self.date_format, '%Y%m%d')
        return date.strftime(py_format)

    @classmethod
    def get_next_number(cls, document_type: str) -> str:
        """
        Get next document number for a given type.
        Creates default rule if not exists.
        """
        rule, created = cls.objects.get_or_create(
            document_type=document_type,
            defaults=cls._get_default_config(document_type)
        )
        return rule.generate_number()

    @classmethod
    def _get_default_config(cls, document_type: str) -> dict:
        """Get default configuration for a document type."""
        defaults = {
            'ORDER': {'prefix': 'ORD', 'date_format': 'YYYYMMDD', 'sequence_length': 4},
            'PURCHASE_ORDER': {'prefix': 'PO', 'date_format': 'YYYYMMDD', 'sequence_length': 4},
            'GOODS_RECEIPT': {'prefix': 'GR', 'date_format': 'YYYYMMDD', 'sequence_length': 4},
            'STOCK_TRANSFER': {'prefix': 'ST', 'date_format': 'YYYYMMDD', 'sequence_length': 4},
            'STOCK_COUNT': {'prefix': 'SC', 'date_format': 'YYYYMMDD', 'sequence_length': 4},
            'MEMBER': {'prefix': 'M', 'date_format': 'YYMM', 'sequence_length': 6, 'reset_frequency': 'MONTHLY'},
            'INVOICE': {'prefix': '', 'date_format': 'YYYYMM', 'sequence_length': 8, 'reset_frequency': 'MONTHLY'},
            'REFUND': {'prefix': 'RF', 'date_format': 'YYYYMMDD', 'sequence_length': 4},
        }
        return defaults.get(document_type, {'prefix': '', 'date_format': 'YYYYMMDD', 'sequence_length': 6})


class ProductPrice(BaseModel):
    """
    Product price with time/tier support.
    F03-003: 價格管理
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='商品'
    )
    # 價格類型
    PRICE_TYPES = [
        ('REGULAR', '一般售價'),
        ('MEMBER', '會員價'),
        ('VIP', 'VIP 價'),
        ('WHOLESALE', '批發價'),
        ('PROMOTIONAL', '促銷價'),
    ]
    price_type = models.CharField(
        max_length=20,
        choices=PRICE_TYPES,
        default='REGULAR',
        verbose_name='價格類型'
    )
    # 關聯會員等級 (可選)
    customer_level = models.ForeignKey(
        'customers.CustomerLevel',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='product_prices',
        verbose_name='會員等級'
    )
    # 價格
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='價格'
    )
    # 最小購買數量
    min_quantity = models.IntegerField(
        default=1,
        verbose_name='最小購買數量'
    )
    # 有效期間
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='生效日期'
    )
    valid_to = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='結束日期'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='啟用'
    )

    class Meta:
        db_table = 'product_prices'
        verbose_name = '商品價格'
        verbose_name_plural = '商品價格'
        ordering = ['product', 'price_type', 'min_quantity']

    def __str__(self):
        return f'{self.product.name} - {self.get_price_type_display()}: ${self.price}'

    def is_valid(self) -> bool:
        """Check if this price is currently valid."""
        if not self.is_active:
            return False

        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False

        return True

    @classmethod
    def get_best_price(cls, product_id: int, customer_level_id: int = None, quantity: int = 1):
        """
        Get the best applicable price for a product.
        """
        now = timezone.now()

        # Base query for valid prices
        prices = cls.objects.filter(
            product_id=product_id,
            is_active=True,
            is_deleted=False,
            min_quantity__lte=quantity
        ).filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=now)
        ).filter(
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=now)
        )

        # Filter by customer level if provided
        if customer_level_id:
            level_prices = prices.filter(customer_level_id=customer_level_id)
            if level_prices.exists():
                return level_prices.order_by('price').first()

        # Get regular or promotional prices
        regular_prices = prices.filter(
            models.Q(price_type='REGULAR') | models.Q(price_type='PROMOTIONAL'),
            customer_level__isnull=True
        )

        if regular_prices.exists():
            return regular_prices.order_by('price').first()

        return None


class SupplierPerformance(BaseModel):
    """
    Supplier performance tracking.
    F07-009: 供應商績效評分
    """
    supplier = models.ForeignKey(
        'purchasing.Supplier',
        on_delete=models.CASCADE,
        related_name='performances',
        verbose_name='供應商'
    )
    # 評估期間
    period_start = models.DateField(verbose_name='期間開始')
    period_end = models.DateField(verbose_name='期間結束')

    # 績效指標
    total_orders = models.IntegerField(default=0, verbose_name='總訂單數')
    completed_orders = models.IntegerField(default=0, verbose_name='完成訂單數')
    on_time_deliveries = models.IntegerField(default=0, verbose_name='準時交貨數')
    quality_pass_orders = models.IntegerField(default=0, verbose_name='品質合格數')
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='總採購金額'
    )
    return_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='退貨金額'
    )

    # 計算得分 (0-100)
    delivery_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='交期得分'
    )
    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='品質得分'
    )
    price_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='價格得分'
    )
    service_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='服務得分'
    )
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='綜合得分'
    )

    # 評等
    RATING_CHOICES = [
        ('A', '優良'),
        ('B', '良好'),
        ('C', '普通'),
        ('D', '待改善'),
        ('F', '不合格'),
    ]
    rating = models.CharField(
        max_length=1,
        choices=RATING_CHOICES,
        default='C',
        verbose_name='評等'
    )
    notes = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'supplier_performances'
        verbose_name = '供應商績效'
        verbose_name_plural = '供應商績效'
        ordering = ['-period_end']
        unique_together = ['supplier', 'period_start', 'period_end']

    def __str__(self):
        return f'{self.supplier.name} - {self.period_start} ~ {self.period_end}'

    def calculate_scores(self):
        """Calculate performance scores."""
        # Delivery score
        if self.total_orders > 0:
            self.delivery_score = (self.on_time_deliveries / self.total_orders) * 100
        else:
            self.delivery_score = 0

        # Quality score
        if self.total_orders > 0:
            self.quality_score = (self.quality_pass_orders / self.total_orders) * 100
        else:
            self.quality_score = 0

        # Calculate overall score (weighted average)
        # Delivery: 30%, Quality: 40%, Price: 20%, Service: 10%
        self.overall_score = (
            self.delivery_score * 0.3 +
            self.quality_score * 0.4 +
            self.price_score * 0.2 +
            self.service_score * 0.1
        )

        # Determine rating
        if self.overall_score >= 90:
            self.rating = 'A'
        elif self.overall_score >= 80:
            self.rating = 'B'
        elif self.overall_score >= 70:
            self.rating = 'C'
        elif self.overall_score >= 60:
            self.rating = 'D'
        else:
            self.rating = 'F'

    def save(self, *args, **kwargs):
        self.calculate_scores()
        super().save(*args, **kwargs)


class AccountPayable(BaseModel):
    """
    Accounts payable tracking.
    F07-008: 應付帳款管理
    """
    STATUS_CHOICES = [
        ('PENDING', '待付款'),
        ('PARTIAL', '部分付款'),
        ('PAID', '已付款'),
        ('OVERDUE', '逾期'),
    ]

    supplier = models.ForeignKey(
        'purchasing.Supplier',
        on_delete=models.PROTECT,
        related_name='payables',
        verbose_name='供應商'
    )
    purchase_order = models.ForeignKey(
        'purchasing.PurchaseOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payables',
        verbose_name='採購單'
    )
    goods_receipt = models.ForeignKey(
        'purchasing.GoodsReceipt',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payables',
        verbose_name='收貨單'
    )
    # 帳款編號
    payable_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='帳款編號'
    )
    # 金額
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='總金額'
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='已付金額'
    )
    # 日期
    invoice_date = models.DateField(verbose_name='發票日期')
    due_date = models.DateField(verbose_name='到期日')
    # 狀態
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    # 發票號碼
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='發票號碼'
    )
    notes = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'accounts_payable'
        verbose_name = '應付帳款'
        verbose_name_plural = '應付帳款'
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['supplier']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f'{self.payable_number} - {self.supplier.name}'

    @property
    def remaining_amount(self):
        """Calculate remaining amount to pay."""
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self):
        """Check if payment is overdue."""
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status not in ['PAID']

    def update_status(self):
        """Update status based on payment progress."""
        if self.paid_amount >= self.total_amount:
            self.status = 'PAID'
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        elif self.is_overdue:
            self.status = 'OVERDUE'
        else:
            self.status = 'PENDING'


class PayablePayment(BaseModel):
    """
    Payment record for accounts payable.
    """
    payable = models.ForeignKey(
        AccountPayable,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='應付帳款'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='付款金額'
    )
    payment_date = models.DateField(verbose_name='付款日期')
    payment_method = models.CharField(
        max_length=20,
        default='BANK_TRANSFER',
        verbose_name='付款方式'
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='參考編號'
    )
    notes = models.TextField(blank=True, verbose_name='備註')

    class Meta:
        db_table = 'payable_payments'
        verbose_name = '付款紀錄'
        verbose_name_plural = '付款紀錄'
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.payable.payable_number} - ${self.amount}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update payable's paid amount
        total_paid = self.payable.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.payable.paid_amount = total_paid
        self.payable.update_status()
        self.payable.save(update_fields=['paid_amount', 'status'])
