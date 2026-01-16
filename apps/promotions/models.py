"""
Promotions models: Promotion, Coupon.
"""
from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel


class Promotion(BaseModel):
    """Promotion model."""
    TYPE_CHOICES = [
        ('PERCENTAGE', '百分比折扣'),
        ('FIXED', '固定金額折扣'),
        ('BUY_X_GET_Y', '買X送Y'),
    ]

    name = models.CharField(max_length=100, verbose_name='活動名稱')
    description = models.TextField(blank=True, verbose_name='活動說明')
    promotion_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='PERCENTAGE',
        verbose_name='促銷類型'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='折扣值',
        help_text='百分比折扣輸入10代表9折，固定金額直接輸入金額'
    )
    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='最低消費金額'
    )
    buy_quantity = models.IntegerField(
        default=0,
        verbose_name='購買數量',
        help_text='買X送Y的X'
    )
    get_quantity = models.IntegerField(
        default=0,
        verbose_name='贈送數量',
        help_text='買X送Y的Y'
    )
    start_date = models.DateTimeField(verbose_name='開始時間')
    end_date = models.DateTimeField(verbose_name='結束時間')
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    # Applicable scope
    products = models.ManyToManyField(
        'products.Product',
        blank=True,
        related_name='promotions',
        verbose_name='適用商品'
    )
    categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        related_name='promotions',
        verbose_name='適用分類'
    )
    stores = models.ManyToManyField(
        'stores.Store',
        blank=True,
        related_name='promotions',
        verbose_name='適用門店'
    )
    customer_levels = models.ManyToManyField(
        'customers.CustomerLevel',
        blank=True,
        related_name='promotions',
        verbose_name='適用會員等級'
    )

    class Meta:
        db_table = 'promotions'
        verbose_name = '促銷活動'
        verbose_name_plural = '促銷活動'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_valid(self):
        """Check if promotion is currently valid."""
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date


class Coupon(BaseModel):
    """Coupon model."""
    TYPE_CHOICES = [
        ('PERCENTAGE', '百分比折扣'),
        ('FIXED', '固定金額折扣'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', '有效'),
        ('USED', '已使用'),
        ('EXPIRED', '已過期'),
        ('DISABLED', '已停用'),
    ]

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='優惠券代碼'
    )
    name = models.CharField(max_length=100, verbose_name='優惠券名稱')
    discount_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='PERCENTAGE',
        verbose_name='折扣類型'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='折扣值'
    )
    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='最低消費金額'
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='最高折扣金額'
    )
    usage_limit = models.IntegerField(
        default=1,
        verbose_name='使用上限',
        help_text='0表示無限制'
    )
    used_count = models.IntegerField(default=0, verbose_name='已使用次數')
    start_date = models.DateTimeField(verbose_name='開始時間')
    end_date = models.DateTimeField(verbose_name='結束時間')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='狀態'
    )

    class Meta:
        db_table = 'coupons'
        verbose_name = '優惠券'
        verbose_name_plural = '優惠券'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f'{self.name} ({self.code})'

    @property
    def is_valid(self):
        """Check if coupon is valid for use."""
        now = timezone.now()
        if self.status != 'ACTIVE':
            return False
        if now < self.start_date or now > self.end_date:
            return False
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            return False
        return True

    def use(self):
        """Mark coupon as used."""
        self.used_count += 1
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            self.status = 'USED'
        self.save(update_fields=['used_count', 'status'])


class CouponUsage(BaseModel):
    """Coupon usage history."""
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name='優惠券'
    )
    order = models.ForeignKey(
        'sales.Order',
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name='訂單'
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='折扣金額'
    )

    class Meta:
        db_table = 'coupon_usages'
        verbose_name = '優惠券使用記錄'
        verbose_name_plural = '優惠券使用記錄'
