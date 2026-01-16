"""
Customer models: CustomerLevel, Customer, PointsLog.
"""
from django.db import models
from apps.core.models import BaseModel


class CustomerLevel(BaseModel):
    """Customer membership level."""
    name = models.CharField(max_length=50, verbose_name='等級名稱')
    discount_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='折扣率 (%)'
    )
    points_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1,
        verbose_name='點數倍率'
    )
    min_points = models.IntegerField(
        default=0,
        verbose_name='升等門檻點數'
    )
    min_spending = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='升等門檻消費金額'
    )
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_default = models.BooleanField(default=False, verbose_name='預設等級')

    class Meta:
        db_table = 'customer_levels'
        verbose_name = '會員等級'
        verbose_name_plural = '會員等級'
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class Customer(BaseModel):
    """Customer model."""
    member_no = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='會員編號'
    )
    name = models.CharField(max_length=100, verbose_name='姓名')
    phone = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='手機號碼'
    )
    email = models.EmailField(blank=True, verbose_name='電子郵件')
    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    gender = models.CharField(
        max_length=1,
        choices=[('M', '男'), ('F', '女'), ('O', '其他')],
        blank=True,
        verbose_name='性別'
    )
    address = models.TextField(blank=True, verbose_name='地址')
    level = models.ForeignKey(
        CustomerLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name='會員等級'
    )
    points = models.IntegerField(default=0, verbose_name='累積點數')
    total_spending = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='累積消費金額'
    )
    total_orders = models.IntegerField(default=0, verbose_name='訂單數')
    note = models.TextField(blank=True, verbose_name='備註')
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    class Meta:
        db_table = 'customers'
        verbose_name = '客戶'
        verbose_name_plural = '客戶'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member_no']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f'{self.name} ({self.member_no})'

    def add_points(self, points, description='', user=None):
        """Add points to customer."""
        self.points += points
        self.save(update_fields=['points'])

        PointsLog.objects.create(
            customer=self,
            points=points,
            balance=self.points,
            description=description,
            created_by=user
        )

    def use_points(self, points, description='', user=None):
        """Use points from customer."""
        if points > self.points:
            raise ValueError('點數不足')

        self.points -= points
        self.save(update_fields=['points'])

        PointsLog.objects.create(
            customer=self,
            points=-points,
            balance=self.points,
            description=description,
            created_by=user
        )


class PointsLog(BaseModel):
    """Customer points transaction log."""
    TYPE_CHOICES = [
        ('EARN', '獲得'),
        ('REDEEM', '兌換'),
        ('ADJUST', '調整'),
        ('EXPIRE', '過期'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='points_logs',
        verbose_name='客戶'
    )
    points = models.IntegerField(verbose_name='點數異動')
    balance = models.IntegerField(verbose_name='異動後餘額')
    log_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='EARN',
        verbose_name='異動類型'
    )
    description = models.CharField(max_length=200, blank=True, verbose_name='說明')
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='來源類型'
    )
    reference_id = models.IntegerField(null=True, blank=True, verbose_name='來源ID')

    class Meta:
        db_table = 'points_logs'
        verbose_name = '點數異動記錄'
        verbose_name_plural = '點數異動記錄'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.customer.name}: {self.points:+d}'
